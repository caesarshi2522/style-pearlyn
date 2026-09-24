"""Task-scoped, loopback-only visual style picker. Python 3.9+, no packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'references/catalog.json'

def html_target(path):
    p = Path(path).resolve()
    if p.suffix.lower() not in ('.html', '.htm') or not p.is_file():
        raise ValueError('An existing HTML file is required')
    content = p.read_bytes()
    if not content.strip():
        raise ValueError('HTML file is empty')
    return {'path': str(p), 'name': p.name, 'sha256': hashlib.sha256(content).hexdigest()}

def target_current(state):
    target = state.get('target')
    if not target:
        return False
    try:
        return html_target(target['path']) == target
    except (OSError, ValueError):
        return False

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def request_json(url, data=None, timeout=2):
    headers = {'Content-Type': 'application/json'}
    if data is not None:
        parsed = urlsplit(url)
        headers['Origin'] = f'{parsed.scheme}://{parsed.netloc}'
    req = Request(url, data=None if data is None else json.dumps(data).encode(), headers=headers)
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)

def result(state):
    selected = state.get('selection')
    item = next((s for s in read_json(CATALOG) if selected and s['id'] == selected['id']), None)
    return {'sessionId': state['sessionId'], 'task': state['task'], 'url': state.get('url'),
            'selection': selected, 'style': item, 'target': state.get('target'),
            'intent': state.get('intent', 'apply'), 'preset': state.get('preset'),
            'imagePath': str(ROOT / 'assets/references' / (item['id'] + '.jpg')) if item else None}

def preset_result(state):
    preset = state.get('preset')
    item = next((s for s in read_json(CATALOG) if preset and s['id'] == preset['id']), None)
    return {'sessionId': state['sessionId'], 'task': state['task'], 'preset': preset,
            'style': item, 'imagePath': str(ROOT / 'assets/references' / (item['id'] + '.jpg')) if item else None}

def serve(session_file):
    state = read_json(session_file)
    catalog = read_json(CATALOG)
    by_id = {s['id']: s for s in catalog}
    prefix = '/s/' + state['token'] + '/'
    lock = threading.Lock()
    changed = threading.Condition(lock)
    receiver = {'status': 'disconnected'}
    last_used = [time.monotonic()]

    def connection():
        if receiver.get('status') == 'waiting' and time.time() > receiver.get('expiresAt', 0):
            receiver['status'] = 'expired'
        return dict(receiver)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, data, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
            self.end_headers()
            self.wfile.write(data)

        def route(self):
            expected = '127.0.0.1:' + str(self.server.server_port)
            if self.headers.get('Host') != expected:
                self.reply(403, {'error': 'Invalid host'})
                return None
            path = urlsplit(self.path).path
            if not path.startswith(prefix):
                self.reply(404, {'error': 'Unknown session'})
                return None
            last_used[0] = time.monotonic()
            return path[len(prefix):]

        def do_GET(self):
            route = self.route()
            if route is None:
                return
            if route == 'selection':
                with lock:
                    self.reply(200, {'sessionId': state['sessionId'], 'task': state['task'], 'targetName': (state.get('target') or {}).get('name'), 'selection': state.get('selection'), 'receiver': connection(), 'intent': state.get('intent', 'apply'), 'preset': state.get('preset')})
            elif route in ('', 'index.html'):
                self.reply(200, (ROOT / 'assets/picker.html').read_bytes(), 'text/html; charset=utf-8')
            elif route == 'picker.js':
                self.reply(200, (ROOT / 'assets/picker.js').read_bytes(), 'text/javascript; charset=utf-8')
            elif route.startswith('references/') and route.endswith('.jpg'):
                code = route[len('references/'):-4]
                if code not in by_id:
                    self.reply(404, {'error': 'Unknown style'})
                else:
                    self.reply(200, (ROOT / 'assets/references' / (code + '.jpg')).read_bytes(), 'image/jpeg')
            else:
                self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            route = self.route()
            if route is None:
                return
            if self.headers.get('Origin') != f'http://127.0.0.1:{self.server.server_port}':
                self.reply(403, {'error': 'Invalid origin'})
                return
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                self.reply(415, {'error': 'JSON required'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length < 1 or length > 2048:
                    raise ValueError('Invalid body size')
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError('Object required')
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'Invalid request'})
                return
            if route == 'stop':
                self.reply(200, {'stopped': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if route == 'clear-preset':
                with changed:
                    state['preset'] = None
                    if state.get('intent') == 'preset':
                        state['selection'] = None
                        receiver['status'] = 'cancelled'
                    write_json(session_file, state)
                    changed.notify_all()
                    self.reply(200, {'preset': None, 'selection': state.get('selection'), 'receiver': connection()})
                return
            if route == 'arm':
                with changed:
                    intent = state.get('intent', 'apply')
                    panel_edit = body.get('presetEdit') is True
                    if panel_edit and intent != 'preset':
                        self.reply(409, {'error': 'Preset editing requires a preset panel'})
                        return
                    if panel_edit and connection()['status'] == 'waiting':
                        self.reply(200, connection())
                        return
                    if intent != 'preset' and (intent != 'apply' or not target_current(state)):
                        self.reply(409, {'error': 'source_unavailable'})
                        return
                    receiver.clear()
                    receiver.update(status='waiting', roundId=secrets.token_hex(12), expiresAt=time.time() + (600 if panel_edit else 120))
                    changed.notify_all()
                    self.reply(200, connection())
                return
            if route in ('wait', 'cancel'):
                with changed:
                    if body.get('roundId') != receiver.get('roundId') or not body.get('roundId'):
                        self.reply(409, {'error': 'Selection round changed'})
                        return
                    if route == 'cancel':
                        receiver['status'] = 'cancelled'
                        changed.notify_all()
                        self.reply(200, connection())
                        return
                    timeout = body.get('timeout', 45)
                    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 <= timeout <= 45:
                        self.reply(400, {'error': 'Timeout must be between 0 and 45 seconds'})
                        return
                    if connection()['status'] == 'waiting':
                        receiver['expiresAt'] = time.time() + timeout + 120
                        deadline = time.monotonic() + timeout
                        round_id = receiver['roundId']
                        while receiver.get('status') == 'waiting' and receiver.get('roundId') == round_id:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                break
                            changed.wait(remaining)
                    if body['roundId'] != receiver.get('roundId'):
                        self.reply(409, {'error': 'Selection round changed'})
                    elif receiver.get('status') == 'submitted':
                        receiver['status'] = 'received'
                        self.reply(200, dict(result(state), status='selected', roundId=receiver['roundId']))
                    else:
                        self.reply(200, {'status': connection()['status'], 'roundId': receiver['roundId']})
                return
            if route != 'selection':
                self.reply(404, {'error': 'Not found'})
                return
            code, mode = body.get('id'), body.get('mode', 'style')
            if not isinstance(code, str) or code not in by_id or mode not in ('style', 'layout'):
                self.reply(400, {'error': 'Unknown style or mode'})
                return
            action = body.get('action', 'save')
            if action not in ('save', 'continue'):
                self.reply(400, {'error': 'Unknown action'})
                return
            with changed:
                if action == 'continue':
                    if body.get('roundId') != receiver.get('roundId') or connection()['status'] != 'waiting':
                        self.reply(409, {'error': 'No active receiver. Reopen the panel from your task.'})
                        return
                    intent = state.get('intent', 'apply')
                    if intent != 'preset' and (intent != 'apply' or not target_current(state)):
                        receiver['status'] = 'source_changed'
                        changed.notify_all()
                        self.reply(409, {'error': 'source_changed'})
                        return
                elif connection()['status'] in ('submitted', 'received'):
                    self.reply(409, {'error': 'Selection already submitted. Start a new selection round.'})
                    return
                state['selection'] = {'id': code, 'name': by_id[code]['name'], 'mode': mode,
                                      'selectedAt': datetime.now(timezone.utc).isoformat()}
                if action == 'continue' and state.get('intent') == 'preset':
                    state['preset'] = dict(state['selection'], scope='task')
                write_json(session_file, state)
                if action == 'continue':
                    receiver['status'] = 'submitted'
                    changed.notify_all()
                self.reply(200, {'sessionId': state['sessionId'], 'selection': state['selection'], 'receiver': connection(), 'preset': state.get('preset')})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    state['url'] = f'http://127.0.0.1:{server.server_port}{prefix}'
    state['pid'] = os.getpid()
    write_json(session_file, state)
    def expire():
        while time.monotonic() - last_used[0] < 12 * 3600:
            time.sleep(60)
        server.shutdown()
    threading.Thread(target=expire, daemon=True).start()
    server.serve_forever(poll_interval=0.5)
    server.server_close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['start', 'serve', 'read', 'read-preset', 'clear-preset', 'stop', 'arm', 'wait', 'watch', 'cancel', 'choose'])
    parser.add_argument('--session-file', required=True)
    parser.add_argument('--task', default='当前网页任务')
    parser.add_argument('--round-id')
    parser.add_argument('--style-id')
    parser.add_argument('--html-file')
    parser.add_argument('--intent', choices=['apply', 'preset', 'browse'])
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args()
    session_file = Path(args.session_file).resolve()
    if args.command == 'serve':
        serve(session_file)
        return
    if args.command == 'read':
        print(json.dumps(result(read_json(session_file)), ensure_ascii=False))
        return
    if args.command == 'read-preset':
        print(json.dumps(preset_result(read_json(session_file)), ensure_ascii=False))
        return
    if args.command == 'choose':
        if not args.round_id or not args.style_id:
            parser.error('--round-id and --style-id are required')
        response = request_json(read_json(session_file)['url'] + 'selection',
                                {'id': args.style_id, 'action': 'continue', 'roundId': args.round_id})
        print(json.dumps(response, ensure_ascii=False))
        return
    if args.command == 'clear-preset':
        state = read_json(session_file)
        try:
            request_json(state['url'] + 'selection')
        except (OSError, KeyError):
            state['preset'] = None
            if state.get('intent') == 'preset':
                state['selection'] = None
            write_json(session_file, state)
        else:
            request_json(state['url'] + 'clear-preset', {})
        print(json.dumps({'preset': None}))
        return
    if args.command in ('arm', 'wait', 'watch', 'cancel'):
        if args.command != 'arm' and not args.round_id:
            parser.error('--round-id is required')
        maximum = 600 if args.command == 'watch' else 45
        if not 0 <= args.timeout <= maximum:
            parser.error(f'--timeout must be between 0 and {maximum}')
        if args.command == 'watch':
            url = read_json(session_file)['url']
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                seconds = min(45, deadline - time.monotonic())
                response = request_json(url + 'wait', {'roundId': args.round_id, 'timeout': seconds}, timeout=seconds + 5)
                if response['status'] != 'waiting':
                    print(json.dumps(response))
                    return
            request_json(url + 'cancel', {'roundId': args.round_id})
            print(json.dumps({'status': 'timed_out', 'roundId': args.round_id}))
            return
        payload = {} if args.command == 'arm' else {'roundId': args.round_id, 'timeout': args.timeout}
        response = request_json(read_json(session_file)['url'] + args.command, payload, timeout=args.timeout + 5)
        print(json.dumps(response, ensure_ascii=False))
        return
    if args.command == 'stop':
        print(json.dumps(request_json(read_json(session_file)['url'] + 'stop', {})))
        return
    session_file.parent.mkdir(parents=True, exist_ok=True)
    if args.intent in ('preset', 'browse') and args.html_file:
        parser.error('--html-file is only used for apply')
    target = html_target(args.html_file) if args.html_file else None
    state = read_json(session_file) if session_file.exists() else {'sessionId': secrets.token_hex(12), 'task': args.task, 'selection': None}
    intent = args.intent or ('apply' if target else state.get('intent', 'apply' if state.get('target') else 'browse'))
    if args.intent is None and target is None:
        target = state.get('target')
    if intent != 'apply':
        target = None
    previous_intent = state.get('intent', 'apply' if state.get('target') else 'browse')
    changed_input = state.get('target') != target or previous_intent != intent
    if session_file.exists():
        try:
            live = request_json(state['url'] + 'selection')
            if live['sessionId'] == state['sessionId']:
                if not changed_input:
                    print(json.dumps({'url': state['url'], 'sessionFile': str(session_file), 'reused': True}))
                    return
                request_json(state['url'] + 'stop', {})
        except Exception:
            pass
    if changed_input:
        state['selection'] = None
    state['target'] = target
    state['intent'] = intent
    state['task'] = args.task
    state['token'] = secrets.token_urlsafe(24)
    state.pop('url', None)
    write_json(session_file, state)
    command = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), 'serve', '--session-file', str(session_file)]
    kwargs = {'stdin': subprocess.DEVNULL, 'close_fds': True}
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    else:
        kwargs['start_new_session'] = True
    with session_file.with_suffix('.log').open('ab') as log:
        process = subprocess.Popen(command, stdout=log, stderr=log, **kwargs)
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError('Picker could not start; inspect the session .log file')
        try:
            state = read_json(session_file)
            if state.get('url') and request_json(state['url'] + 'selection')['sessionId'] == state['sessionId']:
                print(json.dumps({'url': state['url'], 'sessionFile': str(session_file), 'reused': False}, ensure_ascii=False))
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise TimeoutError('Picker startup timed out')

if __name__ == '__main__':
    main()
