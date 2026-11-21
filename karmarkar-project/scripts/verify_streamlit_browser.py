"""Browser smoke test; start Streamlit on localhost:8501 first.

Requires Playwright and Google Chrome: python -m pip install playwright.
Uses a temporary browser profile; does not access the user's browser session.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page()
            page.goto("http://127.0.0.1:8501")
            page.get_by_role("button", name="Giải bài toán", exact=True).click()
            page.get_by_text("Đã đạt sai số yêu cầu", exact=True).wait_for(timeout=60000)
            with page.expect_download() as event:
                page.get_by_role("button", name="Tải lời giải HTML", exact=True).click()
            download = event.value
            assert download.suggested_filename == "Loi_giai_Karmarkar.html"
            assert "Kết quả đầu ra" in Path(download.path()).read_text(encoding="utf-8")
            frame = page.frame_locator("iframe").first
            frame.get_by_text("Kết quả đầu ra", exact=False).first.wait_for()
            page.get_by_role("textbox", name="Hệ số mục tiêu").fill("1/0 0")
            page.get_by_role("button", name="Giải bài toán", exact=True).click()
            page.get_by_text('Không đọc được số hữu hạn', exact=False).wait_for()
            assert page.get_by_role("button", name="Tải lời giải HTML", exact=True).count() == 0
            print("PASS: solve, HTML preview, download, invalid input clears old report")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
