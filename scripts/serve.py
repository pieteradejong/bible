#!/usr/bin/env python3
"""Static server for web/ that honours the pre-compressed .json.gz files.

python -m http.server would send the raw JSON and ignore the .gz siblings, so
this adds the one behaviour a real static host would give us: if the client
accepts gzip and a current .gz exists, send that with Content-Encoding: gzip.
"""
import functools, http.server, os, pathlib, socketserver, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "web"


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = pathlib.Path(self.translate_path(self.path))
        gz = path.with_suffix(path.suffix + ".gz")
        accepts = "gzip" in self.headers.get("Accept-Encoding", "")
        if (path.suffix == ".json" and accepts and gz.is_file()
                and gz.stat().st_mtime >= path.stat().st_mtime):
            try:
                f = gz.open("rb")
            except OSError:
                return super().send_head()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(gz.stat().st_size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return f
        return super().send_head()

    def log_message(self, fmt, *args):
        if "404" in fmt % args:
            super().log_message(fmt, *args)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    os.chdir(ROOT)
    socketserver.TCPServer.allow_request_reuse = True

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
