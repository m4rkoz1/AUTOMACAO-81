"""
=======================================================
  AUTOMAÇÃO SSW - 081 CTRCs Disponíveis para Entrega
  Domínio: GIA | Usuário: 12345678
  Fluxo: Login → ssw0052 → Excel=S → Sem roteirizar
         → Salva em RJO.xlsx → Apaga download
=======================================================
"""

import asyncio
import os
import shutil
import time
import glob
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    TZ_BR = timezone(timedelta(hours=-3))

def get_agora():
    return datetime.now(TZ_BR)


from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import openpyxl

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
    "url_relatorio": "https://sistema.ssw.inf.br/bin/ssw0052",
    "pasta_download":    str(BASE_DIR / "downloads"),
    "pasta_screenshots": str(BASE_DIR / "screenshots"),
    "timeout_ms":    45_000,
}

# Callback de log (será substituído pelo servidor web)
_log_callback = None

def set_log_callback(fn):
    global _log_callback
    _log_callback = fn

def log(msg: str):
    ts = get_agora().strftime("%H:%M:%S")
    linha = f"[{ts}] {msg}"
    print(linha)
    if _log_callback:
        _log_callback(linha)


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
    # IDs numéricos não aceitam seletor CSS #5, usar atributo [id="5"]
    await page.click('a[id="5"]')

    # Aguarda sair da página de login
    try:
        await page.wait_for_function(
            "window.location.href.indexOf('ssw0422') === -1",
            timeout=CONFIG["timeout_ms"]
        )
    except PlaywrightTimeout:
        pass

    url_atual = page.url
    if "ssw0422" in url_atual:
        await _screenshot(page, "ERRO_login")
        raise Exception("Login falhou! Verifique credenciais. Screenshot: screenshots/ERRO_login.png")

    log(f"✔ Login OK → URL: {url_atual}")
    await _screenshot(page, "01_pos_login")


# ─────────────────────────────────────────────────────
#  PASSO 2: NAVEGAR PARA ssw0052
# ─────────────────────────────────────────────────────
async def navegar_para_relatorio(page):
    log("=== PASSO 2: NAVEGANDO PARA ssw0052 ===")
    log(f"Abrindo: {CONFIG['url_relatorio']}")

    await page.goto(CONFIG["url_relatorio"], wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=CONFIG["timeout_ms"])
    except PlaywrightTimeout:
        log("⚠ Timeout (continuando...)")

    log(f"✔ Página ssw0052 carregada — URL: {page.url}")
    await _screenshot(page, "02_ssw0052")


# ─────────────────────────────────────────────────────
#  PASSO 3: PREENCHER EXCEL=S E CLICAR SEM ROTEIRIZAR
# ─────────────────────────────────────────────────────
async def preencher_e_gerar(page, context):
    log("=== PASSO 3: CONFIGURANDO Excel=S ===")

    # Encontra o campo Excel via JavaScript (busca label + input próximo)
    resultado = await page.evaluate("""
        () => {
            const tds = Array.from(document.querySelectorAll('td'));
            for (let i = 0; i < tds.length; i++) {
                const texto = tds[i].innerText.trim().toLowerCase();
                if (texto.startsWith('excel')) {
                    // Próximo td pode ter o input
                    const prox = tds[i + 1];
                    if (prox) {
                        const inp = prox.querySelector('input');
                        if (inp) return {name: inp.name, id: inp.id, value: inp.value};
                    }
                }
            }
            // Fallback: pega todos os inputs e retorna nomes/valores
            return Array.from(document.querySelectorAll('input[type=text]'))
                    .map(el => ({name:el.name, id:el.id, value:el.value}));
        }
    """)

    log(f"Resultado campo Excel: {resultado}")

    campo_excel_name = None

    if isinstance(resultado, dict) and resultado.get("name"):
        campo_excel_name = resultado["name"]
        log(f"Campo Excel encontrado: name={campo_excel_name}")
        await page.fill(f'input[name="{campo_excel_name}"]', "S")
    else:
        # Tenta preencher pelo último campo de texto que aceita S/N
        log("Buscando campo Excel pelo valor padrão 'N'...")
        todos_inputs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input[type=text]'))
                    .map((el,i) => ({idx:i, name:el.name, id:el.id, value:el.value}))
        """)
        log(f"Inputs encontrados: {todos_inputs}")

        # Procura input com valor "N" (padrão do campo Excel) mais próximo do final
        for inp in reversed(todos_inputs):
            if inp.get("value", "").upper() in ("N", "S"):
                campo_excel_name = inp["name"]
                log(f"Campo Excel (por valor N/S): name={campo_excel_name}")
                await page.fill(f'input[name="{campo_excel_name}"]', "S")
                break

    if not campo_excel_name:
        log("⚠ Campo Excel não encontrado automaticamente — tentando por posição")
        # Estratégia de fallback: pegar o último campo de 1 char
        await page.evaluate("""
            () => {
                const inputs = Array.from(document.querySelectorAll('input[type=text]'));
                const alvo = inputs.reverse().find(el => el.maxLength === 1 || el.size <= 2);
                if (alvo) alvo.value = 'S';
            }
        """)

    await _screenshot(page, "03_excel_S_preenchido")
    log("✔ Excel=S configurado!")

    # ── Clica em "Sem roteirizar" ─────────────────
    log("=== PASSO 3b: CLICANDO EM 'SEM ROTEIRIZAR' ===")

    # Cria um listener para capturar o download antes de clicar
    async with context.expect_page() as nova_pagina_info:
        # Tentativa 1: clicar pelo texto exato
        try:
            link = page.get_by_text("Sem roteirizar", exact=False).first
            await link.click(timeout=5000)
            log("✔ Clicou em 'Sem roteirizar' (por texto)")
        except Exception:
            # Tentativa 2: via JavaScript (busca link com texto contendo 'roteirizar')
            log("Tentando clicar via JavaScript...")
            await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const alvo = links.find(a => 
                        a.innerText.toLowerCase().includes('sem roteirizar') || 
                        a.innerText.toLowerCase().includes('roteirizar')
                    );
                    if (alvo) alvo.click();
                }
            """)
            log("✔ Clicou via JavaScript")

    nova_pagina = await nova_pagina_info.value
    return nova_pagina


async def aguardar_e_baixar(context, page):
    """
    Aguarda o download do arquivo Excel gerado pelo SSW.
    O SSW geralmente abre uma nova aba/popup com o arquivo.
    """
    log("=== PASSO 3c: AGUARDANDO DOWNLOAD ===")
    pasta = Path(CONFIG["pasta_download"])
    pasta.mkdir(exist_ok=True)

    # Limpa downloads antigos do SSW antes
    for f in pasta.glob("*.xls*"):
        f.unlink()

    # Estratégia 1: aguardar evento de download direto
    try:
        async with page.expect_download(timeout=30_000) as dl_info:
            # Se ainda não disparou o download, tenta clicar novamente
            pass
        download = await dl_info.value
        destino = str(pasta / download.suggested_filename)
        await download.save_as(destino)
        log(f"✔ Download recebido → {destino}")
        return destino
    except Exception as e:
        log(f"⚠ Download direto não detectado ({e}). Tentando via nova aba...")

    # Estratégia 2: aguardar nova aba com o arquivo
    try:
        async with context.expect_page(timeout=20_000) as nova_info:
            pass
        nova = await nova_info.value
        await nova.wait_for_load_state("domcontentloaded", timeout=20_000)
        url_nova = nova.url
        log(f"Nova aba aberta: {url_nova}")

        # Baixa o arquivo via request com os cookies da sessão
        if ".xls" in url_nova.lower() or "download" in url_nova.lower():
            import httpx
            cookies = await context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(url_nova, headers={"Cookie": cookie_str}, follow_redirects=True)
                nome_arq = f"ssw_relatorio_{get_agora().strftime('%Y%m%d_%H%M%S')}.xls"
                destino = str(pasta / nome_arq)
                with open(destino, "wb") as f:
                    f.write(resp.content)
                log(f"✔ Arquivo baixado via nova aba → {destino}")
                return destino
        await nova.close()
    except Exception as e:
        log(f"⚠ Nova aba não detectada ({e})")

    # Estratégia 3: procurar arquivo recente na pasta
    log("Aguardando arquivo aparecer na pasta downloads (10s)...")
    for _ in range(20):
        await asyncio.sleep(0.5)
        arquivos = sorted(pasta.glob("*.xls*"), key=os.path.getmtime, reverse=True)
        if arquivos:
            log(f"✔ Arquivo encontrado: {arquivos[0]}")
            return str(arquivos[0])

    raise Exception("Não foi possível detectar o arquivo baixado! Verifique a pasta downloads/")


# ─────────────────────────────────────────────────────
#  PASSO 4: COPIAR DADOS PARA RJO.xlsx
# ─────────────────────────────────────────────────────
import re as _re

def _parsear_sswweb(arquivo: str):
    """
    Lê o relatório SSW de largura fixa (.sswweb) e extrai as linhas de CTRCs.
    O cabeçalho do relatório define as colunas; usamos regex para extrair cada CTRC.
    Retorna (cabecalho_list, dados_list_of_lists)
    """
    log(f"Parseando arquivo SSW formato texto: {arquivo}")

    with open(arquivo, "rb") as f:
        raw = f.read()

    for enc in ("latin-1", "cp1252", "utf-8-sig"):
        try:
            texto = raw.decode(enc)
            break
        except Exception:
            texto = raw.decode("latin-1", errors="replace")

    linhas = texto.replace("\r", "").split("\n")

    CAB = ["SETOR", "CTRC", "NF", "PAGADOR", "DESTINATARIO",
           "ENDERECO", "CIDADE", "BAIRRO", "CEP",
           "PREVISAO", "AGENDAMENTO", "VAL_MERC",
           "KG", "M3", "QVOL", "FRETE", "ULT_OCOR",
           "PREV_CHEGADA", "MANIFESTO", "SERV_ADIC", "PER",
           "INSTRUCAO_ENTREGA"]

    # Regex para linha de CTRC (começa com 2 espaços + código alfanumérico + hífen)
    RE_CTRC = _re.compile(
        r'^  ([A-Z0-9]+-\d)\s+'
        r'(\S+)\s+'
        r'(.{14})'
        r'(.{9})'
        r'(.{18})'
        r'(.{6})'
        r'(.{6})'
        r'(.{9})'
        r'(\S+)\s+'
        r'(.{11})'
        r'(.{9})'
        r'(.{6})'
        r'(.{5})'
        r'(.{7})'
        r'(.{6})'
        r'(.{8})'
        r'(.)\s+'
        r'(.{11})'
        r'(.{14})'
        r'(.{8})'
        r'(\S*)'
    )

    RE_SETOR    = _re.compile(r'^SETOR:\s*(.+)')
    RE_INSTRUCAO = _re.compile(r'^\s+INSTRUCAO ENTREGA:\s*(.*)')
    RE_CTRC_SIMPLES = _re.compile(r'^  ([A-Z0-9]{3,}\d+-\d)')

    setor_atual = ""
    dados = []
    linha_atual = None

    for linha in linhas:
        # Detecta setor
        m = RE_SETOR.match(linha.strip())
        if m:
            setor_atual = m.group(1).strip()
            continue

        # Detecta instrução de entrega (linha complementar)
        m_instr = RE_INSTRUCAO.match(linha)
        if m_instr and linha_atual is not None:
            linha_atual[-1] = m_instr.group(1).strip()
            continue

        # Detecta linha de CTRC
        if not RE_CTRC_SIMPLES.match(linha):
            # Salva a linha anterior se havia uma
            if linha_atual is not None:
                dados.append(linha_atual)
                linha_atual = None
            continue

        # Salva linha anterior
        if linha_atual is not None:
            dados.append(linha_atual)

        # Extrai campos por posição (a linha tem largura fixa)
        # Garante tamanho mínimo
        lp = linha.ljust(220)

        # Posições baseadas no separador da linha de cabeçalho:
        # ------------+-----------+--------------+---------+------------------+------+------+---------+-----+-----------+---------+------+-----+-------+------+--------+-+-----------+--------------+--------+---
        # 0           13          25             39        49                 67     73     79        89    94         105       114   120   125    132    138      147 149         161           175      183
        try:
            ctrc       = lp[2:18].strip()
            nf         = lp[18:27].strip()
            pagador    = lp[27:41].strip()
            destinat   = lp[41:50].strip()
            endereco   = lp[50:68].strip()
            cidade     = lp[68:74].strip()
            bairro     = lp[74:80].strip()
            cep        = lp[80:89].strip()
            previsao   = lp[89:94].strip()
            agendamento= lp[94:105].strip()
            val_merc   = lp[105:114].strip().replace(".", "").replace(",", ".")
            kg         = lp[114:120].strip()
            m3         = lp[120:125].strip()
            qvol       = lp[125:131].strip()
            frete      = lp[131:137].strip().replace(".", "").replace(",", ".")
            ult_ocor   = lp[137:145].strip()
            b_flag     = lp[145:147].strip()
            prev_cheg  = lp[147:158].strip()
            manifesto  = lp[158:171].strip()
            serv_adic  = lp[171:179].strip()
            periodo    = lp[179:182].strip()
        except Exception:
            continue

        linha_atual = [
            setor_atual, ctrc, nf, pagador, destinat,
            endereco, cidade, bairro, cep,
            previsao, agendamento, val_merc,
            kg, m3, qvol, frete, ult_ocor,
            prev_cheg, manifesto, serv_adic, periodo,
            ""  # instrucao_entrega (preenchida nas linhas seguintes)
        ]

    if linha_atual is not None:
        dados.append(linha_atual)

    log(f"✔ Parser concluído: {len(dados)} CTRCs extraídos")
    return CAB, dados


def copiar_para_planilha(filial: str, arquivo_baixado: str):
    log(f"=== PASSO 4: COPIANDO DADOS PARA {filial}.xlsx ===")
    log(f"Lendo arquivo: {arquivo_baixado}")

    destino = BASE_DIR / f"{filial}.xlsx"

    # Lê o arquivo como texto puro (encoding latin-1, padrão SSW)
    with open(arquivo_baixado, "rb") as f:
        conteudo = f.read()

    for enc in ("latin-1", "cp1252", "utf-8-sig"):
        try:
            texto = conteudo.decode(enc)
            break
        except Exception:
            texto = conteudo.decode("latin-1", errors="replace")

    # Remove caracteres de controle inválidos no Excel (mantém só printáveis + \n\t)
    import re as _re2
    texto = _re2.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)

    # Divide em linhas e remove \r
    linhas = texto.replace("\r", "").split("\n")
    log(f"Arquivo lido: {len(linhas)} linhas")

    # Cria a planilha da filial do zero (sobrescreve se já existir)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = filial

    # Cola cada linha na coluna A — sem formatação alguma
    for i, linha in enumerate(linhas, 1):
        ws.cell(row=i, column=1, value=linha)

    wb.save(str(destino))
    log(f"✔ {filial}.xlsx salvo: {destino}")
    log(f"   → {len(linhas)} linhas copiadas")
    return str(destino)

# ─────────────────────────────────────────────────────
#  PASSO 5: LIMPAR CACHE (APAGAR ARQUIVOS TEMPORÁRIOS)
# ─────────────────────────────────────────────────────
def limpar_cache():
    log("=== PASSO 5: LIMPANDO CACHE TEMPORÁRIO ===")
    
    # Limpa pasta de downloads
    pasta_dl = Path(CONFIG["pasta_download"])
    if pasta_dl.exists():
        for arq in pasta_dl.iterdir():
            if arq.is_file():
                try:
                    arq.unlink()
                except Exception:
                    pass
        log(f"✔ Pasta de downloads limpa.")

    # Limpa pasta de screenshots
    pasta_ss = Path(CONFIG["pasta_screenshots"])
    if pasta_ss.exists():
        for arq in pasta_ss.iterdir():
            if arq.is_file():
                try:
                    arq.unlink()
                except Exception:
                    pass
        log(f"✔ Pasta de screenshots limpa.")



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


# ─────────────────────────────────────────────────────
#  ORQUESTRADOR PRINCIPAL
# ─────────────────────────────────────────────────────
async def executar_automacao():
    """
    Ponto de entrada principal da automação.
    Retorna True se bem-sucedido, False se houve erro.
    """
    log("╔══════════════════════════════════════════════╗")
    log("║  AUTOMAÇÃO SSW — 081 CTRCs p/ Entrega        ║")
    log(f"║  Início: {get_agora().strftime('%d/%m/%Y %H:%M:%S')}                    ║")
    log("╚══════════════════════════════════════════════╝")

    Path(CONFIG["pasta_download"]).mkdir(exist_ok=True)
    Path(CONFIG["pasta_screenshots"]).mkdir(exist_ok=True)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,          # True = sem janela (modo servidor)
                downloads_path=CONFIG["pasta_download"],
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1400, "height": 900},
                ignore_https_errors=True,
            )
            FILIAIS = ["RJO", "FSP", "TRA", "BAR", "ARA"]

            # Limpa todas as planilhas existentes ANTES da extração
            for filial in FILIAIS:
                old_file = BASE_DIR / f"{filial}.xlsx"
                if old_file.exists():
                    old_file.unlink()

            for filial in FILIAIS:
                log(f"\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                log(f" INICIANDO EXTRAÇÃO: FILIAL {filial}")
                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                page = await context.new_page()
                page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

                # Passo 1: Login
                await fazer_login(page)

                # Trocar filial se não for a padrão (RJO)
                if filial != "RJO":
                    import time
                    log(f"Mudando filial para {filial} via chamada POST TRO...")
                    await page.fill('input[id="2"]', filial)
                    await asyncio.sleep(0.3)
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
                    log(f"Sessão atualizada para filial {filial}.")
                    await asyncio.sleep(2)

                # Passo 2: Navegar
                await navegar_para_relatorio(page)

                # Passo 3: Preencher Excel=S + clicar Sem roteirizar
                log("=== PASSO 3: PREENCHENDO EXCEL=S ===")
                await _preencher_campo_excel(page)
                await _screenshot(page, f"03_excel_S_{filial}")

                log("=== PASSO 3b: CLICANDO SEM ROTEIRIZAR ===")
                arquivo_baixado = await _clicar_sem_roteirizar_e_baixar(page, context)

                # Passo 4: Copiar para Planilha (Filial.xlsx)
                planilha_path = copiar_para_planilha(filial, arquivo_baixado)
                log(f"✔ Planilha {filial} pronta: {planilha_path}")

                await page.close()

            await browser.close()
            
        # Passo 5: Limpar Cache
        limpar_cache()

        log("╔══════════════════════════════════════════════╗")
        log("║  ✔ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!          ║")
        log("║  Todas as planilhas (RJO, FSP, TRA, BAR, ARA)║")
        log("║  foram processadas e salvas.                 ║")
        log(f"║  Fim: {get_agora().strftime('%d/%m/%Y %H:%M:%S')}                       ║")
        log("╚══════════════════════════════════════════════╝")
        return True

    except Exception as e:
        log(f"✘ ERRO NA AUTOMAÇÃO: {e}")
        import traceback
        traceback.print_exc()
        return False


async def _preencher_campo_excel(page):
    """Preenche o campo Excel (relatorio_excel) com 'S' e Data Prev. (data_prev_man)."""
    from datetime import timedelta
    try:
        await page.fill('input[name="relatorio_excel"]', "S")
        log("✔ Campo Excel (relatorio_excel) preenchido com S")

        data_futura = get_agora() + timedelta(days=10)
        str_data = data_futura.strftime("%d%m%y")
        try:
            await page.fill('input[name="data_prev_man"]', str_data)
            log(f"✔ Campo data_prev_man preenchido com {str_data} (+10 dias)")
        except Exception as e2:
            log(f"⚠ Erro ao preencher data_prev_man: {e2}")

    except Exception as e:
        log(f"⚠ Erro ao preencher relatorio_excel: {e}")



async def _clicar_sem_roteirizar_e_baixar(page, context):
    """Clica no link Sem roteirizar e captura o download."""
    Path(CONFIG["pasta_download"]).mkdir(exist_ok=True)
    pasta = Path(CONFIG["pasta_download"])

    # Limpa downloads antigos (.xls*, .sswweb, .csv)
    for ext in ("*.xls*", "*.sswweb", "*.csv"):
        for f in pasta.glob(ext):
            f.unlink(missing_ok=True)

    # Inicia escuta de download
    download_futuro = asyncio.get_event_loop().create_future()

    async def handle_download(download):
        if not download_futuro.done():
            download_futuro.set_result(download)

    page.on("download", handle_download)

    # Clica diretamente pelo ID do botão "Sem roteirizar"
    try:
        await page.click('a[id="btn_envia"]')
        log("✔ Clicou no botão 'Sem roteirizar' (id: btn_envia) com sucesso!")
    except Exception as e:
        log(f"⚠ Erro ao clicar no botão btn_envia: {e}")

    await _screenshot(page, "04_pos_clique")

    # Aguarda o download acontecer (até 45s)
    log("Aguardando download... (até 45s)")
    try:
        download = await asyncio.wait_for(download_futuro, timeout=45)
        # Garante nome unico para não reler lixo
        extensao = Path(download.suggested_filename).suffix if download.suggested_filename else ".csv"
        unico_str = get_agora().strftime('%Y%m%d_%H%M%S')
        destino = str(pasta / f"ssw_ext_{unico_str}{extensao}")
        await download.save_as(destino)
        log(f"✔ Download capturado: {destino}")
        return destino
    except asyncio.TimeoutError:
        log("⚠ Timeout no evento de download — procurando na pasta...")

    # Fallback: procura qualquer arquivo recente na pasta (.xls*, .sswweb, .csv)
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

    raise Exception("Arquivo não encontrado após 45s. Verifique a tela do SSW.")


# ─────────────────────────────────────────────────────
#  EXECUÇÃO DIRETA (python automacao_ssw.py)
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(executar_automacao())
