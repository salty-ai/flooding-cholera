"""Capture V11 paper figures from the live deployment (desktop 1600x1000, DPR 2)."""
from playwright.sync_api import sync_playwright
import re, time
OUT="/root/cholera_hod_tasks/figs_v11"
import os; os.makedirs(OUT, exist_ok=True)
BASE="https://cholera.abokiwise.ai"


def close_sidebar(pg):
    """Close the AI copilot side panel (defaults open on >=1024px) so figures show the page itself."""
    pg.wait_for_timeout(500)
    try:
        if pg.evaluate("() => !!document.querySelector('aside, [class*=Sidebar], [data-testid=agent-sidebar]') && document.body.innerText.includes('Surveillance Assistant')"):
            btn = pg.locator('button:has(span.material-symbols-outlined:text-is(\"smart_toy\"))').first
            btn.click(timeout=5000); pg.wait_for_timeout(800)
    except Exception as e:
        print("close_sidebar:", str(e)[:80])
    print("sidebar closed:", 'Surveillance Assistant' not in pg.inner_text('body'))

with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':1600,'height':1000}, device_scale_factor=2)
    pg=ctx.new_page()

    # Fig 4: national dashboard — top section (verified state tier) + KPIs
    pg.goto(BASE+"/", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(6000)
    close_sidebar(pg)
    pg.screenshot(path=f"{OUT}/fig4_dashboard_national_tier.png")

    # Fig 4b: drill-down open (FCT -> click a large state), scrolled to panel
    pg.evaluate("""() => { const m=document.querySelectorAll('.leaflet-container')[0];
        const ps=[...m.querySelectorAll('path.leaflet-interactive')].filter(p=>p.getBoundingClientRect().width>20);
        // pick the largest polygon (most likely a big northern state) for a rich drill-down
        ps.sort((a,b)=>b.getBoundingClientRect().width-a.getBoundingClientRect().width);
        ps[0].dispatchEvent(new MouseEvent('click',{bubbles:true})); }""")
    pg.wait_for_timeout(3000)
    h=pg.query_selector('h4:has-text("verified situation-report")')
    print("drilldown:", h.inner_text() if h else None)
    h.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
    pg.screenshot(path=f"{OUT}/fig4b_state_drilldown.png")

    # Fig 9: scroll to LGA risk map + correlation panel (heuristic tier)
    pg.goto(BASE+"/", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(5000)
    close_sidebar(pg)
    el=pg.query_selector('h3:has-text("heuristic tier")'); el.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-80)"); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"{OUT}/fig9_heuristic_tier_riskmap.png")

    # Fig 5: full-screen map view
    pg.goto(BASE+"/map", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(5000)
    close_sidebar(pg)
    pg.screenshot(path=f"{OUT}/fig5_map_view.png")

    # Fig 10: alerts page
    pg.goto(BASE+"/alerts", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(4000)
    close_sidebar(pg)
    pg.screenshot(path=f"{OUT}/fig10_alerts.png")
    print("alerts text:", pg.inner_text('body')[:300].replace('\n',' | '))

    # Fig 11: copilot live query on the national dashboard
    pg.goto(BASE+"/", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(4000)
    pg.get_by_placeholder(re.compile('Ask|question|message', re.I)).first.fill("Which states had the highest verified suspected-case counts in 2021, and what is the official NCDC year-end total?")
    pg.keyboard.press("Enter"); pg.wait_for_timeout(60000)
    pg.screenshot(path=f"{OUT}/fig11_copilot_live.png")
    t=pg.inner_text('body'); i=t.rfind('smart_toy'); print("copilot answer:", t[i:i+500].replace('\n',' | '))

    # Fig 12: agent explorer
    pg.goto(BASE+"/agent-explorer", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(4000)
    close_sidebar(pg)
    pg.screenshot(path=f"{OUT}/fig12_agent_explorer.png")
    b.close()
print("done")
