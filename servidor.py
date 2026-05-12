"""
=======================================================
  SERVIDOR WEB - Agendador da Automação SSW
  Acesse: http://localhost:5000
=======================================================
"""

import asyncio
import json
import os
import threading
from collections import deque

GLOBAL_LOCK = threading.Lock()
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    TZ_BR = ZoneInfo("America/Sao_Paulo")
except ImportError:
    TZ_BR = timezone(timedelta(hours=-3))

def get_agora():
    return datetime.now(TZ_BR)

from pathlib import Path

from flask import Flask, jsonify, render_template_string, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import automacao_ssw
import automacao_036

# ─────────────────────────────────────────────────────
#  ESTADO GLOBAL — 081
# ─────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config_agendamentos.json"

app       = Flask(__name__)
scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

# Buffer de logs (últimas 500 linhas)
LOG_BUFFER  = deque(maxlen=500)
STATUS      = {"rodando": False, "ultimo": None, "proximo": None}

def adicionar_log(linha: str):
    LOG_BUFFER.append(linha)

automacao_ssw.set_log_callback(adicionar_log)

# ─────────────────────────────────────────────────────
#  ESTADO GLOBAL — 036
# ─────────────────────────────────────────────────────
CONFIG_FILE_036 = BASE_DIR / "config_agendamentos_036.json"

LOG_BUFFER_036  = deque(maxlen=500)
STATUS_036      = {"rodando": False, "ultimo": None, "proximo": None}

def adicionar_log_036(linha: str):
    LOG_BUFFER_036.append(linha)

automacao_036.set_log_callback(adicionar_log_036)


# ─────────────────────────────────────────────────────
#  AGENDAMENTOS: salvar / carregar
# ─────────────────────────────────────────────────────
def salvar_config(agendamentos: list):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(agendamentos, f, ensure_ascii=False, indent=2)


def carregar_config() -> list:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def reconstruir_scheduler(agendamentos: list):
    """Remove todos os jobs da 081 e recria com a lista atual."""
    for job in scheduler.get_jobs():
        if not job.id.startswith("job036_"):
            job.remove()

    for ag in agendamentos:
        hora, minuto = ag["hora"].split(":")
        scheduler.add_job(
            rodar_automacao_job,
            CronTrigger(hour=int(hora), minute=int(minuto)),
            id=f"job_{ag['hora'].replace(':','_')}",
            name=f"Automação SSW {ag['hora']}",
            replace_existing=True,
        )

    atualizar_proximo()


def atualizar_proximo():
    jobs = [j for j in scheduler.get_jobs() if not j.id.startswith("job036_")]
    if jobs:
        proximos = [getattr(j, "next_run_time", None) for j in jobs]
        proximos = [p for p in proximos if p is not None]
        if proximos:
            prox = min(proximos)
            STATUS["proximo"] = prox.strftime("%d/%m/%Y %H:%M")
            return
    STATUS["proximo"] = None


# ─────────────────────────────────────────────────────
#  EXECUTAR AUTOMAÇÃO (thread separada)
# ─────────────────────────────────────────────────────
def rodar_automacao_job():
    if STATUS["rodando"]:
        adicionar_log("[AVISO] Automação já está rodando, pulando esta execução.")
        return

    adicionar_log("[FILA] Aguardando liberação do sistema para iniciar 081...")
    with GLOBAL_LOCK:
        STATUS["rodando"] = True
        STATUS["ultimo"]  = get_agora().strftime("%d/%m/%Y %H:%M:%S")
        adicionar_log(f"[AGENDAMENTO] Iniciando automação — {STATUS['ultimo']}")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sucesso = loop.run_until_complete(automacao_ssw.executar_automacao())
            loop.close()

            if sucesso:
                adicionar_log("[SUCESSO] Automação concluída ✔")
            else:
                adicionar_log("[ERRO] Automação terminou com erro ✘")
        except Exception as e:
            adicionar_log(f"[ERRO CRÍTICO] {e}")
        finally:
            STATUS["rodando"] = False
            atualizar_proximo()


# ─────────────────────────────────────────────────────
#  ROTAS DA API
# ─────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    atualizar_proximo()
    rjo = BASE_DIR / "RJO.xlsx"
    return jsonify({
        "rodando": STATUS["rodando"],
        "ultimo":  STATUS["ultimo"],
        "proximo": STATUS["proximo"],
        "rjo_existe": rjo.exists(),
        "rjo_modificado": datetime.fromtimestamp(rjo.stat().st_mtime, TZ_BR).strftime("%d/%m/%Y %H:%M:%S")
                          if rjo.exists() else None,
    })


@app.route("/api/logs")
def api_logs():
    ultimo_idx = int(request.args.get("desde", 0))
    todas = list(LOG_BUFFER)
    novas = todas[ultimo_idx:]
    return jsonify({"logs": novas, "total": len(todas)})


@app.route("/api/agendamentos", methods=["GET"])
def api_lista_agendamentos():
    return jsonify(carregar_config())


@app.route("/api/agendamentos", methods=["POST"])
def api_salvar_agendamentos():
    data = request.get_json()
    agendamentos = sorted(data.get("agendamentos", []), key=lambda x: x["hora"])
    salvar_config(agendamentos)
    reconstruir_scheduler(agendamentos)
    return jsonify({"ok": True, "quantidade": len(agendamentos)})


@app.route("/api/executar", methods=["POST"])
def api_executar_agora():
    if STATUS["rodando"]:
        return jsonify({"ok": False, "msg": "Automação já está rodando!"})
    t = threading.Thread(target=rodar_automacao_job, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "Automação iniciada!"})


from flask import Flask, jsonify, render_template_string, request, send_file

@app.route("/api/abrir_rjo", methods=["POST"])
def api_abrir_rjo():
    rjo = BASE_DIR / "RJO.xlsx"
    if rjo.exists():
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(rjo))
            else:
                adicionar_log("[AVISO] Abertura direta de arquivo não suportada neste ambiente (Linux/Docker).")
        except Exception as e:
            adicionar_log(f"[ERRO] Falha ao abrir arquivo: {e}")
        return jsonify({"ok": True})
    return jsonify({"ok": False, "msg": "RJO.xlsx não encontrado"})


@app.route("/download/<filial>.xlsx", methods=["GET"])
def download_filial(filial):
    """Rota dinâmica para o Power BI puxar a planilha da filial especificada."""
    # Garante que só puxará planilhas com 3 letras por segurança (ex: RJO, FSP)
    filial = filial.upper()
    arquivo = BASE_DIR / f"{filial}.xlsx"
    if arquivo.exists():
        return send_file(
            arquivo,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True
        )
    return f"Planilha {filial}.xlsx ainda não foi gerada", 404


@app.route("/api/planilhas", methods=["GET"])
def api_planilhas():
    planilhas = []
    for file in BASE_DIR.glob("*.xlsx"):
        planilhas.append({
            "nome": file.name,
            "tamanho": file.stat().st_size,
            "modificado": datetime.fromtimestamp(file.stat().st_mtime, TZ_BR).strftime("%d/%m/%Y %H:%M:%S")
        })
    return jsonify(planilhas)

# ═══════════════════════════════════════════════════════
#  ROTAS DA API — 036 (completamente separadas)
# ═══════════════════════════════════════════════════════
def salvar_config_036(agendamentos: list):
    with open(CONFIG_FILE_036, "w", encoding="utf-8") as f:
        json.dump(agendamentos, f, ensure_ascii=False, indent=2)

def carregar_config_036() -> list:
    if CONFIG_FILE_036.exists():
        with open(CONFIG_FILE_036, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def reconstruir_scheduler_036(agendamentos: list):
    for job in scheduler.get_jobs():
        if job.id.startswith("job036_"):
            job.remove()
    for ag in agendamentos:
        hora, minuto = ag["hora"].split(":")
        scheduler.add_job(
            rodar_automacao_036_job,
            CronTrigger(hour=int(hora), minute=int(minuto)),
            id=f"job036_{ag['hora'].replace(':','_')}",
            name=f"Automação 036 {ag['hora']}",
            replace_existing=True,
        )
    atualizar_proximo_036()

def atualizar_proximo_036():
    jobs = [j for j in scheduler.get_jobs() if j.id.startswith("job036_")]
    if jobs:
        proximos = [getattr(j, "next_run_time", None) for j in jobs]
        proximos = [p for p in proximos if p is not None]
        if proximos:
            STATUS_036["proximo"] = min(proximos).strftime("%d/%m/%Y %H:%M")
            return
    STATUS_036["proximo"] = None

def rodar_automacao_036_job():
    if STATUS_036["rodando"]:
        adicionar_log_036("[AVISO] Automação 036 já está rodando, pulando.")
        return
    
    adicionar_log_036("[FILA] Aguardando liberação do sistema para iniciar 036...")
    with GLOBAL_LOCK:
        STATUS_036["rodando"] = True
        STATUS_036["ultimo"] = get_agora().strftime("%d/%m/%Y %H:%M:%S")
        adicionar_log_036(f"[AGENDAMENTO] Iniciando automação 036 — {STATUS_036['ultimo']}")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            sucesso = loop.run_until_complete(automacao_036.executar_automacao())
            loop.close()
            if sucesso:
                adicionar_log_036("[SUCESSO] Automação 036 concluída ✔")
            else:
                adicionar_log_036("[ERRO] Automação 036 terminou com erro ✘")
        except Exception as e:
            adicionar_log_036(f"[ERRO CRÍTICO] {e}")
        finally:
            STATUS_036["rodando"] = False
            atualizar_proximo_036()

@app.route("/036/api/status")
def api_status_036():
    atualizar_proximo_036()
    arq = BASE_DIR / automacao_036.CONFIG["arquivo_final"]
    return jsonify({
        "rodando": STATUS_036["rodando"],
        "ultimo":  STATUS_036["ultimo"],
        "proximo": STATUS_036["proximo"],
        "arquivo_existe": arq.exists(),
        "arquivo_modificado": datetime.fromtimestamp(arq.stat().st_mtime, TZ_BR).strftime("%d/%m/%Y %H:%M:%S")
                              if arq.exists() else None,
    })

@app.route("/036/api/logs")
def api_logs_036():
    ultimo_idx = int(request.args.get("desde", 0))
    todas = list(LOG_BUFFER_036)
    novas = todas[ultimo_idx:]
    return jsonify({"logs": novas, "total": len(todas)})

@app.route("/036/api/agendamentos", methods=["GET"])
def api_lista_agendamentos_036():
    return jsonify(carregar_config_036())

@app.route("/036/api/agendamentos", methods=["POST"])
def api_salvar_agendamentos_036():
    data = request.get_json()
    agendamentos = sorted(data.get("agendamentos", []), key=lambda x: x["hora"])
    salvar_config_036(agendamentos)
    reconstruir_scheduler_036(agendamentos)
    return jsonify({"ok": True, "quantidade": len(agendamentos)})

@app.route("/036/api/executar", methods=["POST"])
def api_executar_036():
    if STATUS_036["rodando"]:
        return jsonify({"ok": False, "msg": "Automação 036 já está rodando!"})
    t = threading.Thread(target=rodar_automacao_036_job, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "Automação 036 iniciada!"})

@app.route("/036/download/<filename>", methods=["GET"])
def download_036(filename):
    arquivo = BASE_DIR / filename
    if arquivo.exists():
        return send_file(
            arquivo,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True
        )
    return f"Arquivo {filename} ainda não foi gerado", 404


# ─────────────────────────────────────────────────────
#  FRONTEND
# ─────────────────────────────────────────────────────
@app.route("/081")
def index_081():
    with open(BASE_DIR / "index.html", encoding="utf-8") as f:
        return f.read()

@app.route("/036")
def index_036():
    with open(BASE_DIR / "index_036.html", encoding="utf-8") as f:
        return f.read()

@app.route("/")
def index():
    return '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Automação SSW — Painel</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root { --bg:#0d1117; --bg2:#161b22; --bg3:#1c2330; --border:#30363d; --blue:#2f81f7; --purple:#a371f7; --text:#e6edf3; --text2:#8b949e; --text3:#484f58; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family:"Inter",sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
    .nav-bar { background:linear-gradient(135deg,#0d1117,#161b22); border-bottom:1px solid var(--border); padding:0 32px; height:64px; display:flex; align-items:center; gap:24px; position:sticky; top:0; z-index:100; backdrop-filter:blur(10px); }
    .nav-logo { display:flex; align-items:center; gap:10px; font-size:1.1rem; font-weight:700; margin-right:32px; }
    .nav-logo-icon { width:36px; height:36px; background:linear-gradient(135deg,var(--blue),var(--purple)); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1.2rem; }
    .tab-buttons { display:flex; gap:4px; }
    .tab-btn { padding:8px 20px; border-radius:8px; border:1px solid transparent; background:transparent; color:var(--text2); font-family:"Inter",sans-serif; font-size:.875rem; font-weight:600; cursor:pointer; transition:all .2s; display:flex; align-items:center; gap:8px; }
    .tab-btn:hover { background:var(--bg3); color:var(--text); }
    .tab-btn.active-blue { background:rgba(47,129,247,.15); border-color:var(--blue); color:var(--blue); }
    .tab-btn.active-purple { background:rgba(163,113,247,.15); border-color:var(--purple); color:var(--purple); }
    .tab-dot { width:8px; height:8px; border-radius:50%; }
    .tab-dot.blue { background:var(--blue); }
    .tab-dot.purple { background:var(--purple); }
    iframe { width:100%; height:calc(100vh - 64px); border:none; }
  </style>
</head>
<body>
  <div class="nav-bar">
    <div class="nav-logo"><div class="nav-logo-icon">🚛</div> Automação SSW</div>
    <div class="tab-buttons">
      <button class="tab-btn active-blue" id="tab-081" onclick="trocarAba(\'/081\', this, \'blue\')"><div class="tab-dot blue"></div> 081 CTRCs</button>
      <button class="tab-btn" id="tab-036" onclick="trocarAba(\'/036\', this, \'purple\')"><div class="tab-dot purple"></div> 036 Relatório</button>
    </div>
  </div>
  <iframe id="frame" src="/081"></iframe>
  <script>
    function trocarAba(url, btn, cor) {
      document.getElementById("frame").src = url;
      document.querySelectorAll(".tab-btn").forEach(b => { b.className = "tab-btn"; });
      btn.classList.add("active-" + cor);
    }
  </script>
</body>
</html>
'''


# ─────────────────────────────────────────────────────
#  INICIALIZAÇÃO
# ─────────────────────────────────────────────────────
def main():
    # Carrega agendamentos da 081
    agendamentos = carregar_config()
    reconstruir_scheduler(agendamentos)

    # Carrega agendamentos da 036
    agendamentos_036 = carregar_config_036()
    reconstruir_scheduler_036(agendamentos_036)

    scheduler.start()

    adicionar_log(f"[SERVIDOR] Iniciado em {get_agora().strftime('%d/%m/%Y %H:%M:%S')}")
    adicionar_log(f"[SERVIDOR] Acesse: http://localhost:5000")
    if agendamentos:
        for ag in agendamentos:
            adicionar_log(f"[AGENDA] Agendado para {ag['hora']}")

    adicionar_log_036(f"[SERVIDOR] Iniciado em {get_agora().strftime('%d/%m/%Y %H:%M:%S')}")
    adicionar_log_036(f"[SERVIDOR] Acesse: http://localhost:5000/036")
    if agendamentos_036:
        for ag in agendamentos_036:
            adicionar_log_036(f"[AGENDA] 036 agendado para {ag['hora']}")

    print("\n" + "=" * 50)
    print("  AUTOMACAO SSW - Servidor Iniciado")
    print("  Acesse: http://localhost:5000")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
