# ═══════════════════════════════════════════════════════════════════
# ⚠️  DEPRECATED — هذا الملف قديم ولا يُنصح باستخدامه
#
#  استخدم server.py بدلاً من main.py:
#    • zero dependencies خارجية (لا يحتاج FastAPI, uvicorn, requests...)
#    • توافق أفضل مع Termux وبيئات ARM64
#    • نفس الوظائف بالضبط — بل وأسرع وأخف
#
#  $ cd backend && python3 server.py
# ═══════════════════════════════════════════════════════════════════
# Sonic Backend v3 - Fast with yt-dlp -g + caching
# ⚠️  DEPRECATED — Use server.py instead (lighter, zero deps, Termux-friendly)
# ═══════════════════════════════════════════════════════════════════

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import subprocess
import uvicorn
import json
import time
import os
import requests
import syncedlyrics
import os
import uuid

app = FastAPI(title="Sonic Backend v3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_FILE = '/tmp/sonic_cache_v3.json'
cache = {'search': {}, 'stream': {}, 'stream_url': {}}

def save_cache():
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except: pass

def load_cache():
    global cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cache = json.load(f)
    except: cache = {'search': {}, 'stream': {}, 'stream_url': {}}

load_cache()

@app.get("/search")
async def search(q: str = Query(..., min_length=1), limit: int = Query(20, le=200), offset: int = Query(0, ge=0)):
    """Search YouTube tracks with pagination support"""
    cache_key = f"search_{q}"
    if cache_key in cache['search']:
        entry = cache['search'][cache_key]
        if time.time() - entry['time'] < 1800:
            sliced = entry['results'][offset:offset + limit]
            return JSONResponse(content={"results": sliced, "total": len(entry['results']), "cached": True})

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({
            'quiet': True, 'no_warnings': True,
            'extract_flat': True, 'ignore_errors': True,
        }) as ydl:
            # Fetch based on user's requested limit
            result = ydl.extract_info(f"ytsearch{limit}:{q}", download=False)
            if not result or 'entries' not in result:
                return {"results": [], "total": 0}
            tracks = []
            for entry in result['entries']:
                if not entry or not entry.get('id'):
                    continue
                tracks.append({
                    "id": f"yt_{entry['id']}",
                    "title": entry.get('title', 'Unknown'),
                    "artist": entry.get('uploader', 'Unknown'),
                    "album": entry.get('album', '') or 'YouTube',
                    "duration": entry.get('duration', 0) or 0,
                    "cover": f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg",
                    "audio": f"http://localhost:8005/stream/{entry['id']}",
                    "source": "YouTube",
                    "videoId": entry['id'],
                })
            cache['search'][cache_key] = {'results': tracks, 'time': time.time()}
            save_cache()
            sliced = tracks[offset:offset + limit]
            return {"results": sliced, "total": len(tracks)}
    except Exception as e:
        return {"error": str(e), "results": [], "total": 0}

# ─── YouTube Playlist Search ───

@app.get("/search_playlists")
async def search_playlists(q: str = Query(..., min_length=1), limit: int = Query(10, le=20)):
    """Search YouTube and group results by uploader as playlists"""
    cache_key = f"pl_{q}_{limit}"
    if cache_key in cache and time.time() - cache[cache_key].get('time', 0) < 1800:
        return JSONResponse(content=cache[cache_key]['data'])

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({
            'quiet': True, 'no_warnings': True,
            'extract_flat': True, 'ignore_errors': True,
        }) as ydl:
            result = ydl.extract_info(f"ytsearch{limit*3}:{q}", download=False)
            if not result or 'entries' not in result:
                return {"playlists": []}

            # Group by uploader
            uploader_map = {}
            for entry in result['entries']:
                if not entry or not entry.get('id'):
                    continue
                uploader = entry.get('uploader', 'Unknown')
                if uploader not in uploader_map:
                    uploader_map[uploader] = {
                        "uploader": uploader,
                        "tracks": [],
                        "thumbnail": entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg",
                    }
                uploader_map[uploader]["tracks"].append({
                    "id": f"yt_{entry['id']}",
                    "title": entry.get('title', 'Unknown'),
                    "duration": entry.get('duration', 0) or 0,
                    "cover": f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg",
                    "videoId": entry['id'],
                })

            playlists = list(uploader_map.values())[:limit]
            data = {"playlists": playlists}
            cache[cache_key] = {'data': data, 'time': time.time()}
            save_cache()
            return JSONResponse(content=data)
    except Exception as e:
        return {"error": str(e), "playlists": []}

@app.get("/uploader_tracks")
async def uploader_tracks(uploader: str = Query(..., min_length=1), limit: int = Query(20, le=50)):
    """Get tracks by a specific uploader/channel"""
    cache_key = f"up_{uploader}_{limit}"
    if cache_key in cache and time.time() - cache[cache_key].get('time', 0) < 1800:
        return JSONResponse(content=cache[cache_key]['data'])

    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({
            'quiet': True, 'no_warnings': True,
            'extract_flat': True, 'ignore_errors': True,
        }) as ydl:
            result = ydl.extract_info(f"ytsearch{limit}:{uploader}", download=False)
            if not result or 'entries' not in result:
                return {"results": []}
            tracks = []
            for entry in result['entries']:
                if not entry or not entry.get('id'):
                    continue
                tracks.append({
                    "id": f"yt_{entry['id']}",
                    "title": entry.get('title', 'Unknown'),
                    "artist": uploader,
                    "album": 'YouTube',
                    "duration": entry.get('duration', 0) or 0,
                    "cover": f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg",
                    "audio": f"http://localhost:8005/stream/{entry['id']}",
                    "source": "YouTube",
                    "videoId": entry['id'],
                })
            data = {"results": tracks}
            cache[cache_key] = {'data': data, 'time': time.time()}
            save_cache()
            return JSONResponse(content=data)
    except Exception as e:
        return {"error": str(e), "results": []}

@app.get("/stream/{video_id}")
async def stream(video_id: str):
    """Get audio stream URL using yt-dlp -g (fast)"""
    if video_id in cache['stream_url']:
        entry = cache['stream_url'][video_id]
        if time.time() - entry['time'] < 7200:
            return JSONResponse(content=entry['data'])
    
    try:
        # yt-dlp -g extracts only the URL, much faster than full extraction
        result = subprocess.run(
            ['yt-dlp', '-g', '-f', 'bestaudio[ext=m4a]/bestaudio/best', 
             '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=30
        )
        
        audio_url = result.stdout.strip()
        
        # Fallback: try without format restriction
        if not audio_url or result.returncode != 0:
            result = subprocess.run(
                ['yt-dlp', '-g', '--no-warnings', '--quiet',
                 f'https://www.youtube.com/watch?v={video_id}'],
                capture_output=True, text=True, timeout=30
            )
            audio_url = result.stdout.strip()
        
        data = {
            "title": "",
            "uploader": "",
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "audio_url": audio_url or "",
        }
        
        cache['stream_url'][video_id] = {'data': data, 'time': time.time()}
        save_cache()
        return JSONResponse(content=data)
    except Exception as e:
        return {"error": str(e), "audio_url": ""}

@app.get("/proxy")
async def proxy(url: str = Query(...)):
    """Proxy audio streams"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
        }
        req = requests.get(url, headers=headers, stream=True, timeout=30)
        return StreamingResponse(
            req.iter_content(chunk_size=8192),
            media_type=req.headers.get('content-type', 'audio/mpeg'),
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except:
        return {"error": "proxy failed"}

@app.get("/download/{video_id}")
async def download(video_id: str):
    """Download audio as MP3 file"""
    try:
        result = subprocess.run(
            ['yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio/best', 
             '-o', '-', '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, timeout=60
        )
        return StreamingResponse(
            iter([result.stdout]),
            media_type='audio/mpeg',
            headers={
                "Content-Disposition": f'attachment; filename="{video_id}.m4a"',
                "Access-Control-Allow-Origin": "*",
            }
        )
    except:
        return {"error": "download failed"}

@app.get("/video_stream/{video_id}")
async def video_stream(video_id: str):
    """Get video stream URL (for music video mode)"""
    cache_key = f"video_{video_id}"
    if cache_key in cache:
        entry = cache[cache_key]
        if time.time() - entry['time'] < 7200:
            return JSONResponse(content=entry['data'])
    
    try:
        result = subprocess.run(
            ['yt-dlp', '-g', '-f', 'best[height<=720]', '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=30
        )
        video_url = result.stdout.strip()
        if not video_url:
            result = subprocess.run(
                ['yt-dlp', '-g', '--no-warnings', '--quiet',
                 f'https://www.youtube.com/watch?v={video_id}'],
                capture_output=True, text=True, timeout=30
            )
            video_url = result.stdout.strip()
        
        data = {"video_url": video_url or ""}
        cache[cache_key] = {'data': data, 'time': time.time()}
        save_cache()
        return JSONResponse(content=data)
    except:
        return {"video_url": ""}

@app.get("/download_video/{video_id}")
async def download_video(video_id: str):
    """Download video as MP4"""
    try:
        result = subprocess.run(
            ['yt-dlp', '-f', 'best[height<=720]', '-o', '-', '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, timeout=120
        )
        return StreamingResponse(
            iter([result.stdout]),
            media_type='video/mp4',
            headers={
                "Content-Disposition": f'attachment; filename="{video_id}.mp4"',
                "Access-Control-Allow-Origin": "*",
            }
        )
    except:
        return {"error": "download failed"}

@app.get("/download_local/{video_id}")
async def download_local(video_id: str, title: str = Query('')):
    """Download audio locally within the app"""
    safe_name = ''.join(c for c in (title or video_id) if c.isalnum() or c in ' ._-').strip() or video_id
    save_path = f"backend/downloads/{safe_name}_{video_id[:8]}.m4a"
    try:
        subprocess.run(
            ['yt-dlp', '-f', 'bestaudio[ext=m4a]/bestaudio/best', '-o', save_path,
             '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, timeout=120
        )
        if os.path.exists(save_path):
            size = os.path.getsize(save_path)
            return {"path": f"/local_play/{os.path.basename(save_path)}", "size": size, "success": True}
        return {"error": "download failed", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

@app.get("/local_play/{filename:path}")
async def local_play(filename: str):
    """Serve locally downloaded files"""
    filepath = f"backend/downloads/{filename}"
    if not os.path.exists(filepath):
        return {"error": "file not found"}
    from fastapi.responses import FileResponse
    return FileResponse(filepath, media_type='audio/mp4')

@app.get("/local_list")
async def local_list():
    """List locally saved downloads"""
    import glob
    files = glob.glob("backend/downloads/*")
    result = []
    for f in files:
        if os.path.isfile(f):
            result.append({
                "path": f"/local_play/{os.path.basename(f)}",
                "name": os.path.basename(f),
                "size": os.path.getsize(f)
            })
    return {"files": result}

@app.get("/info/{video_id}")
async def info(video_id: str):
    """Fast info extraction"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--print', 'title', '--print', 'uploader', '--print', 'duration',
             '--no-warnings', '--quiet',
             f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.strip().split('\n')
        title = lines[0] if len(lines) > 0 else ''
        uploader = lines[1] if len(lines) > 1 else ''
        duration = lines[2] if len(lines) > 2 else '0'
        return {
            "title": title,
            "uploader": uploader,
            "duration": int(float(duration)) if duration else 0,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }
    except:
        return {"error": "info failed"}

@app.get("/lyrics")
async def lyrics(title: str = Query(...), artist: str = Query('')):
    """Get synced LRC lyrics"""
    cache_key = f"lyrics_{artist}_{title}"
    if 'lyrics' in cache and cache_key in cache['lyrics']:
        return JSONResponse(content=cache['lyrics'][cache_key])
    
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        lrc = await asyncio.wait_for(
            loop.run_in_executor(None, syncedlyrics.search, f"{artist} {title}", True),
            timeout=15
        )
        result = {"lrc": lrc or "", "source": "synced" if lrc else "none"}
        if 'lyrics' not in cache: cache['lyrics'] = {}
        cache['lyrics'][cache_key] = result
        save_cache()
        return JSONResponse(content=result)
    except asyncio.TimeoutError:
        return JSONResponse(content={"lrc": "", "source": "timeout"})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "lrc": ""})

@app.get("/check_local")
async def check_local(video_id: str = Query(...)):
    """Check if a video's audio has been downloaded locally"""
    import glob
    pattern = f"backend/downloads/*{video_id[:8]}*"
    files = glob.glob(pattern)
    for f in files:
        if os.path.isfile(f):
            return {"exists": True, "path": f"/local_play/{os.path.basename(f)}", "size": os.path.getsize(f)}
    return {"exists": False}

@app.get("/health")
async def health():
    return {"status": "ok", "cached_streams": len(cache['stream_url'])}

if __name__ == "__main__":
    import sys
    print("⚠️ DEPRECATED: استخدم server.py بدلاً من main.py (zero dependencies, أفضل توافق مع Termux)", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=8005)
