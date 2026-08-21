"""Capture real app screenshots for the cholera paper."""
import asyncio, os
from playwright.async_api import async_playwright

BASE = "http://localhost:5174"   # active vite port
OUT = "/root/paper_figures_app"
os.makedirs(OUT, exist_ok=True)

VIEWS = [
    ("dashboard", "/",            5000),
    ("map",       "/map",         6000),
    ("facilities","/facilities",  6000),
    ("alerts",    "/alerts",      4000),
    ("correlation","/correlation",5000),
    ("agent",     "/agent-explorer",4000),
    ("satellite", "/satellite",   4000),
    ("reports",   "/reports",     4000),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(viewport={"width":1600,"height":1000}, device_scale_factor=2)
        # pre-seed auth localStorage so no login screen
        page = await ctx.new_page()
        await page.goto(BASE, wait_until="domcontentloaded")
        await page.evaluate("""() => {
            localStorage.setItem('cholera-auth-storage', JSON.stringify({
              state:{isAuthenticated:true,user:{email:'demo@nasrda.gov.ng',role:'admin',name:'Yakubu Tanimu Umar'}},version:0}));
        }""")
        for name, path, wait in VIEWS:
            try:
                await page.goto(BASE+path, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"[warn] {name}: networkidle timeout, continuing ({e})")
                try: await page.goto(BASE+path, wait_until="domcontentloaded", timeout=20000)
                except: pass
            await page.wait_for_timeout(wait)
            fp = os.path.join(OUT, f"app_{name}.png")
            await page.screenshot(path=fp, full_page=False)
            print(f"[ok] {name} -> {fp} ({os.path.getsize(fp)} bytes)")
        await browser.close()

asyncio.run(main())
