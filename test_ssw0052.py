import paramiko

IP = '192.168.5.26'
USER = 'root'
PASSWORD = 'gustgia*'
REMOTE_DIR = '/opt/automacao'

script = """
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://sistema.ssw.inf.br/bin/ssw0422")
        await page.fill('input[name="f1"]', "GIA")
        await page.fill('input[name="f2"]', "11571959700")
        await page.fill('input[name="f3"]', "12345678")
        await page.fill('input[name="f4"]', "123")
        await page.click('a[id="5"]')
        await asyncio.sleep(5)
        
        # Go to ssw0052 and dump inputs to see if there is a branch field
        await page.goto("https://sistema.ssw.inf.br/bin/ssw0052")
        await asyncio.sleep(3)
        html = await page.content()
        with open("/opt/automacao/ssw0052.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        await browser.close()

asyncio.run(run())
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

stdin, stdout, stderr = client.exec_command(f'cat << "EOF" > {REMOTE_DIR}/debug_ssw3.py\n{script}\nEOF')
out_write = stdout.read()

print("Running test...")
stdin, stdout, stderr = client.exec_command(f'{REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/debug_ssw3.py')
print(stdout.read().decode())

print("Grep for <input in ssw0052:")
stdin, stdout, stderr = client.exec_command(f'grep -Eio "<input[^>]+" {REMOTE_DIR}/ssw0052.html | head -n 40')
print(stdout.read().decode())

client.close()
