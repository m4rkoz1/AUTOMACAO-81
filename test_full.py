import asyncio
import time
from playwright.async_api import async_playwright

REMOTE_DIR = "/opt/automacao"

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        for filial in ["RJO", "FSP"]:
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()
            page.on("dialog", lambda d: asyncio.create_task(d.accept()))

            # Login
            await page.goto("https://sistema.ssw.inf.br/bin/ssw0422", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.fill('input[name="f1"]', "GIA")
            await page.fill('input[name="f2"]', "11571959700")
            await page.fill('input[name="f3"]', "12345678")
            await page.fill('input[name="f4"]', "123")
            await page.click('a[id="5"]')
            await asyncio.sleep(5)

            if filial != "RJO":
                await page.fill('input[id="2"]', filial)
                await asyncio.sleep(0.3)

                # The key: POST to menu01 with act=TRO&f2=FSP&f3=52 changes the session!
                dummy = str(int(time.time() * 1000))
                await page.evaluate(f"""
                    () => {{
                        return new Promise((resolve) => {{
                            const xhr = new XMLHttpRequest();
                            xhr.open('POST', '/bin/menu01', true);
                            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                            xhr.onreadystatechange = function() {{
                                if (xhr.readyState === 4) resolve(xhr.status);
                            }};
                            xhr.send('act=TRO&f2={filial}&f3=52&menu01=1&dummy={dummy}');
                        }});
                    }}
                """)
                await asyncio.sleep(2)

            # Navigate to report
            await page.goto("https://sistema.ssw.inf.br/bin/ssw0052", wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await asyncio.sleep(2)

            await page.fill('input[name="relatorio_excel"]', "S")
            download_future = asyncio.get_event_loop().create_future()
            page.on("download", lambda dl: (not download_future.done()) and download_future.set_result(dl))
            await page.click('a[id="btn_envia"]')

            try:
                dl = await asyncio.wait_for(download_future, timeout=30)
                dest = f"{REMOTE_DIR}/test14_{filial}.csv"
                await dl.save_as(dest)
                with open(dest, "rb") as f:
                    content = f.read()
                lines_content = content.decode("latin-1", errors="replace").split("\n")
                # Check first 3 data lines for the CTRC column
                header = lines_content[0] if len(lines_content) > 0 else ""
                data1 = lines_content[1] if len(lines_content) > 1 else ""
                data2 = lines_content[2] if len(lines_content) > 2 else ""
                data3 = lines_content[3] if len(lines_content) > 3 else ""
                
                ctrc1 = data1.split(";")[2] if len(data1.split(";")) > 2 else ""
                ctrc2 = data2.split(";")[2] if len(data2.split(";")) > 2 else ""
                ctrc3 = data3.split(";")[2] if len(data3.split(";")) > 2 else ""
                
                print(f"[{filial}] Lines: {len(lines_content)}, Size: {len(content)}")
                print(f"[{filial}] CTRCs: {ctrc1} | {ctrc2} | {ctrc3}")
                print(f"[{filial}] Size bytes: {len(content)}")
            except Exception as e:
                print(f"[{filial}] Download FAILED: {e}")

            await context.close()

        await browser.close()

asyncio.run(run())
