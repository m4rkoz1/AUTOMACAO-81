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
        print("Logging in...")
        await page.goto("https://sistema.ssw.inf.br/bin/ssw0422")
        await page.fill('input[name="f1"]', "GIA")
        await page.fill('input[name="f2"]', "11571959700")
        await page.fill('input[name="f3"]', "12345678")
        await page.fill('input[name="f4"]', "123")
        await page.click('a[id="5"]')
        
        # Wait 5 seconds to settle
        await asyncio.sleep(8)
        
        url = page.url
        print(f"URL is {url}")
        
        # Dump frames
        print(f"Frames: {[f.name for f in page.frames]}")
        
        for idx, frame in enumerate(page.frames):
            html = await frame.content()
            with open(f"/opt/automacao/frame_{idx}.html", "w", encoding="utf-8") as f:
                f.write(html)
        
        await browser.close()

asyncio.run(run())
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

stdin, stdout, stderr = client.exec_command(f'cat << "EOF" > {REMOTE_DIR}/debug_ssw.py\n{script}\nEOF')
stdout.read()

print("Running debug_ssw.py...")
stdin, stdout, stderr = client.exec_command(f'{REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/debug_ssw.py')
print(stdout.read().decode())
print(stderr.read().decode())

print("Grep for <input in frames:")
for idx in range(10):
    stdin, stdout, stderr = client.exec_command(f'grep -Eio "<input[^>]+" {REMOTE_DIR}/frame_{idx}.html | head -n 30')
    out = stdout.read().decode()
    if out.strip():
        print(f"--- frame_{idx}.html ---")
        print(out)

client.close()
