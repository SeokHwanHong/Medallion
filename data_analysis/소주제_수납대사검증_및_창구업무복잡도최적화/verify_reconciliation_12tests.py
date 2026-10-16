import polars as pl, sys, os
sys.stdout.reconfigure(encoding="utf-8")
pl.Config.set_tbl_rows(30); pl.Config.set_tbl_cols(20); pl.Config.set_fmt_str_lengths(30)
D = "data_corrupted/data/"
os.makedirs("pivot/work", exist_ok=True)
rd = lambda t: pl.read_csv(f"{D}{t}/*.csv", infer_schema_length=0)
dt = lambda c: pl.col(c).str.to_datetime(strict=False)
fl = lambda c: pl.col(c).cast(pl.Float64, strict=False)

a = rd("appointments").with_columns(dt("booked_at"), dt("scheduled_at"))
ck = rd("checkins").with_columns(dt("arrival_at"), dt("checked_in_at"))
s = rd("clinic_sessions").with_columns(dt("session_start"), fl("capacity"))
hd = rd("hospital_departments"); h = rd("hospitals"); dep = rd("departments"); pt = rd("patients")
e = rd("encounters").with_columns(dt("started_at"), dt("ended_at"), fl("gross_charge"), fl("authorized_refund"), fl("net_charge"))
sv = rd("encounter_services").with_columns(fl("line_amount"), fl("quantity"))
pay = rd("payments").with_columns(dt("transacted_at"), fl("amount"))

svs = sv.group_by("encounter_id").agg(pl.col("line_amount").sum().alias("svc_sum"), pl.len().alias("n_lines"))
ps = pay.group_by("encounter_id").agg(
    pl.col("amount").filter(pl.col("transaction_type")=="PAYMENT").sum().alias("paid"),
    pl.col("amount").filter(pl.col("transaction_type")=="REFUND").sum().alias("refund_amt"),
    pl.len().alias("n_tx"))
m = (e.join(ck, on="checkin_id", how="left", suffix="_ck")
      .join(a, on="appointment_id", how="left", suffix="_ap")
      .join(s, on="session_id", how="left", suffix="_ss")
      .join(hd, on="hospital_department_id", how="left", suffix="_hd")
      .join(h, on="hospital_id", how="left", suffix="_h")
      .join(dep, on="department_code", how="left", suffix="_dep")
      .join(pt, on="patient_id", how="left", suffix="_pt")
      .join(svs, on="encounter_id", how="left").join(ps, on="encounter_id", how="left"))
print(m.shape)
print("join null rates:", {c: round(m[c].null_count()/m.height,4) for c in ["checkin_id","appointment_id","session_id","hospital_id","department_name","patient_id","svc_sum","paid"]})
m = m.with_columns(
    pl.col("started_at").dt.year().alias("yr"), pl.col("started_at").dt.month().alias("mon"),
    pl.col("started_at").dt.weekday().alias("wd"), pl.col("started_at").dt.hour().alias("hr"),
    ((pl.col("ended_at")-pl.col("started_at")).dt.total_minutes()).alias("dur_min"),
    ((pl.col("started_at")-pl.col("checked_in_at")).dt.total_minutes()).alias("wait_min"),
    ((pl.col("scheduled_at")-pl.col("booked_at")).dt.total_hours()).alias("lead_h"),
    (pl.col("authorized_refund")>0).cast(pl.Int8).alias("has_refund"),
    ((pl.col("gross_charge")-pl.col("svc_sum")).abs()>0.5).cast(pl.Int8).alias("svc_mismatch"),
    ((pl.col("paid")-pl.col("net_charge")).abs()>0.5).cast(pl.Int8).alias("pay_mismatch"),
    (2024 - pl.col("birth_date").str.slice(0,4).cast(pl.Int32, strict=False)).alias("age"))
m.write_parquet("pivot/work/mart.parquet")

def by(c, aggs=None):
    aggs = aggs or [pl.len().alias("n"), pl.col("gross_charge").mean().round(0).alias("charge"),
        pl.col("dur_min").mean().round(2).alias("dur"), pl.col("wait_min").mean().round(2).alias("wait"),
        (pl.col("has_refund").mean()*100).round(2).alias("refund%"),
        (pl.col("svc_mismatch").mean()*100).round(2).alias("svcmis%"), (pl.col("pay_mismatch").mean()*100).round(2).alias("paymis%"),
        pl.col("lead_h").mean().round(0).alias("lead"), pl.col("age").mean().round(1).alias("age")]
    print(f"\n=== by {c}"); print(m.group_by(c).agg(aggs).sort(c).head(30))
for c in ["yr","mon","wd","hr","department_name","hospital_type","region_code","channel","visit_type","outcome","sex_code","source_system","payment_method"] :
    if c in m.columns: by(c)

