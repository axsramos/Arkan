from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
# from backend.database.database import init_db
import os
import argparse
import socket
import threading
import webbrowser
import uvicorn


STORAGE_DIR = "data"
DB_PATH = os.path.join(STORAGE_DIR, "arkan_vault.db")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(STORAGE_DIR, "files"), exist_ok=True)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Executado no boot da aplicação (Etapa 1: Garantir persistência e SQLite)
#     print("[Arkan] Inicializando camada de persistência...")
#     init_db()
#     yield
#     # Lote de encerramento, se necessário
            
app = FastAPI(title="Arkan Node", version="1.0.0")

# Monta a pasta frontend estaticamente para evitar problemas de CORS
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/favicon.ico")
def favicon():
    return RedirectResponse(url="/static/favicon.ico")

@app.get("/api/v1/node/check-setup")
def check_node_setup():
    vault_exists = os.path.exists(DB_PATH)
    return {"is_configured": vault_exists}

@app.get("/api/v1/health")
def health_check():
    return {"status": "ONLINE", "tor": "CONNECTED"}
            
def find_free_port():
    """Busca dinamicamente uma porta livre disponível no loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def open_browser(port):
    """Abre o navegador padrão no endereço local da aplicação."""
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Arkan - Nó Local P2P")
    parser.add_argument(
        '-port', 
        type=int, 
        default=0, 
        help="Porta opcional para execução do servidor (ex: -port 8123). Se omitida, escolhe aleatoriamente."
    )
    args = parser.parse_args()

    # Define a porta: se informada usa o valor, senão busca uma livre
    port = args.port if args.port > 0 else find_free_port()

    # Agenda a abertura do browser após 1 segundo para garantir que o servidor subiu
    threading.Timer(3.0, open_browser, args=[port]).start()
    
    # Executa o servidor FastAPI restrito exclusivamente ao loopback (127.0.0.1) conforme arquitetura
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True, log_level="info")
