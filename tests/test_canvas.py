import sys
from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("🌍 Navigeren naar http://localhost:8000...")
        try:
            page.goto('http://localhost:8000')
            # Wacht tot map element er is
            page.wait_for_selector('#map canvas', timeout=10000)
            print("⏳ Wachten op render...")
            time.sleep(5)  # Laat mapbox + deckgl goed laden
            
            # Voer JS uit in browser
            result = page.evaluate('''() => {
                let responses = [];
                try {
                    const canvases = document.querySelectorAll('#map canvas');
                    responses.push(`Aantal canvases: ${canvases.length}`);
                    
                    Array.from(canvases).forEach((c, index) => {
                        let info = `Canvas ${index} (${c.width}x${c.height}): `;
                        try {
                            const data = c.toDataURL('image/png');
                            info += `SUCCES! (Lengte dataURL: ${data.length} chars)`;
                        } catch(e) {
                            info += `FOUT! ${e.toString()}`;
                        }
                        responses.push(info);
                    });
                } catch(e) {
                    responses.push(`Algemene JS error: ${e.toString()}`);
                }
                return responses;
            }''')
            
            print("\n=== Resultaten ===")
            for r in result:
                print(r)
                
        except Exception as e:
            print(f"Playwright error: {e}")
            
        browser.close()

if __name__ == '__main__':
    main()
