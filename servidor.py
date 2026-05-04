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

# ─────────────────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config_agendamentos.json"

app       = Flask(__name__)
scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

# Buffer de logs (últimas 500 linhas)
LOG_BUFFER  = deque(maxlen=500)
STATUS      = {"rodando": False, "ultimo": None, "proximo": None}


def adicionar_log(linha: str):
    LOG_BUFFER.append(linha)


# Conecta o callback de log da automação
automacao_ssw.set_log_callback(adicionar_log)


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
    """Remove todos os jobs e recria com a lista atual."""
    for job in scheduler.get_jobs():
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
    jobs = scheduler.get_jobs()
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
            as_attachment=True,
            download_name=f"{filial}.xlsx"
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

# ─────────────────────────────────────────────────────
#  FRONTEND (HTML embutido)
# ─────────────────────────────────────────────────────
@app.route("/")
def index():
    with open(BASE_DIR / "index.html", encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────────────
#  INICIALIZAÇÃO
# ─────────────────────────────────────────────────────
def main():
    agendamentos = carregar_config()
    reconstruir_scheduler(agendamentos)
    scheduler.start()

    adicionar_log(f"[SERVIDOR] Iniciado em {get_agora().strftime('%d/%m/%Y %H:%M:%S')}")
    adicionar_log(f"[SERVIDOR] Acesse: http://localhost:5000")
    if agendamentos:
        for ag in agendamentos:
            adicionar_log(f"[AGENDA] Agendado para {ag['hora']}")

    print("\n" + "═" * 50)
    print("  🚛 AUTOMAÇÃO SSW — Servidor Iniciado")
    print("  🌐 Acesse: http://localhost:5000")
    print("═" * 50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
