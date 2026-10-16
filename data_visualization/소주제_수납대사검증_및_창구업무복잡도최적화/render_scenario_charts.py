"""목적: 발표용 차트 렌더 검증. 입력: 로컬 Plotly HTML. 출력: PNG와 검증 JSON. DB 접속 없음."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parent
results=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1320,'height':760},device_scale_factor=1.5)
    for source in sorted((root/'charts').glob('*.html')):
        errors=[]
        page.on('pageerror',lambda err: errors.append(str(err)))
        page.goto(source.as_uri())
        page.wait_for_function("document.querySelector('.js-plotly-plot') && document.querySelector('.js-plotly-plot')._fullLayout")
        page.locator('.js-plotly-plot').screenshot(path=str(source.with_suffix('.png')))
        traces=page.evaluate("document.querySelector('.js-plotly-plot').data.length")
        assert traces>0 and not errors,(source,errors)
        results.append({'chart':source.stem,'traces':traces,'page_errors':errors,'png_bytes':source.with_suffix('.png').stat().st_size})
    browser.close()
(root/'차트렌더검증.json').write_text(json.dumps({'author':'Team 3','purpose':'HTML 렌더 및 PNG 생성 검증','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
print('Rendered',len(results),'charts')
