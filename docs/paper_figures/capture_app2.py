"""Improved capture: hi-res, Copilot CLOSED on section shots, real AI-generated agent dashboard."""
import asyncio, os
from playwright.async_api import async_playwright

BASE="http://localhost:5173"
OUT="/root/paper_figures_app"; os.makedirs(OUT, exist_ok=True)
VP={"width":1680,"height":1050}
SCALE=3

# section views to capture WITH COPILOT CLOSED
SECTIONS=[("dashboard","/",5000),("map","/map",6500),("facilities","/facilities",6000),
          ("alerts","/alerts",4500),("reports","/reports",4500)]

async def close_copilot(page):
    # The Copilot floating panel: click any element with title "Close sidebar"; fallback set store
    for sel in ['[title="Close sidebar"]','button[aria-label="Close sidebar"]']:
        try:
            el=await page.query_selector(sel)
            if el:
                await el.click(); await page.wait_for_timeout(600); return True
        except: pass
    # fallback: hide via DOM (the fixed overlay + panel)
    try:
        await page.evaluate("""() => {
          document.querySelectorAll('[title=\"Close sidebar\"]').forEach(b=>b.click());
        }""")
    except: pass
    return False

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage","--force-device-scale-factor=3"])
        ctx=await b.new_context(viewport=VP, device_scale_factor=SCALE)
        page=await ctx.new_page()
        await page.goto(BASE,wait_until="domcontentloaded")
        await page.evaluate("""()=>localStorage.setItem('cholera-auth-storage',JSON.stringify({state:{isAuthenticated:true,user:{email:'demo@nasrda.gov.ng',role:'admin',name:'Yakubu Tanimu Umar'}},version:0}))""")

        for name,path,wait in SECTIONS:
            try: await page.goto(BASE+path,wait_until="networkidle",timeout=45000)
            except Exception as e: print(f"[warn] {name}: {e}")
            await page.wait_for_timeout(wait)
            await close_copilot(page)
            await page.wait_for_timeout(1200)
            fp=os.path.join(OUT,f"app_{name}.png")
            await page.screenshot(path=fp)
            print(f"[ok] {name} -> {fp} ({os.path.getsize(fp)//1024} KB)")

        # ===== AGENT EXPLORER: real AI-generated dashboard via Vertex =====
        await page.goto(BASE+"/agent-explorer",wait_until="networkidle",timeout=45000)
        await page.wait_for_timeout(3000)
        # open copilot if not open
        opened=False
        for sel in ['[title="Open AI Copilot"]','button[title="Open AI Copilot"]']:
            el=await page.query_selector(sel)
            if el: await el.click(); opened=True; break
        await page.wait_for_timeout(1500)
        # type the message into the copilot chat input
        msg=('I have uploaded "crossriver_2021_pilot_linelist_agg.csv". '
             'Build a dashboard visualizing cholera cases and deaths by LGA.')
        # find a textarea/input in the sidebar
        typed=False
        for sel in ['textarea','input[type="text"]']:
            el=await page.query_selector(sel)
            if el:
                await el.click(); await el.fill(msg); await page.keyboard.press("Enter"); typed=True; break
        print("agent opened:",opened,"typed:",typed)
        # wait for Vertex to stream + dashboard to render
        await page.wait_for_timeout(22000)
        # close copilot to reveal the generated dashboard cleanly
        await close_copilot(page)
        await page.wait_for_timeout(1500)
        fp=os.path.join(OUT,"app_agent_generated.png")
        await page.screenshot(path=fp, full_page=True)
        print(f"[ok] agent_generated -> {fp} ({os.path.getsize(fp)//1024} KB)")

        await b.close()

asyncio.run(main())
