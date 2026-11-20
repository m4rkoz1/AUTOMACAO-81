import json
import logging
from pathlib import Path
import httpx

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config_filebrowser.json"

def carregar_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "habilitado": True,
        "base_url": "https://1-filebrowser1.wvm3zj.easypanel.host",
        "pasta_remota": "home/opc/ti",
        "usuario": "",
        "senha": ""
    }

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def upload_para_filebrowser(arquivos=None, log_fn=print):
    """
    Realiza o upload das planilhas para o Filebrowser via API REST.
    Substitui os arquivos existentes automaticamente (override=true).
    """
    cfg = carregar_config()
    if not cfg.get("habilitado", True):
        log_fn("[FILEBROWSER] Sincronização desabilitada em config_filebrowser.json.")
        return False

    base_url = cfg.get("base_url", "").rstrip("/")
    usuario = cfg.get("usuario", "").strip()
    senha = cfg.get("senha", "").strip()
    pasta = cfg.get("pasta_remota", "").strip("/")

    if not base_url or not usuario or not senha:
        log_fn("[FILEBROWSER] ⚠ Usuário ou senha do Filebrowser não configurados.")
        return False

    if arquivos is None:
        arquivos = ["RJO.xlsx", "FSP.xlsx", "BAR.xlsx", "ARA.xlsx", "TRA.xlsx", "relatorio_036.xlsx"]

    log_fn(f"[FILEBROWSER] Iniciando sincronização de {len(arquivos)} arquivo(s) com a VPS...")

    try:
        with httpx.Client(timeout=45.0, verify=False) as client:
            # 1. Autenticação para obter o token JWT
            login_url = f"{base_url}/api/login"
            resp_login = client.post(login_url, json={"username": usuario, "password": senha})
            if resp_login.status_code != 200:
                log_fn(f"[FILEBROWSER] ✘ Falha na autenticação ({resp_login.status_code}): verifique usuário e senha.")
                return False

            token = resp_login.text.strip().strip('"')
            headers = {"X-Auth": token}

            sucesso_total = True
            for nome_arq in arquivos:
                caminho = BASE_DIR / nome_arq if isinstance(nome_arq, str) else nome_arq
                if not caminho.exists():
                    continue

                # Caminho destino no Filebrowser
                if pasta:
                    remote_path = f"{pasta}/{caminho.name}"
                else:
                    remote_path = caminho.name

                upload_url = f"{base_url}/api/resources/{remote_path}?override=true"

                with open(caminho, "rb") as f_data:
                    resp_upload = client.post(upload_url, headers=headers, content=f_data.read())

                if resp_upload.status_code in (200, 201):
                    log_fn(f"[FILEBROWSER] ✔ {caminho.name} sincronizado com sucesso na VPS!")
                else:
                    log_fn(f"[FILEBROWSER] ✘ Erro ao enviar {caminho.name} ({resp_upload.status_code}): {resp_upload.text}")
                    sucesso_total = False

            return sucesso_total
    except Exception as e:
        log_fn(f"[FILEBROWSER] ✘ Erro de conexão com a VPS: {e}")
        return False

if __name__ == "__main__":
    import sys
    print("Testando upload manual...")
    upload_para_filebrowser()

