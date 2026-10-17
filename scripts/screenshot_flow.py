"""Drive the full UI flow in headless Chrome and capture screenshots."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent.parent / "docs" / "proofs"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name: str, full: bool = False) -> None:
    page.screenshot(path=str(OUT / name), full_page=full)
    print("shot", name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    page = context.new_page()
    page.set_default_timeout(15000)

    page.goto(BASE + "/")
    page.wait_for_timeout(600)
    shot(page, "flow-landing.png", full=True)
    shot(page, "flow-landing-hero.png")

    page.goto(BASE + "/signin")
    page.fill("#email", "marisol@gowanuskettle.example")
    page.click("button:has-text('Continue')")
    page.wait_for_url("**/onboarding/connect")
    shot(page, "flow-connect.png")

    page.click("button:has-text('Authorize')")
    page.wait_for_url("**/onboarding/profile", timeout=15000)
    page.wait_for_timeout(300)
    shot(page, "flow-profile.png")

    page.fill("#field_phone", "(718) 555-0142")
    page.fill("#field_authorized_rep", "Marisol Vance, Managing Member")
    page.click("button:has-text('Continue to benefit search')")
    page.wait_for_url("**/onboarding/benefits", timeout=20000)
    page.wait_for_timeout(300)
    shot(page, "flow-benefits.png")

    page.click("a:has-text('Fill this form')")
    page.wait_for_url("**/onboarding/benefits/**")
    page.wait_for_timeout(300)
    shot(page, "flow-form.png")

    page.check("input[name='approve']")
    page.click("button:has-text('Approve')")
    page.wait_for_url("**/onboarding/progress/**")
    page.wait_for_timeout(300)
    shot(page, "flow-progress.png")

    page.goto(BASE + "/dashboard")
    page.wait_for_timeout(500)
    shot(page, "flow-dashboard.png")

    browser.close()
    print("done")
