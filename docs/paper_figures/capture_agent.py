"""Recapture ONLY the agent-generated dashboard, copilot closed, clean."""
import asyncio, os
from playwright.async_api import async_playwright
BASE="http://localhost:5173"; OUT="/root/paper_figures_app"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(headless=True,args=["--no-sandbox","--force-device-scale-factor=3"])
        pg=await (await b.new_context(viewport={"width":1680,"height":1050},device_scale_factor=3)).new_page()
        await pg.goto(BASE,wait_until="domcontentloaded")
        await pg.evaluate("""()=>localStorage.setItem('cholera-auth-storage',JSON.stringify({state:{isAuthenticated:true,user:{email:'d@n.ng',role:'admin',name:'Yakubu Tanimu Umar'}},version:0}))""")
        await pg.goto(BASE+"/agent-explorer",wait_until="networkidle"); await pg.wait_for_timeout(3000)
        # open copilot
        el=await pg.query_selector('[title="Open AI Copilot"]')
        if el: await el.click(); await pg.wait_for_timeout(1500)
        msg='I have uploaded "crossriver_2021_pilot_linelist_agg.csv". Build a dashboard visualizing cholera cases and deaths by LGA.'
        for sel in ['textarea','input[type="text"]']:
            e=await pg.query_selector(sel)
            if e: await e.fill(msg); await pg.keyboard.press("Enter"); break
        # wait for generation
        await pg.wait_for_timeout(24000)
        # close copilot to reveal dashboard
        for _ in range(3):
            c=await pg.query_selector('[title="Close sidebar"]')
            if c: await c.click(); await pg.wait_for_timeout(600)
            else: break
        await pg.wait_for_timeout(1500)
        # capture viewport (dashboard top)
        await pg.screenshot(path=os.path.join(OUT,"app_agent_generated.png"))
        print("saved viewport agent dashboard", os.path.getsize(os.path.join(OUT,'app_agent_generated.png'))//1024,"KB")
        await b.close()
asyncio.run(main())
