#!/usr/bin/env python3
"""edit_serve.py — serve an HTML file with in-browser editable text + autosave to disk.

Usage:
    python3 edit_serve.py path/to/issue.html [--port 8765]

Open the printed URL in a browser: every text block becomes editable in place.
Edits are written back to the SAME file automatically (debounced ~0.8s after you
stop typing), on Ctrl/Cmd+S immediately, and on tab close (sendBeacon).
The saved file stays clean: the injected editor script, the save badge, and all
contenteditable/spellcheck attributes are stripped before writing, so the file
can go straight into the render pipeline afterwards.

Security: serves only files under the target file's directory; saves only to
that one file.
"""

import argparse
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TARGET: str = ''  # absolute path of the HTML file being edited
ROOT: str = ''    # its parent directory

INJECT_JS = """(function () {
  var SEL = 'h1,h2,h3,h4,h5,h6,p,li,td,th,figcaption,.map-head,.cat-head,' +
            '.map-item,.link-item,.title,.meta,.title-en,.num,.fig-title';
  document.querySelectorAll(SEL).forEach(function (el) {
    el.setAttribute('contenteditable', 'true');
    el.setAttribute('spellcheck', 'false');
  });
  var badge = document.createElement('div');
  badge.id = '__edit_serve_badge';
  badge.textContent = 'editing — autosaves to file';
  badge.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:2147483647;' +
    'background:#222;color:#fff;font:12px/1.6 sans-serif;padding:4px 10px;' +
    'border-radius:6px;opacity:.85;pointer-events:none;';
  document.body.appendChild(badge);
  function flash(msg, color) {
    badge.textContent = msg;
    badge.style.background = color || '#222';
  }
  function serialize() {
    var clone = document.documentElement.cloneNode(true);
    clone.querySelectorAll('[contenteditable]').forEach(function (el) {
      el.removeAttribute('contenteditable');
      el.removeAttribute('spellcheck');
    });
    var js = clone.querySelector('#__edit_serve_js'); if (js) js.remove();
    var bd = clone.querySelector('#__edit_serve_badge'); if (bd) bd.remove();
    return '<!DOCTYPE html>\\n' + clone.outerHTML;
  }
  var timer = null;
  function save() {
    fetch('/__save', { method: 'POST', body: serialize() }).then(function (r) {
      if (r.ok) {
        flash('saved ' + new Date().toLocaleTimeString(), '#1a7f37');
      } else {
        flash('SAVE FAILED (' + r.status + ')', '#b42318');
      }
    }).catch(function () { flash('SAVE FAILED (network)', '#b42318'); });
  }
  document.addEventListener('input', function (e) {
    if (e.target && e.target.getAttribute && e.target.getAttribute('contenteditable')) {
      flash('editing… unsaved', '#8a6d1a');
      clearTimeout(timer);
      timer = setTimeout(save, 800);
    }
  });
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      clearTimeout(timer);
      save();
    }
  });
  window.addEventListener('pagehide', function () {
    if (timer) { clearTimeout(timer); navigator.sendBeacon('/__save', serialize()); }
  });
})();"""


def build_page(html: str) -> str:
    """Return html with the editor script injected (response-time only)."""
    tag = '<script id="__edit_serve_js">' + INJECT_JS + '</script>'
    if re.search(r'</body>', html, re.IGNORECASE):
        return re.sub(r'</body>', lambda m: tag + '</body>', html, count=1, flags=re.IGNORECASE)
    return html + tag


def clean_payload(data: str) -> str:
    """Defensive: strip any injected-editor leftovers before writing to disk."""
    data = re.sub(r'<script id="__edit_serve_js">.*?</script>', '', data, flags=re.DOTALL)
    data = re.sub(r'<div id="__edit_serve_badge"[^>]*>.*?</div>', '', data, flags=re.DOTALL)
    data = re.sub(r'\s*contenteditable="[^"]*"', '', data)
    data = re.sub(r'\s*spellcheck="(?:true|false)"', '', data)
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/index.html'):
            with open(TARGET, 'rb') as f:
                page = f.read().decode('utf-8', errors='replace')
            self._send(200, build_page(page).encode('utf-8'), 'text/html; charset=utf-8')
            return
        # static assets under ROOT only
        rel = os.path.normpath(path.lstrip('/'))
        full = os.path.join(ROOT, rel)
        if not full.startswith(ROOT) or not os.path.isfile(full):
            self._send(404, b'not found', 'text/plain')
            return
        ctype = 'application/octet-stream'
        if full.endswith(('.html', '.htm')):
            ctype = 'text/html; charset=utf-8'
        elif full.endswith('.css'):
            ctype = 'text/css'
        elif full.endswith('.js'):
            ctype = 'text/javascript'
        elif full.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
            ctype = 'image/' + full.rsplit('.', 1)[-1].replace('jpg', 'jpeg')
        with open(full, 'rb') as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        if self.path.split('?', 1)[0] != '/__save':
            self._send(404, b'not found', 'text/plain')
            return
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode('utf-8', errors='replace')
        data = clean_payload(body)
        if not data.strip():
            self._send(400, b'empty payload', 'text/plain')
            return
        tmp = TARGET + '.edit-tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(data)
        os.replace(tmp, TARGET)
        self._send(200, b'ok', 'text/plain')


def main():
    global TARGET, ROOT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('html_file', help='HTML file to serve and edit')
    ap.add_argument('--port', type=int, default=8765)
    args = ap.parse_args()
    TARGET = os.path.abspath(args.html_file)
    if not os.path.isfile(TARGET):
        sys.exit(f'no such file: {TARGET}')
    ROOT = os.path.dirname(TARGET)
    srv = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'EDITING {TARGET}')
    print(f'OPEN    http://127.0.0.1:{args.port}/')
    print('Edit text in the browser; the file on disk updates as you type. Ctrl+S to force save.')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
