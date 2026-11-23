import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path("/opt/automacao")
STORAGE_FILE = BASE_DIR / "storage_state.json"

async def login_vnc():
    os.environ["DISPLAY"] = ":99"
    print("[VNC_LOGIN] Iniciando Chromium no display :99...", flush=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1200,750",
                "--window-position=0,0",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1200, "height": 750},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="pt-BR",
        )

        page = await context.new_page()
        print("[VNC_LOGIN] Navegando para ssw0422...", flush=True)
        await page.goto("https://tms.ssw.inf.br/bin/ssw0422", wait_until="domcontentloaded")

        try:
            print("[VNC_LOGIN] Preenchendo credenciais...", flush=True)
            await page.fill('input[name="f1"]', "GIA")
            await page.fill('input[name="f2"]', "11571959700")
            await page.fill('input[name="f3"]', "12345678")
            await page.fill('input[name="f4"]', "123")
        except Exception as e:
            print(f"[VNC_LOGIN] Erro ao preencher campos: {e}", flush=True)

        print("[VNC_LOGIN] Pronto! Aguardando o usuario resolver o reCAPTCHA e clicar em Login...", flush=True)

        # Aguarda ate o login ser concluido (sai de ssw0422) por ate 10 minutos
        try:
            await page.wait_for_function(
                "window.location.href.indexOf('ssw0422') === -1",
                timeout=600_000
            )
            print("[VNC_LOGIN] Login detectado com sucesso!", flush=True)
            await asyncio.sleep(2)
            await context.storage_state(path=str(STORAGE_FILE))
            print(f"[VNC_LOGIN] storage_state salvo em {STORAGE_FILE}", flush=True)
        except Exception as e:
            print(f"[VNC_LOGIN] Timeout ou erro no login: {e}", flush=True)
        finally:
            await browser.close()
            print("[VNC_LOGIN] Browser finalizado.", flush=True)

if __name__ == "__main__":
    asyncio.run(login_vnc())
