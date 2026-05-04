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
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        
        print("Logging in...")
        await page.goto("https://sistema.ssw.inf.br/bin/ssw0422")
        await page.fill('input[name="f1"]', "GIA")
        await page.fill('input[name="f2"]', "11571959700")
        await page.fill('input[name="f3"]', "12345678")
        await page.fill('input[name="f4"]', "123")
        await page.click('a[id="5"]')
        
        await asyncio.sleep(5)
        
        # Test change branch to FSP
        print("Changing branch to FSP via JS form submit...")
        await page.fill('input[id="2"]', "FSP")
        # Find the form and submit it
        await page.evaluate("document.getElementById('2').form.submit()")
        
        await asyncio.sleep(5)
        
        # Check if it changed
        val = await page.evaluate("document.getElementById('2').value")
        print(f"Branch is now: {val}")
        
        # Test change branch using page.press Enter
        print("Changing branch to TRA via Enter on id=2...")
        await page.fill('input[id="2"]', "TRA")
        await page.press('input[id="2"]', "Enter")
        await asyncio.sleep(5)
        val2 = await page.evaluate("document.getElementById('2').value")
        print(f"Branch after Enter is now: {val2}")
        
        await browser.close()

asyncio.run(run())
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(IP, username=USER, password=PASSWORD)

stdin, stdout, stderr = client.exec_command(f'cat << "EOF" > {REMOTE_DIR}/debug_ssw2.py\n{script}\nEOF')
out_write = stdout.read()

print("Running test...")
stdin, stdout, stderr = client.exec_command(f'{REMOTE_DIR}/venv/bin/python {REMOTE_DIR}/debug_ssw2.py')
print("OUTPUT:", stdout.read().decode())
print("ERROR:", stderr.read().decode())

client.close()
