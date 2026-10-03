"""Ver en el navegador ficheros que están en MareNostrum sin copiarlos aquí.

Cada petición lee el fichero por SSH y lo pasa al navegador. No se guarda nada
en esta máquina. Escucha solo en 127.0.0.1.

    python3 mn5/view_proxy.py --remote maps/outputs/eda --port 8630
"""

from __future__ import annotations

import argparse
import mimetypes
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SAFE = re.compile(r"^[\w./-]+$")


def make_handler(host: str, remote: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (nombre impuesto por http.server)
            path = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            if not SAFE.match(path) or ".." in path:
                self.send_error(400)
                return
            result = subprocess.run(["ssh", "-o", "BatchMode=yes", host, "cat", f"{remote}/{path}"],
                                    capture_output=True, check=False)
            if result.returncode != 0:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(result.stdout)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(result.stdout)

        def log_message(self, *args) -> None:  # sin registro: las rutas llevan identificadores de sujeto
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="mn5")
    parser.add_argument("--remote", default="maps/outputs/eda")
    parser.add_argument("--port", type=int, default=8630)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.host, args.remote)).serve_forever()


if __name__ == "__main__":
    main()
