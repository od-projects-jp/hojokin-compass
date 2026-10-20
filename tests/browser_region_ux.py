"""End-to-end UX smoke test against a real browser, not just static HTML checks."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/individual.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width, height in [(1366, 900), (390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE, wait_until="networkidle")
        toggle = page.locator("#prefectureToggle")
        toggle.click()
        menu = page.locator("#prefectureMenu")
        assert menu.is_visible(), f"menu not visible at {width}px"
        assert toggle.get_attribute("aria-expanded") == "true"
        assert page.locator("#prefectureChoices input").count() == 47
        assert page.locator(".hero-search").evaluate("(e) => getComputedStyle(e).overflow") == "visible"
        # Crucial regression: dropdown must remain visible outside the hero boundary.
        menu_box = menu.bounding_box()
        hero_box = page.locator(".hero-search").bounding_box()
        assert menu_box and hero_box
        assert menu_box["y"] + menu_box["height"] > hero_box["y"] + hero_box["height"]

        page.locator("#selectKanto").click()
        assert page.locator("#prefectureChoices input:checked").count() == 7
        assert "7都道府県" in page.locator("#selectedPrefectures").inner_text()
        page.locator("#selectAllPrefectures").click()
        assert page.locator("#prefectureChoices input:checked").count() == 47
        page.locator("#clearPrefectures").click()
        assert page.locator("#prefectureChoices input:checked").count() == 0

        page.get_by_text("東京都", exact=True).last.click()
        assert page.locator("#prefectureChoices input:checked").count() == 1
        assert page.locator("#region").input_value() == "東京都"
        page.locator("#closePrefectures").click()
        assert not menu.is_visible()
        page.locator("#region").select_option("神奈川県")
        toggle.click()
        assert page.locator("#prefectureChoices input:checked").count() == 1
        assert page.locator("#prefectureChoices input[value='神奈川県']").is_checked()
        page.locator("#closePrefectures").click()
        page.locator(".topic[data-topic='住宅']").click()
        assert "件の支援制度が見つかりました" in page.locator("#count").inner_text()
        assert not errors, f"browser JavaScript errors at {width}px: {errors}"
        page.close()
    browser.close()
print("Desktop and mobile real-browser region UX passed")
