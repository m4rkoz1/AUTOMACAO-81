# Script simples de teste rodando localmente
import asyncio
import time
from playwright.async_api import async_playwright

REMOTE_DIR = "c:/opt/automacao" if __import__("sys").platform == "win32" else "/opt/automacao"

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        for filial in ["RJO", "FSP"]:
            context = await browser.new_context(accept_downloads=True, ignore_https_errors=True)
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
                import time
                print(f"[{filial}] Mudando filial para {filial} via POST...")
                await page.fill('input[id="2"]', filial)
                await asyncio.sleep(0.3)
                dummy = str(int(time.time() * 1000))
                
                status_code = await page.evaluate(f"""
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
                print(f"[{filial}] Sessão atualizada (status HTTP {status_code}).")
                await asyncio.sleep(2)

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
                dest = f"test_{filial}.csv"
                await dl.save_as(dest)
                with open(dest, "rb") as f:
                    content = f.read()
                print(f"[{filial}] Tamanho CSV: {len(content)}")
            except Exception as e:
                print(f"[{filial}] ERRO: {e}")

            await context.close()

        await browser.close()

asyncio.run(run())
