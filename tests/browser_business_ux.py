"""Real-browser smoke checks for B2B faceted search and result visibility."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width,height in [(1366,900),(390,844)]:
        page=browser.new_page(viewport={"width":width,"height":height})
        page.set_default_timeout(10000)
        errors=[]
        page.on("pageerror",lambda err: errors.append(str(err)))
        page.goto("http://127.0.0.1:8765/search.html",wait_until="networkidle")
        assert page.locator("#count").inner_text().find("件の補助金")>=0
        page.locator("#businessAreaToggle").click()
        assert page.locator("#businessAreaMenu").is_visible()
        assert page.locator("#businessAreaChoices input").count()==47
        page.locator("#businessKanto").click()
        assert page.locator("#businessAreaChoices input:checked").count()==7
        assert "7件" in page.locator("#businessAreaToggle").inner_text()
        page.locator("#businessAreaDone").click()
        assert not page.locator("#businessAreaMenu").is_visible()
        page.locator("#businessTopics .topic[data-keyword='創業']").click()
        page.locator("#businessTopics .topic[data-keyword='設備投資']").click()
        assert page.locator("#businessTopics .topic[aria-pressed='true']").count()==2
        assert "創業" in page.locator("#businessActiveFilters").inner_text()
        assert "設備投資" in page.locator("#businessActiveFilters").inner_text()
        page.locator("#reset").click()
        assert page.locator("#businessTopics .topic[aria-pressed='true']").count()==0
        assert page.locator("#businessAreaChoices input:checked").count()==0
        assert not errors, f"JavaScript errors at {width}px: {errors}"
        print(f"B2B browser UX passed: {width}px",flush=True)
        page.close()
    browser.close()
