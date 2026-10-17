"""Drive the full UI flow in headless Chrome and capture screenshots."""
from __future__ import annotations

from pathlib import Path
import re

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

    page.request.post(BASE + "/api/demo/reset")
    page.goto(BASE + "/")
    page.wait_for_timeout(600)
    shot(page, "flow-landing.png", full=True)
    shot(page, "flow-landing-hero.png")

    page.goto(BASE + "/signin")
    page.wait_for_timeout(300)
    shot(page, "flow-signin.png")
    page.click("button:has-text('Continue with Google')", no_wait_after=True)
    page.wait_for_url("**/onboarding/connect")
    page.wait_for_selector(".modal-card", timeout=10000)
    shot(page, "flow-connect.png")

    page.click("button:has-text('Allow read-only access')", no_wait_after=True)
    page.wait_for_url("**/onboarding/crawl", timeout=15000)
    page.wait_for_timeout(400)
    shot(page, "flow-crawl.png")
    page.wait_for_url("**/onboarding/profile-building", timeout=15000)
    page.wait_for_timeout(600)
    shot(page, "flow-profile-building.png")
    page.wait_for_url("**/onboarding/profile", timeout=15000)
    page.wait_for_timeout(300)
    shot(page, "flow-profile.png")

    page.fill("#field_phone", "(718) 555-0142")
    page.fill("#field_authorized_rep", "Marisol Vance, Managing Member")
    page.click("button:has-text('Continue to verification')", no_wait_after=True)
    page.wait_for_url("**/onboarding/verify", timeout=15000)
    page.wait_for_selector("text=Verified against government records", timeout=20000)
    page.wait_for_timeout(400)
    shot(page, "flow-verify.png")
    page.click("a:has-text('Continue to benefit search')", no_wait_after=True)
    page.wait_for_url("**/onboarding/benefits", timeout=20000)
    page.wait_for_timeout(300)
    shot(page, "flow-benefits.png")

    page.click("a:has-text('Fill this form')")
    page.wait_for_url("**/filling", timeout=15000)
    page.wait_for_selector(".pdf-field", timeout=20000)
    page.wait_for_timeout(1600)
    shot(page, "flow-filling.png")
    page.wait_for_url(re.compile(r".*/onboarding/benefits/ben_[^/]+$"), timeout=20000)
    page.wait_for_timeout(400)
    shot(page, "flow-form.png")

    page.check("input[name='approve']")
    page.click("button:has-text('Approve')", no_wait_after=True)
    page.wait_for_url("**/onboarding/progress/**")
    page.wait_for_timeout(300)
    shot(page, "flow-progress.png")

    page.goto(BASE + "/dashboard")
    page.wait_for_timeout(500)
    shot(page, "flow-dashboard.png")

    page.goto(BASE + "/gov-docs")
    page.wait_for_timeout(600)
    shot(page, "flow-gov-docs.png")

    browser.close()
    print("done")
