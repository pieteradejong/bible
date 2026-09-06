#!/usr/bin/env python3
"""Render every page in headless Chromium and assert it produced real output.

This is the cheapest check that the views still execute: module graph resolves,
data loads, the expected number of elements appear, and nothing throws. It is
not a substitute for looking at a screenshot -- the rendering bugs in this
project's history (a saturated canvas, colliding labels, a squashed graph) were
all visually obvious and none would have failed an assertion.

Skips cleanly when no Chromium-family browser is installed, so `make test-all`
works on a machine without one. Run directly: python3 tests/smoke.py
"""
import http.server
import pathlib
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

BROWSERS = [
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

# page -> (regex that must appear in the rendered DOM, minimum match count)
EXPECTED = {
    "index.html":       (r'class="card"', 6),
    "timeline.html":    (r'class="item"', 100),
    "atlas.html":       (r"leaflet-interactive", 200),
    "footprint.html":   (r"<circle", 100),
    "network.html":     (r'data-book="\d+"', 66),
    "quotations.html":  (r"QUOTATION|Quotation", 5),
    "genealogy.html":   (r'class="p"', 50),
    "reader.html":      (r'class="v" id="v\d+"', 20),
}


def find_browser():
    for path in BROWSERS:
        if pathlib.Path(path).exists():
            return path
    return shutil.which("chromium") or shutil.which("google-chrome")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass                              # the browser's 404 for favicon is noise


def serve(directory):
    handler = lambda *a, **k: QuietHandler(*a, directory=str(directory), **k)

    class Quiet(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    httpd = Quiet(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def render(browser, url, budget_ms=9000, deadline=22):
    """Dump a page's post-JavaScript DOM.

    Headless Chromium writes the DOM and then, on some builds, never exits, and
    it buffers that output until it does -- so the file stays empty until the
    process is killed, and there is no early exit to be had. stdout goes to a
    real file rather than a pipe because Python discards a pipe's contents when
    communicate() times out, which silently turned every assertion into 0.
    """
    with tempfile.TemporaryDirectory() as profile:
        out = pathlib.Path(profile) / "dom.html"
        with out.open("w") as fh:
            proc = subprocess.Popen(
                [browser, "--headless=new", "--disable-gpu", "--no-first-run",
                 "--no-default-browser-check", f"--user-data-dir={profile}",
                 f"--virtual-time-budget={budget_ms}", "--window-size=1600,1000",
                 "--dump-dom", url],
                stdout=fh, stderr=subprocess.DEVNULL)
            waited, step = 0.0, 0.5
            while waited < deadline and proc.poll() is None:
                time.sleep(step)
                waited += step
            proc.kill()
            proc.wait(timeout=10)
        return out.read_text(errors="replace")


def main():
    browser = find_browser()
    if not browser:
        print("smoke: no Chromium-family browser found; skipping")
        return 0
    if not (WEB / "data" / "timeline.json").exists():
        print("smoke: web/data not built; run `make data` first")
        return 0

    httpd, port = serve(WEB)
    failures = []
    try:
        for page, (pattern, minimum) in EXPECTED.items():
            dom = render(browser, f"http://127.0.0.1:{port}/{page}")
            hits = len(re.findall(pattern, dom))
            ok = hits >= minimum
            print(f"  {'ok  ' if ok else 'FAIL'} {page:18s} "
                  f"{hits:>6} matches of /{pattern}/ (need {minimum})", flush=True)
            if not ok:
                failures.append(f"{page}: {hits} < {minimum}")
    finally:
        httpd.shutdown()

    if failures:
        print("\nsmoke failures:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("smoke: all pages rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
