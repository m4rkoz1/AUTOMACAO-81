"""
=======================================================
  AUTOMAÇÃO SSW - 036 Relatório
  Domínio: GIA | Usuário: 12345678
  Fluxo: Login → Filial MTZ → Tela 036
         → Excel=S → Datas (01/mês ~ hoje)
         → Clica ► → Baixa arquivo
=======================================================
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    TZ_BR = timezone(timedelta(hours=-3))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────────────
#  CONFIGURAÇÕES
# ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

CONFIG = {
    "dominio":       "GIA",
    "cpf":           "11571959700",
    "usuario":       "12345678",
    "senha":         "123",
    "url_login":     "https://sistema.ssw.inf.br/bin/ssw0422",
    "filial":        "MTZ",
    "relatorio":     "036",
    "pasta_download":    str(BASE_DIR / "downloads_036"),
    "pasta_screenshots": str(BASE_DIR / "screenshots_036"),
    "arquivo_final":     "relatorio_036.xlsx",
    "timeout_ms":    45_000,
}


# ─────────────────────────────────────────────────────
#  LOG (callback substituído pelo servidor)
# ─────────────────────────────────────────────────────
_log_callback = None

def set_log_callback(fn):
    global _log_callback
    _log_callback = fn

def _get_agora():
    return datetime.now(TZ_BR)

def log(msg: str):
    ts = _get_agora().strftime("%H:%M:%S")
    linha = f"[{ts}] {msg}"
    try:
        print(linha)
    except UnicodeEncodeError:
        print(linha.encode("ascii", errors="replace").decode("ascii"))
    if _log_callback:
        _log_callback(linha)


# ─────────────────────────────────────────────────────
#  AUXILIARES
# ─────────────────────────────────────────────────────
async def _screenshot(page, nome: str):
    Path(CONFIG["pasta_screenshots"]).mkdir(exist_ok=True)
    path = str(Path(CONFIG["pasta_screenshots"]) / f"{nome}.png")
    try:
        await page.screenshot(path=path, full_page=True)
        log(f"📸 {path}")
    except Exception:
        pass


def _data_inicio_mes() -> str:
    """Retorna o 1º dia do mês atual no formato DDMMAA."""
    agora = _get_agora()
    return f"01{agora.strftime('%m%y')}"


def _data_hoje() -> str:
    """Retorna a data de hoje no formato DDMMAA."""
    return _get_agora().strftime("%d%m%y")


# ─────────────────────────────────────────────────────
#  PASSO 1: LOGIN
# ─────────────────────────────────────────────────────
async def fazer_login(page):
    log("=== PASSO 1: LOGIN ===")
    log(f"Abrindo: {CONFIG['url_login']}")

    await page.goto(CONFIG["url_login"], wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=CONFIG["timeout_ms"])

    log("Preenchendo credenciais...")
    await page.fill('input[name="f1"]', CONFIG["dominio"])
    await page.fill('input[name="f2"]', CONFIG["cpf"])
    await page.fill('input[name="f3"]', CONFIG["usuario"])
    await page.fill('input[name="f4"]', CONFIG["senha"])

    log("Clicando em Login (►)...")
    await page.click('a[id="5"]')

    try:
        await page.wait_for_function(
            "window.location.href.indexOf('ssw0422') === -1",
            timeout=CONFIG["timeout_ms"]
        )
    except PlaywrightTimeout:
        pass

    if "ssw0422" in page.url:
        await _screenshot(page, "ERRO_login")
        raise Exception("Login falhou! Verifique credenciais.")

    log(f"✔ Login OK → URL: {page.url}")
    await _screenshot(page, "01_pos_login")


# ─────────────────────────────────────────────────────
#  PASSO 2: SELECIONAR FILIAL MTZ E ABRIR RELATÓRIO 036 (POPUP)
# ─────────────────────────────────────────────────────
async def selecionar_filial_e_relatorio(page, context):
    import time as _time

    log("=== PASSO 2: FILIAL MTZ + RELATÓRIO 036 ===")

    # Troca a filial para MTZ via POST (mesma tecnica da automacao 081)
    log(f"Trocando filial para {CONFIG['filial']} via POST...")
    await page.fill('input[id="2"]', CONFIG["filial"])
    await asyncio.sleep(0.3)
    dummy = str(int(_time.time() * 1000))

    await page.evaluate(f"""
        () => {{
            return new Promise((resolve) => {{
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/bin/menu01', true);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.onreadystatechange = function() {{
                    if (xhr.readyState === 4) resolve(xhr.status);
                }};
                xhr.send('act=TRO&f2={CONFIG["filial"]}&f3=36&menu01=1&dummy={dummy}');
            }});
        }}
    """)
    log(f"Sessao atualizada para filial {CONFIG['filial']}.")
    await asyncio.sleep(2)

    await _screenshot(page, "02a_filial_MTZ")

    # Digita 036 no campo Opcao (f3) e captura o popup
    log("Digitando 036 no campo Opcao para abrir popup...")
    campo_opcao = page.locator('input[name="f3"]')
    await campo_opcao.click()
    await asyncio.sleep(0.3)

    # Escuta pelo popup ANTES de digitar
    async with context.expect_page(timeout=30_000) as popup_info:
        await campo_opcao.fill("036")
        await asyncio.sleep(0.3)
        # Dispara o onchange que abre o popup
        await campo_opcao.evaluate("el => { el.dispatchEvent(new Event('change')); }")
        log("Aguardando popup abrir...")

    popup = await popup_info.value
    await popup.wait_for_load_state("domcontentloaded", timeout=30_000)
    try:
        await popup.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeout:
        log("Timeout networkidle no popup (continuando...)")

    # Aceita dialogos no popup tambem
    popup.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

    await _screenshot(popup, "02b_tela_relatorio_popup")
    log(f"Popup do relatorio 036 aberto - URL: {popup.url}")
    return popup


# ─────────────────────────────────────────────────────
#  PASSO 3: PREENCHER CAMPOS DO RELATÓRIO
# ─────────────────────────────────────────────────────
async def preencher_campos_relatorio(page):
    log("=== PASSO 3: PREENCHENDO CAMPOS ===")

    # Excel = S
    log("Preenchendo Excel = S")
    campo_excel = page.locator('input[name="t_excel"]')
    await campo_excel.fill("S")
    log("✔ Excel = S")

    # Data inicial = 01 do mês atual
    dt_ini = _data_inicio_mes()
    log(f"Preenchendo data inicial: {dt_ini}")
    campo_dt_ini = page.locator('input[name="t_dt_ini"]')
    await campo_dt_ini.fill("")
    await campo_dt_ini.type(dt_ini, delay=50)
    log(f"✔ Data inicial = {dt_ini}")

    # Data final = hoje
    dt_fin = _data_hoje()
    log(f"Preenchendo data final: {dt_fin}")
    campo_dt_fin = page.locator('input[name="t_dt_fin"]')
    await campo_dt_fin.fill("")
    await campo_dt_fin.type(dt_fin, delay=50)
    log(f"✔ Data final = {dt_fin}")

    await _screenshot(page, "03_campos_preenchidos")
    log("✔ Todos os campos preenchidos!")


# ─────────────────────────────────────────────────────
#  PASSO 4: CLICAR NO BOTÃO ► E BAIXAR O ARQUIVO
# ─────────────────────────────────────────────────────
async def clicar_gerar_e_baixar(page, context):
    log("=== PASSO 4: GERANDO RELATÓRIO E BAIXANDO ===")

    pasta = Path(CONFIG["pasta_download"])
    pasta.mkdir(exist_ok=True)

    # Limpa downloads antigos
    for ext in ("*.xls*", "*.sswweb", "*.csv"):
        for f in pasta.glob(ext):
            f.unlink(missing_ok=True)

    # Listener de download
    download_futuro = asyncio.get_event_loop().create_future()

    async def handle_download(download):
        if not download_futuro.done():
            download_futuro.set_result(download)

    page.on("download", handle_download)

    # Clica no botão ► (btn_env_periodo)
    log("Clicando no botão ► (btn_env_periodo)...")
    try:
        await page.click('a[id="btn_env_periodo"]')
        log("✔ Clicou no botão com sucesso!")
    except Exception as e:
        log(f"⚠ Erro ao clicar no botão: {e}")
        # Fallback: executa via JavaScript
        log("Tentando via JavaScript...")
        await page.evaluate("() => { const btn = document.getElementById('btn_env_periodo'); if(btn) btn.click(); }")
        log("✔ Clicou via JavaScript")

    await _screenshot(page, "04_pos_clique_gerar")

    # Aguarda o download (até 60s)
    log("Aguardando download... (até 60s)")
    try:
        download = await asyncio.wait_for(download_futuro, timeout=60)
        nome_original = download.suggested_filename or "relatorio_036.xls"
        extensao = Path(nome_original).suffix or ".xls"
        destino = str(pasta / f"relatorio_036_temp{extensao}")
        await download.save_as(destino)
        log(f"✔ Download capturado: {destino}")
        return destino
    except asyncio.TimeoutError:
        log("⚠ Timeout no evento de download — procurando na pasta...")

    # Fallback: procura arquivo recente na pasta
    for _ in range(20):
        await asyncio.sleep(1)
        todos_arqs = [
            f for f in pasta.iterdir()
            if f.suffix.lower() in (".xls", ".xlsx", ".sswweb", ".csv")
        ]
        if todos_arqs:
            mais_recente = max(todos_arqs, key=os.path.getmtime)
            log(f"✔ Arquivo encontrado na pasta: {mais_recente}")
            return str(mais_recente)

    raise Exception("Arquivo não encontrado após 60s. Verifique a tela do SSW.")


# ─────────────────────────────────────────────────────
#  PASSO 5: SALVAR ARQUIVO FINAL
# ─────────────────────────────────────────────────────
def salvar_arquivo_final(arquivo_baixado: str):
    """Copia o arquivo baixado para o nome final na raiz do projeto."""
    import shutil
    import re

    log("=== PASSO 5: SALVANDO ARQUIVO FINAL ===")

    destino = BASE_DIR / CONFIG["arquivo_final"]

    # Lê o conteúdo original
    with open(arquivo_baixado, "rb") as f:
        conteudo = f.read()

    # Tenta decodificar o texto
    for enc in ("latin-1", "cp1252", "utf-8-sig"):
        try:
            texto = conteudo.decode(enc)
            break
        except Exception:
            texto = conteudo.decode("latin-1", errors="replace")

    # Remove caracteres de controle inválidos no Excel
    texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)
    linhas = texto.replace("\r", "").split("\n")

    # Salva como .xlsx usando openpyxl
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Relatório 036"

    for i, linha in enumerate(linhas, 1):
        ws.cell(row=i, column=1, value=linha)

    wb.save(str(destino))
    log(f"✔ Arquivo final salvo: {destino}")
    log(f"   → {len(linhas)} linhas")
    return str(destino)


# ─────────────────────────────────────────────────────
#  PASSO 6: LIMPAR CACHE
# ─────────────────────────────────────────────────────
def limpar_cache():
    log("=== PASSO 6: LIMPANDO CACHE ===")

    for pasta_nome in ("pasta_download", "pasta_screenshots"):
        pasta = Path(CONFIG[pasta_nome])
        if pasta.exists():
            for arq in pasta.iterdir():
                if arq.is_file():
                    try:
                        arq.unlink()
                    except Exception:
                        pass
            log(f"✔ {pasta.name} limpa.")


# ─────────────────────────────────────────────────────
#  ORQUESTRADOR PRINCIPAL
# ─────────────────────────────────────────────────────
async def executar_automacao():
    """
    Ponto de entrada principal da automação 036.
    Retorna True se bem-sucedido, False se houve erro.
    """
    log("╔══════════════════════════════════════════════╗")
    log("║  AUTOMAÇÃO SSW — 036 Relatório MTZ           ║")
    log(f"║  Início: {_get_agora().strftime('%d/%m/%Y %H:%M:%S')}                    ║")
    log("╚══════════════════════════════════════════════╝")

    Path(CONFIG["pasta_download"]).mkdir(exist_ok=True)
    Path(CONFIG["pasta_screenshots"]).mkdir(exist_ok=True)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                downloads_path=CONFIG["pasta_download"],
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1400, "height": 900},
                ignore_https_errors=True,
            )

            page = await context.new_page()
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

            # Passo 1: Login
            await fazer_login(page)

            # Passo 2: Filial MTZ + Relatório 036 (abre popup)
            popup = await selecionar_filial_e_relatorio(page, context)

            # Passo 3: Preencher campos no POPUP (Excel=S, datas)
            await preencher_campos_relatorio(popup)

            # Passo 4: Clicar ► e baixar (no POPUP)
            arquivo_baixado = await clicar_gerar_e_baixar(popup, context)

            # Passo 5: Salvar arquivo final
            salvar_arquivo_final(arquivo_baixado)

            await popup.close()
            await page.close()
            await browser.close()

        # Passo 6: Limpar cache
        limpar_cache()

        log("╔══════════════════════════════════════════════╗")
        log("║  ✔ AUTOMAÇÃO 036 CONCLUÍDA COM SUCESSO!      ║")
        log(f"║  Fim: {_get_agora().strftime('%d/%m/%Y %H:%M:%S')}                       ║")
        log("╚══════════════════════════════════════════════╝")
        return True

    except Exception as e:
        log(f"✘ ERRO NA AUTOMAÇÃO 036: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────
#  EXECUÇÃO DIRETA (python automacao_036.py)
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(executar_automacao())
