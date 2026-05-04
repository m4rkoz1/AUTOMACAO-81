import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
REMOTE_DIR = '/opt/automacao'

# Test script: login, change branch, download, compare content
script = r"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

REMOTE_DIR = "/opt/automacao"

async def login(page):
    await page.goto("https://sistema.ssw.inf.br/bin/ssw0422")
    await page.fill('input[name="f1"]', "GIA")
    await page.fill('input[name="f2"]', "11571959700")
    await page.fill('input[name="f3"]', "12345678")
    await page.fill('input[name="f4"]', "123")
    await page.click('a[id="5"]')
    await asyncio.sleep(5)

async def extract_for_branch(context, filial):
    page = await context.new_page()
    page.on("dialog", lambda d: asyncio.create_task(d.accept()))
    
    await login(page)
    
    url_after_login = page.url
    branch_val = await page.evaluate("document.getElementById('2')?.value || 'NOT FOUND'")
    print(f"[{filial}] After login - URL: {url_after_login}, branch field value: {branch_val}")
    
    if filial != "RJO":
        print(f"[{filial}] Changing branch...")
        
        # Method 1: Set value + trigger onchange via JS
        await page.evaluate(f"""
            (function() {{
                var el = document.getElementById('2');
                el.value = '{filial}';
                // Trigger the onchange handler directly
                if (typeof atualizaQuadroIndicadores === 'function') {{
                    atualizaQuadroIndicadores('{filial}');
                }}
                // Also dispatch change event
                el.dispatchEvent(new Event('change'));
            }})();
        """)
        
        await asyncio.sleep(5)
        
        branch_val2 = await page.evaluate("document.getElementById('2')?.value || 'NOT FOUND'")
        print(f"[{filial}] After change - branch field value: {branch_val2}, URL: {page.url}")
    
    # Navigate to the report page
    await page.goto("https://sistema.ssw.inf.br/bin/ssw0052")
    await asyncio.sleep(3)
    
    # Check: what branch does the report page think we're on?
    # Look for any branch indicator in the page
    page_text = await page.evaluate("document.body.innerText.substring(0, 500)")
    print(f"[{filial}] Report page top text: {page_text[:200]}")
    
    # Fill Excel=S
    await page.fill('input[name="relatorio_excel"]', "S")
    
    # Setup download listener
    download_future = asyncio.get_event_loop().create_future()
    async def on_download(dl):
        if not download_future.done():
            download_future.set_result(dl)
    page.on("download", on_download)
    
    # Click "Sem roteirizar"
    await page.click('a[id="btn_envia"]')
    
    try:
        dl = await asyncio.wait_for(download_future, timeout=30)
        dest = f"{REMOTE_DIR}/test_{filial}.csv"
        await dl.save_as(dest)
        print(f"[{filial}] Downloaded to {dest}")
        
        # Read first 3 lines and last 3 lines
        with open(dest, "rb") as f:
            content = f.read()
        lines = content.decode("latin-1", errors="replace").split("\n")
        print(f"[{filial}] Total lines: {len(lines)}")
        print(f"[{filial}] First 2 lines: {lines[:2]}")
        print(f"[{filial}] File size: {len(content)} bytes")
    except Exception as e:
        print(f"[{filial}] Download FAILED: {e}")
    
    await page.close()

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(accept_downloads=True)
        
        await extract_for_branch(context, "RJO")
        await extract_for_branch(context, "FSP")
        
        await browser.close()

asyncio.run(run())
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

stdin, stdout, stderr = client.exec_command(f'cat << "ENDSCRIPT" > {REMOTE_DIR}/test_full.py\n{script}\nENDSCRIPT')
stdout.read()

print("Running full branch test...")
stdin, stdout, stderr = client.exec_command(f'{REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/test_full.py', timeout=120)

with open('test_result.txt', 'w', encoding='utf-8') as f:
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    f.write("STDOUT:\n" + out + "\n\nSTDERR:\n" + err)
    print("STDOUT:", out)
    print("STDERR:", err[:500])

client.close()
