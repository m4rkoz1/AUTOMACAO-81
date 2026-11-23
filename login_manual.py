"""
===========================================================
  AUTENTICAÇÃO MANUAL SSW - GERADOR DE SESSÃO
  Abre navegador visível para o usuário clicar no reCAPTCHA.
  Ao concluir o login, salva o 'storage_state.json' e
  já envia diretamente para o servidor Proxmox (192.168.5.26).
===========================================================
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent
STORAGE_FILE = BASE_DIR / "storage_state.json"

PROXMOX_IP = "192.168.5.26"
PROXMOX_USER = "root"
PROXMOX_PASS = "gustgia*"
PROXMOX_DIR = "/opt/automacao"

async def login_interativo():
    print("\n" + "=" * 60)
    print(" 🚀 INICIANDO NAVEGADOR VISÍVEL PARA LOGIN NO SSW")
    print("=" * 60)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="pt-BR",
        )

        page = await context.new_page()

        print("\n[1/3] Acessando tela de login SSW...")
        await page.goto("https://tms.ssw.inf.br/bin/ssw0422", wait_until="domcontentloaded")

        try:
            print("[2/3] Preenchendo credenciais...")
            await page.fill('input[name="f1"]', "GIA")
            await page.fill('input[name="f2"]', "11571959700")
            await page.fill('input[name="f3"]', "12345678")
            await page.fill('input[name="f4"]', "123")
        except Exception as e:
            print(f"Aviso ao preencher campos: {e}")

        print("\n" + "!" * 60)
        print(" 👉 AGUARDANDO SUA INTERAÇÃO NO NAVEGADOR:")
        print(" 1. Clique no checkbox do reCAPTCHA ('Não sou um robô').")
        print(" 2. Resolva qualquer desafio de imagens se solicitado.")
        print(" 3. Clique no botão Entrar / Confirmar (►).")
        print("!" * 60 + "\n")

        # Aguarda até sair da tela ssw0422 (timeout 5 minutos)
        try:
            await page.wait_for_function(
                "window.location.href.indexOf('ssw0422') === -1",
                timeout=300_000
            )
        except Exception:
            print("\n❌ Tempo limite esgotado (5 minutos) sem confirmação de login.")
            await browser.close()
            return False

        print("\n✔ Login detectado com sucesso!")
        await asyncio.sleep(2)

        # Salva o arquivo de estado de sessão com cookies e tokens
        await context.storage_state(path=str(STORAGE_FILE))
        print(f"✔ Sessão salva localmente em: {STORAGE_FILE}")

        await browser.close()

    # Envia automaticamente para o servidor Proxmox
    print(f"\n[3/3] Enviando sessão para o servidor Proxmox ({PROXMOX_IP})...")
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(PROXMOX_IP, username=PROXMOX_USER, password=PROXMOX_PASS, timeout=10)
        sftp = ssh.open_sftp()
        sftp.put(str(STORAGE_FILE), f"{PROXMOX_DIR}/storage_state.json")
        sftp.close()
        ssh.close()
        print(f"✔ storage_state.json enviado com sucesso para {PROXMOX_DIR}/storage_state.json no Proxmox!")
    except Exception as e_ssh:
        print(f"⚠ Não foi possível enviar automaticamente via SSH para o Proxmox: {e_ssh}")
        print("Você pode enviar executando 'python update_proxmox.py'.")

    print("\n" + "=" * 60)
    print(" 🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
    print(" A automação agora possui sessão ativa e rodará sem reCAPTCHA.")
    print("=" * 60 + "\n")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(login_interativo())
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
