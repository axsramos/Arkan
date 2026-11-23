import argparse
import socket
import threading
import time
import webbrowser
import uvicorn

from backend.main import app

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def open_browser_when_available(port: int) -> None:
    """Abre a interface apenas após o serviço aceitar conexões no loopback."""
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                webbrowser.open(f"http://127.0.0.1:{port}")
                return
        except OSError:
            time.sleep(0.1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Arkan - Aplicativo local")
    parser.add_argument(
        '-port', 
        type=int, 
        default=0, 
        help="Porta opcional para execução do servidor. Se omitida, escolhe uma porta local disponível."
    )
    args = parser.parse_args()

    port = args.port if args.port > 0 else find_free_port()

    threading.Thread(target=open_browser_when_available, args=(port,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
