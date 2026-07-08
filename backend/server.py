#!/usr/bin/env python3
"""
Sonic Player Backend — Zero dependencies (stdlib only)
Replaces FastAPI backend for Termux/Android compatibility.

All endpoints use Python's built-in http.server + json + subprocess + urllib.
No pip packages needed except yt-dlp (install via 'pkg install yt-dlp' on Termux).
"""

import http.server
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import threading
import glob
from pathlib import Path

PORT = 8005
CACHE_FILE = '/tmp/sonic_cache_v3.json'
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')

# ── In-memory cache ──
cache = {'search': {}, 'stream_url': {}, 'lyrics': {}}
cache_lock = threading.Lock()

def save_cache():
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except:
        pass

def load_cache():
    global cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                data = json.load(f)
                with cache_lock:
                    cache.update(data)
    except:
        pass

load_cache()
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


class SonicHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Sonic Player API."""

    def log_message(self, format, *args):
        """Quiet logging — only log errors."""
        if args and len(args) > 0 and '200' not in str(args[0]):
            print(f"[Sonic] {format % args}")

    def _send_json(self, data, status=200):
        """Send JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg, status=400):
        self._send_json({'error': msg}, status)

    def _send_file(self, filepath, media_type):
        """Send a file as binary response."""
        if not os.path.isfile(filepath):
            return self._send_error('file not found', 404)
        size = os.path.getsize(filepath)
        self.send_response(200)
        self.send_header('Content-Type', media_type)
        self.send_header('Content-Length', str(size))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def _proxy_stream(self, url):
        """Proxy a URL and stream its content."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_type = resp.headers.get('Content-Type', 'audio/mpeg')
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.end_headers()
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except Exception as e:
            if not self.wfile.closed:
                self._send_error(f'proxy failed: {str(e)}', 502)

    def _get_params(self):
        """Parse query string parameters."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        return {k: v[0] for k, v in params.items()}

    def _run_ytdlp(self, args, timeout=30):
        """Run yt-dlp with given args, return stdout."""
        try:
            result = subprocess.run(
                ['yt-dlp'] + args,
                capture_output=True, text=True, timeout=timeout,
                errors='replace'
            )
            return result.stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return '', 1
        except FileNotFoundError:
            return '', -1

    def _route(self):
        """Route request to appropriate handler."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/')
        method = self.command

        # CORS preflight
        if method == 'OPTIONS':
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            return

        if method != 'GET':
            return self._send_error('method not allowed', 405)

        params = self._get_params()

        # ── Health ──
        if path == '/health' or path == '':
            return self._send_json({
                'status': 'ok',
                'cached_streams': len(cache.get('stream_url', {}))
            })

        # ── Search YouTube ──
        if path == '/search':
            q = params.get('q', '')
            if not q:
                return self._send_error('query required')
            limit = min(int(params.get('limit', 20)), 200)
            offset = max(int(params.get('offset', 0)), 0)
            return self._handle_search(q, limit, offset)

        # ── Search Playlists ──
        if path == '/search_playlists':
            q = params.get('q', '')
            if not q:
                return self._send_json({'playlists': []})
            limit = min(int(params.get('limit', 10)), 20)
            return self._handle_search_playlists(q, limit)

        # ── Uploader Tracks ──
        if path == '/uploader_tracks':
            uploader = params.get('uploader', '')
            if not uploader:
                return self._send_json({'results': []})
            limit = min(int(params.get('limit', 20)), 50)
            return self._handle_uploader_tracks(uploader, limit)

        # ── Stream URL ──
        m = re.match(r'^/stream/([a-zA-Z0-9_-]+)$', path)
        if m:
            return self._handle_stream(m.group(1))

        # ── Video Stream URL ──
        m = re.match(r'^/video_stream/([a-zA-Z0-9_-]+)$', path)
        if m:
            return self._handle_video_stream(m.group(1))

        # ── Info ──
        m = re.match(r'^/info/([a-zA-Z0-9_-]+)$', path)
        if m:
            return self._handle_info(m.group(1))

        # ── Lyrics ──
        if path == '/lyrics':
            title = params.get('title', '')
            artist = params.get('artist', '')
            return self._handle_lyrics(title, artist)

        # ── Proxy ──
        if path == '/proxy':
            url = params.get('url', '')
            if not url:
                return self._send_error('url required')
            return self._proxy_stream(url)

        # ── Download ──
        m = re.match(r'^/download/([a-zA-Z0-9_-]+)$', path)
        if m:
            return self._handle_download(m.group(1))

        # ── Download Local ──
        m = re.match(r'^/download_local/([a-zA-Z0-9_-]+)$', path)
        if m:
            title = params.get('title', '')
            return self._handle_download_local(m.group(1), title)

        # ── Local Play ──
        m = re.match(r'^/local_play/(.+)', path)
        if m:
            filename = m.group(1)
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            # Prevent path traversal
            if '..' in filename or not os.path.realpath(filepath).startswith(os.path.realpath(DOWNLOADS_DIR)):
                return self._send_error('invalid path', 403)
            return self._send_file(filepath, 'audio/mp4')

        # ── Local List ──
        if path == '/local_list':
            return self._handle_local_list()

        # ── Check Local ──
        if path == '/check_local':
            video_id = params.get('video_id', '')
            return self._handle_check_local(video_id)

        # ── 404 ──
        self._send_error('not found', 404)

    # ── Handler Implementations ──

    def _handle_search(self, q, limit, offset):
        cache_key = f'search_{q}'
        with cache_lock:
            if cache_key in cache.get('search', {}):
                entry = cache['search'][cache_key]
                if time.time() - entry.get('time', 0) < 1800:
                    sliced = entry['results'][offset:offset + limit]
                    return self._send_json({'results': sliced, 'total': len(entry['results']), 'cached': True})

        stdout, rc = self._run_ytdlp([
            '--quiet', '--no-warnings',
            '--dump-json', '--flat-playlist', '--ignore-errors',
            f'ytsearch{limit}:{q}'
        ], timeout=30)

        if rc == -1:
            return self._send_json({'results': [], 'total': 0, 'error': 'yt-dlp not found. Install: pkg install yt-dlp'})

        tracks = self._parse_yt_search(stdout)
        with cache_lock:
            if 'search' not in cache:
                cache['search'] = {}
            cache['search'][cache_key] = {'results': tracks, 'time': time.time()}
        save_cache()
        sliced = tracks[offset:offset + limit]
        return self._send_json({'results': sliced, 'total': len(tracks)})

    def _parse_yt_search(self, stdout):
        """Parse yt-dlp flat JSON output into track list."""
        tracks = []
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except:
                continue
            vid = entry.get('id', '')
            if not vid:
                continue
            tracks.append({
                'id': f'yt_{vid}',
                'title': entry.get('title', 'Unknown'),
                'artist': entry.get('uploader', 'Unknown'),
                'album': entry.get('album', '') or 'YouTube',
                'duration': entry.get('duration', 0) or 0,
                'cover': f'https://img.youtube.com/vi/{vid}/hqdefault.jpg',
                'audio': f'/stream/{vid}',
                'source': 'YouTube',
                'videoId': vid,
            })
        return tracks

    def _handle_search_playlists(self, q, limit):
        cache_key = f'pl_{q}_{limit}'
        with cache_lock:
            if cache_key in cache and time.time() - cache.get(cache_key, {}).get('time', 0) < 1800:
                return self._send_json(cache[cache_key].get('data', {}))

        stdout, rc = self._run_ytdlp([
            '--quiet', '--no-warnings',
            '--dump-json', '--flat-playlist', '--ignore-errors',
            f'ytsearch{limit*3}:{q}'
        ], timeout=30)

        if rc != 0 or not stdout:
            return self._send_json({'playlists': []})

        uploader_map = {}
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except:
                continue
            vid = entry.get('id', '')
            if not vid:
                continue
            uploader = entry.get('uploader', 'Unknown')
            if uploader not in uploader_map:
                uploader_map[uploader] = {
                    'uploader': uploader,
                    'tracks': [],
                    'thumbnail': entry.get('thumbnail') or f'https://img.youtube.com/vi/{vid}/hqdefault.jpg',
                }
            uploader_map[uploader]['tracks'].append({
                'id': f'yt_{vid}',
                'title': entry.get('title', 'Unknown'),
                'duration': entry.get('duration', 0) or 0,
                'cover': f'https://img.youtube.com/vi/{vid}/hqdefault.jpg',
                'videoId': vid,
            })

        playlists = list(uploader_map.values())[:limit]
        data = {'playlists': playlists}
        with cache_lock:
            cache[cache_key] = {'data': data, 'time': time.time()}
        save_cache()
        return self._send_json(data)

    def _handle_uploader_tracks(self, uploader, limit):
        stdout, rc = self._run_ytdlp([
            '--quiet', '--no-warnings',
            '--dump-json', '--flat-playlist', '--ignore-errors',
            f'ytsearch{limit}:{uploader}'
        ], timeout=30)

        if rc != 0 or not stdout:
            return self._send_json({'results': []})

        tracks = []
        for line in stdout.split('\n'):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except:
                continue
            vid = entry.get('id', '')
            if not vid:
                continue
            tracks.append({
                'id': f'yt_{vid}',
                'title': entry.get('title', 'Unknown'),
                'artist': uploader,
                'album': 'YouTube',
                'duration': entry.get('duration', 0) or 0,
                'cover': f'https://img.youtube.com/vi/{vid}/hqdefault.jpg',
                'audio': f'/stream/{vid}',
                'source': 'YouTube',
                'videoId': vid,
            })

        return self._send_json({'results': tracks})

    def _handle_stream(self, video_id):
        with cache_lock:
            if video_id in cache.get('stream_url', {}):
                entry = cache['stream_url'][video_id]
                if time.time() - entry.get('time', 0) < 7200:
                    return self._send_json(entry['data'])

        audio_url, rc = self._run_ytdlp([
            '-g', '-f', 'bestaudio[ext=m4a]/bestaudio/best',
            '--no-warnings', '--quiet',
            f'https://www.youtube.com/watch?v={video_id}'
        ], timeout=30)

        if not audio_url:
            audio_url, rc = self._run_ytdlp([
                '-g', '--no-warnings', '--quiet',
                f'https://www.youtube.com/watch?v={video_id}'
            ], timeout=30)

        data = {
            'title': '',
            'uploader': '',
            'duration': 0,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
            'audio_url': audio_url or '',
        }
        with cache_lock:
            if 'stream_url' not in cache:
                cache['stream_url'] = {}
            cache['stream_url'][video_id] = {'data': data, 'time': time.time()}
        save_cache()
        return self._send_json(data)

    def _handle_video_stream(self, video_id):
        cache_key = f'video_{video_id}'
        with cache_lock:
            if cache_key in cache and time.time() - cache.get(cache_key, {}).get('time', 0) < 7200:
                return self._send_json(cache[cache_key])

        video_url, rc = self._run_ytdlp([
            '-g', '-f', 'best[height<=720]',
            '--no-warnings', '--quiet',
            f'https://www.youtube.com/watch?v={video_id}'
        ], timeout=30)

        if not video_url:
            video_url, rc = self._run_ytdlp([
                '-g', '--no-warnings', '--quiet',
                f'https://www.youtube.com/watch?v={video_id}'
            ], timeout=30)

        data = {'video_url': video_url or ''}
        with cache_lock:
            cache[cache_key] = data
        save_cache()
        return self._send_json(data)

    def _handle_info(self, video_id):
        stdout, rc = self._run_ytdlp([
            '--print', 'title', '--print', 'uploader', '--print', 'duration',
            '--no-warnings', '--quiet',
            f'https://www.youtube.com/watch?v={video_id}'
        ], timeout=15)

        if rc != 0 or not stdout:
            return self._send_json({'error': 'info failed'})

        lines = stdout.strip().split('\n')
        title = lines[0] if len(lines) > 0 else ''
        uploader = lines[1] if len(lines) > 1 else ''
        duration = lines[2] if len(lines) > 2 else '0'
        try:
            duration = int(float(duration))
        except:
            duration = 0

        return self._send_json({
            'title': title,
            'uploader': uploader,
            'duration': duration,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
        })

    def _handle_lyrics(self, title, artist):
        if not title and not artist:
            return self._send_json({'lrc': '', 'source': 'none'})

        cache_key = f'lyrics_{artist}_{title}'
        with cache_lock:
            if 'lyrics' in cache and cache_key in cache['lyrics']:
                return self._send_json(cache['lyrics'][cache_key])

        # Try LRCLib API directly (no syncedlyrics library needed)
        lrc = self._fetch_lrclib(title, artist)
        result = {'lrc': lrc or '', 'source': 'lrclib' if lrc else 'none'}
        with cache_lock:
            if 'lyrics' not in cache:
                cache['lyrics'] = {}
            cache['lyrics'][cache_key] = result
        save_cache()
        return self._send_json(result)

    def _fetch_lrclib(self, title, artist):
        """Fetch synced lyrics from LRCLib API."""
        try:
            query = urllib.parse.quote(f'{artist} {title}')
            url = f'https://lrclib.net/api/get?track_name={urllib.parse.quote(title)}&artist_name={urllib.parse.quote(artist)}'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'SonicPlayer/1.0 (https://github.com/CYBER-HACKER-Studio)',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('syncedLyrics', '') or data.get('plainLyrics', '')
        except:
            return ''

    def _handle_download(self, video_id):
        """Download audio as binary stream."""
        try:
            result = subprocess.run(
                ['yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio/best',
                 '-o', '-', '--no-warnings', '--quiet',
                 f'https://www.youtube.com/watch?v={video_id}'],
                capture_output=True, timeout=60
            )
            self.send_response(200)
            self.send_header('Content-Type', 'audio/mp4')
            self.send_header('Content-Disposition', f'attachment; filename="{video_id}.m4a"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(result.stdout)))
            self.end_headers()
            self.wfile.write(result.stdout)
        except Exception as e:
            self._send_error(f'download failed: {str(e)}', 500)

    def _handle_download_local(self, video_id, title):
        """Download audio to local storage."""
        safe_name = ''.join(c for c in (title or video_id) if c.isalnum() or c in ' ._-').strip() or video_id
        save_path = os.path.join(DOWNLOADS_DIR, f'{safe_name}_{video_id[:8]}.m4a')
        try:
            subprocess.run(
                ['yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio/best', '-o', save_path,
                 '--no-warnings', '--quiet',
                 f'https://www.youtube.com/watch?v={video_id}'],
                capture_output=True, timeout=120
            )
            if os.path.exists(save_path):
                size = os.path.getsize(save_path)
                return self._send_json({
                    'path': f'/local_play/{os.path.basename(save_path)}',
                    'size': size,
                    'success': True
                })
            return self._send_json({'error': 'download failed', 'success': False})
        except Exception as e:
            return self._send_json({'error': str(e), 'success': False})

    def _handle_local_list(self):
        """List locally saved files."""
        files = glob.glob(os.path.join(DOWNLOADS_DIR, '*'))
        result = []
        for f in files:
            if os.path.isfile(f):
                result.append({
                    'path': f'/local_play/{os.path.basename(f)}',
                    'name': os.path.basename(f),
                    'size': os.path.getsize(f)
                })
        return self._send_json({'files': result})

    def _handle_check_local(self, video_id):
        """Check if a video has been downloaded locally."""
        pattern = os.path.join(DOWNLOADS_DIR, f'*{video_id[:8]}*')
        files = glob.glob(pattern)
        for f in files:
            if os.path.isfile(f):
                return self._send_json({
                    'exists': True,
                    'path': f'/local_play/{os.path.basename(f)}',
                    'size': os.path.getsize(f)
                })
        return self._send_json({'exists': False})

    # ── HTTP method handlers ──

    def do_GET(self):
        self._route()

    def do_OPTIONS(self):
        self._route()


def run_server():
    server = http.server.HTTPServer(('0.0.0.0', PORT), SonicHandler)
    print(f'[Sonic] Backend running on http://localhost:{PORT}')
    print(f'[Sonic] Zero dependencies — stdlib only!')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[Sonic] Shutting down...')
        server.shutdown()


if __name__ == '__main__':
    run_server()
