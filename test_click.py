from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser Error: {err.message}"))
        
        print("Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000")
        
        print("Waiting for network idle...")
        page.wait_for_load_state("networkidle")
        
        print("Clicking near coordinates...")
        # Just click the center of the map canvas
        page.mouse.click(600, 400)
        time.sleep(2)
        
        print("Done")
        browser.close()

if __name__ == '__main__':
    run()
