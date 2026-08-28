#!/usr/bin/env python3
"""Publication screenshot capture v7b — reliable AI Copilot + populated alerts."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright

BASE = os.environ.get("PAPER_APP_URL", "http://127.0.0.1:5173")
OUT = Path(os.environ.get("PAPER_FIG_OUT", "/root/flooding-cholera-sync/docs/paper_figures"))
OUT.mkdir(parents=True, exist_ok=True)
VP = {"width": 1920, "height": 1080}
SCALE = 2  # Faster capture with good quality

# Use Vertex provider to avoid DeepSeek 422 errors and ensure chat content
USER_AGENT_JS = """() => {
  localStorage.setItem('cholera-auth-storage', JSON.stringify({
    state: {
      isAuthenticated: true,
      user: { email: 'demo@nasrda.gov.ng', role: 'admin', name: 'Yakubu Tanimu Umar' }
    },
    version: 0
  }));
}"""

AGENT_STORAGE_PATCH_JS = """() => {
  try {
    const raw = localStorage.getItem('cholera-agent-storage') || '{}';
    const parsed = JSON.parse(raw);
    parsed.state = {
      ...(parsed.state || {}),
      provider: 'nvidia_nim',
      model: 'meta/llama-3.3-70b-instruct',
      sidebarOpen: false,
    };
    localStorage.setItem('cholera-agent-storage', JSON.stringify(parsed));
  } catch (e) {}
}"""

AUTH_JS = """() => {
  localStorage.setItem('cholera-auth-storage', JSON.stringify({
    state: {
      isAuthenticated: true,
      user: { email: 'demo@nasrda.gov.ng', role: 'admin', name: 'Yakubu Tanimu Umar' }
    },
    version: 0
  }));
}"""


async def wait_net(page, ms=2500):
    try:
        await page.wait_for_load_state("networkidle", timeout=45000)
    except Exception:
        pass
    await page.wait_for_timeout(ms)


async def close_copilot(page) -> bool:
    # Prefer explicit close controls on the right panel
    for sel in [
        'button[title="Close sidebar"]',
        '[title="Close sidebar"]',
        'button:has-text("Close")',
    ]:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                await loc.click()
                await page.wait_for_timeout(600)
        except Exception:
            pass
    # If floating open button is visible, panel is closed
    try:
        open_btn = page.locator('button[title="Open AI Copilot"]')
        if await open_btn.count() and await open_btn.first.is_visible():
            return True
    except Exception:
        pass
    # Click left-nav AI Copilot toggle if panel still open (toggle off)
    try:
        nav = page.locator('aside button:has-text("AI Copilot")').first
        # if emerald pulse / active state hard to detect — check for chat textarea
        ta = page.locator('textarea').first
        if await ta.count() and await ta.is_visible():
            await nav.click()
            await page.wait_for_timeout(600)
            return True
    except Exception:
        pass
    return False


async def open_copilot(page) -> bool:
    # Prefer floating open control, then left-nav toggle.
    for sel in [
        'button[title="Open AI Copilot"]',
        'aside button:has-text("AI Copilot")',
    ]:
        try:
            loc = page.locator(sel).first
            if await loc.count() and await loc.is_visible():
                # If textarea already visible, stop.
                ta = page.locator('textarea')
                already = False
                if await ta.count():
                    for i in range(await ta.count()):
                        if await ta.nth(i).is_visible():
                            already = True
                            break
                if already:
                    return True
                await loc.click()
                await page.wait_for_timeout(900)
        except Exception:
            pass
    # Force provider/model in the open panel if selectors exist
    try:
        # provider dropdowns vary; try text option clicks
        for label in ['Vertex', 'Google', 'vertex', 'google']:
            opt = page.get_by_text(label, exact=False).first
            if await opt.count():
                try:
                    await opt.click(timeout=800)
                except Exception:
                    pass
    except Exception:
        pass
    try:
        await page.locator('textarea').first.wait_for(state='visible', timeout=6000)
        return True
    except Exception:
        return False


async def type_copilot(page, msg: str) -> bool:
    # Prefer the right-side copilot textarea (last visible textarea)
    tas = page.locator('textarea')
    n = await tas.count()
    target = None
    for i in range(n - 1, -1, -1):
        el = tas.nth(i)
        if await el.is_visible():
            target = el
            break
    if target is None:
        return False
    await target.click()
    await target.fill(msg)
    await page.keyboard.press('Enter')
    return True


async def shot(page, name: str):
    fp = OUT / f"{name}.png"
    await page.wait_for_timeout(500)  # allow UI to settle
    await page.screenshot(path=str(fp), full_page=False, type='png')
    print(f"[ok] {name} -> {fp} ({fp.stat().st_size // 1024} KB)")


async def goto(page, path: str, settle_ms: int = 3500):
    try:
        await page.goto(BASE + path, wait_until='domcontentloaded', timeout=60000)
    except Exception as e:
        print(f"[warn] goto {path}: {e}")
    await wait_net(page, settle_ms)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--font-render-hinting=none',
                '--force-device-scale-factor=2',
                ],
        )
        ctx = await browser.new_context(viewport=VP, device_scale_factor=SCALE, reduced_motion='reduce')
        page = await ctx.new_page()
        page.set_default_timeout(60000)

        await page.goto(BASE + '/', wait_until='domcontentloaded')
        await page.evaluate(AUTH_JS)
        # Force vertex provider and agent storage (patch with correct model)
        await page.evaluate(USER_AGENT_JS)
        await page.evaluate(AGENT_STORAGE_PATCH_JS)
        # Also patch zustand store if already hydrated
        await page.evaluate(
            """() => {
              // best-effort: click nothing; store may rehydrate from localStorage on next load
            }"""
        )

        # Section shots with copilot closed
        sections = [
            ('app_dashboard', '/', 5000),
            ('app_map', '/map', 7000),
            ('app_facilities', '/facilities', 5500),
            ('app_alerts', '/alerts', 5000),
            ('app_reports', '/reports', 4500),
            ('app_satellite', '/satellite', 4500),
            ('app_correlation', '/analytics', 4500),
            ('app_agent_explorer', '/agent-explorer', 5500),
        ]
        for name, path, settle in sections:
            await goto(page, path, settle)
            await close_copilot(page)
            await page.wait_for_timeout(700)
            if name == 'app_alerts':
                try:
                    await page.wait_for_selector('table tbody tr, [class*="alert"]', timeout=12000)
                except Exception:
                    print('[warn] alerts content wait timeout')
                await page.mouse.wheel(0, 120)
                await page.wait_for_timeout(400)
            await shot(page, name)

        # Dashboard + AI Copilot OPEN with conversation
        await goto(page, '/', 4500)
        opened = await open_copilot(page)
        print('copilot_open_dashboard:', opened)
        msg = (
            "Summarize the current national cholera risk picture across 774 LGAs "
            "and highlight Cross River pilot LGAs with elevated case or flood signals."
        )
        typed = await type_copilot(page, msg) if opened else False
        print('copilot_typed:', typed)
        await page.wait_for_timeout(20000 if typed else 2000)
        await shot(page, 'app_copilot_open')

        # Second angle: still open, crop-friendly wider chat
        await shot(page, 'app_surveillance_copilot')

        # Agent Explorer with copilot open + generation attempt
        await goto(page, '/agent-explorer', 4000)
        opened2 = await open_copilot(page)
        print('copilot_open_agent:', opened2)
        agent_msg = (
            'Using the Cross River 2021 sentinel pilot line-list '
            '(crossriver_2021_pilot_linelist_agg.csv), build a dashboard of '
            'cholera cases and deaths by LGA.'
        )
        typed2 = await type_copilot(page, agent_msg) if opened2 else False
        print('agent_typed:', typed2)
        await page.wait_for_timeout(26000 if typed2 else 3000)
        await shot(page, 'app_copilot_agent')

        # Generated explorer with copilot closed
        await close_copilot(page)
        await page.wait_for_timeout(1200)
        await shot(page, 'app_agent_generated')
        await shot(page, 'app_agent')

        await browser.close()
        print('ALL CAPTURES DONE ->', OUT)


if __name__ == '__main__':
    asyncio.run(main())
