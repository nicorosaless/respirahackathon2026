"""Servidor del portal del equipo: páginas locales más los ejemplos leídos de MareNostrum.

Sirve `outputs/portal` y, bajo `/mn/`, ficheros que viven en MareNostrum. Cada
petición a `/mn/` lee el fichero por SSH y lo pasa al navegador, sin guardarlo
aquí. Escucha solo en 127.0.0.1: se publica en el tailnet con `tailscale serve`.

    python3 mn5/portal_server.py --port 8631

Sirve igual la web de la demo con la cohorte real: las páginas salen de `web/out`
y todo lo que cuelga de `/data/` se lee de MareNostrum.

    python3 mn5/portal_server.py --static web/out --remote maps/outputs/web-data --prefix data/ --port 8641
"""

from __future__ import annotations

import argparse
import mimetypes
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SAFE = re.compile(r"^[\w./-]+$")


def make_handler(static: Path, host: str, remote: str, prefix: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:  # noqa: N802 (el navegador pregunta así antes de precargar una página)
            self.do_GET(body=False)

        def do_GET(self, body: bool = True) -> None:  # noqa: N802 (nombre impuesto por http.server)
            path = self.path.split("?", 1)[0].split("#", 1)[0].lstrip("/") or "index.html"
            if not SAFE.match(path) or ".." in path:
                self.send_error(400)
                return
            send = body
            if path.startswith(prefix):
                result = subprocess.run(["ssh", "-o", "BatchMode=yes", host, "cat", f"{remote}/{path[len(prefix):]}"],
                                        capture_output=True, check=False)
                body = result.stdout if result.returncode == 0 else None
            else:
                target = static / path
                if target.is_dir():  # una ruta de página, como /plataforma/
                    target, path = target / "index.html", f"{path.rstrip('/')}/index.html"
                body = target.read_bytes() if target.is_file() else None
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if send:
                self.wfile.write(body)

        def log_message(self, *args) -> None:  # sin registro: las rutas llevan identificadores de sujeto
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--static", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "portal")
    parser.add_argument("--host", default="mn5")
    parser.add_argument("--remote", default="maps/outputs/eda")
    parser.add_argument("--prefix", default="mn/", help="las rutas que empiezan así se leen de MareNostrum")
    parser.add_argument("--port", type=int, default=8631)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(args.static, args.host, args.remote, args.prefix)).serve_forever()


if __name__ == "__main__":
    main()
