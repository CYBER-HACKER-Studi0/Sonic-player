#!/usr/bin/env python3
"""
Sonic Vision — Video Analyzer
تحليل فيديوهات كامل: فريمات، نصوص، ألوان، مشاهد، وجوه
"""

import sys
import os
import subprocess
import json
import tempfile
import shutil
from pathlib import Path

# ── Helper: run ffmpeg/ffprobe ──
def run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

# ── 1. Extract metadata ──
def extract_metadata(video_path):
    result = run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path])
    data = json.loads(result.stdout)
    fmt = data.get('format', {})
    meta = {
        'file': os.path.basename(video_path),
        'size_mb': round(int(fmt.get('size', 0)) / 1048576, 1),
        'duration_s': round(float(fmt.get('duration', 0)), 1),
        'duration_str': fmt.get('duration', '0'),
    }
    for s in data.get('streams', []):
        if s['codec_type'] == 'video':
            meta['resolution'] = f"{s.get('width','?')}x{s.get('height','?')}"
            meta['codec'] = s.get('codec_name', '?')
            meta['fps'] = s.get('r_frame_rate', '?')
            meta['bitrate_kbps'] = round(int(s.get('bit_rate', 0)) / 1000) if s.get('bit_rate') else 0
        elif s['codec_type'] == 'audio':
            meta['audio_codec'] = s.get('codec_name', '?')
            meta['sample_rate'] = s.get('sample_rate', '?')
    return meta

# ── 2. Extract frames at intervals ──
def extract_frames(video_path, output_dir, interval=5, max_frames=20):
    """Extract frames every `interval` seconds"""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/{interval}',
        '-frames:v', str(max_frames),
        '-q:v', '2',
        f'{output_dir}/frame_%03d.jpg', '-y'
    ]
    result = run(cmd, timeout=120)
    frames = sorted(Path(output_dir).glob('frame_*.jpg'))
    return [str(f) for f in frames]

# ── 3. Extract keyframes (scene changes) ──
def extract_keyframes(video_path, output_dir, threshold=0.3):
    """Extract frames at scene changes"""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"select='gt(scene,{threshold})',scale=640:-1",
        '-vsync', 'vfr',
        '-q:v', '2',
        f'{output_dir}/key_%03d.jpg', '-y'
    ]
    result = run(cmd, timeout=120)
    frames = sorted(Path(output_dir).glob('key_*.jpg'))
    return [str(f) for f in frames]

# ── 4. Analyze a single frame ──
def analyze_frame(frame_path):
    from PIL import Image
    import numpy as np
    
    img = Image.open(frame_path)
    arr = np.array(img)
    h, w = arr.shape[:2]
    
    analysis = {
        'size': f'{w}x{h}',
        'colors': {},
        'text': '',
        'skin_pct': 0.0,
        'has_person': False,
        'green_pct': 0.0,
        'red_pct': 0.0,
        'gold_pct': 0.0,
        'brightness': 0.0,
        'ui_elements': [],
    }
    
    # Color bands
    analysis['colors']['top'] = f"RGB({arr[:int(h*0.1),:,:3].mean(axis=(0,1)).astype(int).tolist()})"
    analysis['colors']['mid'] = f"RGB({arr[h//4:3*h//4,:,:3].mean(axis=(0,1)).astype(int).tolist()})"
    analysis['colors']['bot'] = f"RGB({arr[3*h//4:,:,:3].mean(axis=(0,1)).astype(int).tolist()})"
    
    total_pixels = w * h
    total = total_pixels
    
    # Skin detection
    skin = (arr[...,0] > 100) & (arr[...,0] < 250) & \
           (arr[...,1] > 60) & (arr[...,1] < 220) & \
           (arr[...,2] > 40) & (arr[...,2] < 200) & \
           (arr[...,0] > arr[...,1]) & (arr[...,1] > arr[...,2])
    analysis['skin_pct'] = round(100 * skin.sum() / total, 1)
    analysis['has_person'] = analysis['skin_pct'] > 8
    
    # Color detection
    green = (arr[...,1] > 150) & (arr[...,0] < 100) & (arr[...,2] < 100)
    red = (arr[...,0] > 180) & (arr[...,1] < 80) & (arr[...,2] < 80)
    gold = (arr[...,0] > 200) & (arr[...,1] > 150) & (arr[...,2] < 100)
    white = arr.max(axis=2) > 200
    dark = arr.max(axis=2) < 40
    
    analysis['green_pct'] = round(100 * green.sum() / total, 2)
    analysis['red_pct'] = round(100 * red.sum() / total, 2)
    analysis['gold_pct'] = round(100 * gold.sum() / total, 2)
    analysis['brightness'] = round(100 * white.sum() / total, 1)
    
    # UI detection
    if analysis['green_pct'] > 0.5:
        analysis['ui_elements'].append('whatsapp_green')
    if red.sum() > 100:
        analysis['ui_elements'].append('red_button')
    if analysis['gold_pct'] > 0.5:
        analysis['ui_elements'].append('gold_accent')
    
    # Check for horizontal UI bars
    # Top bar
    top_bar = arr[:int(h*0.06), :, :3].mean()
    analysis['top_bar_dark'] = top_bar < 60
    
    # Bottom nav bar
    bot_bar = arr[-int(h*0.08):, :, :3].mean()
    analysis['bot_bar_dark'] = bot_bar < 60
    
    # OCR - extract text
    try:
        result = subprocess.run(
            ['tesseract', frame_path, 'stdout', '-l', 'ara+eng', '--psm', '6'],
            capture_output=True, text=True, timeout=10
        )
        text = result.stdout.strip()
        # Clean up OCR noise
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 2]
        analysis['text'] = '\n'.join(lines[:15])  # Max 15 lines
        analysis['text_lines'] = len(lines)
    except:
        analysis['text'] = '[OCR failed]'
        analysis['text_lines'] = 0
    
    return analysis

# ── 5. Scene detection ──
def detect_scenes(video_path, threshold=0.15):
    """Detect scene changes using ffmpeg"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"select='gt(scene,{threshold})',showinfo",
        '-vsync', 'vfr', '-f', 'null', '-'
    ]
    result = run(cmd, timeout=60)
    # Parse scene change timestamps from stderr
    scenes = []
    for line in result.stderr.split('\n'):
        if 'pts_time:' in line:
            try:
                ts = float(line.split('pts_time:')[1].split()[0])
                scenes.append(ts)
            except:
                pass
    return scenes

# ── 6. Main analyzer ──
def analyze_video(video_path):
    print(f"\n{'═'*60}")
    print(f"  🎬 SONIC VISION — Video Analyzer")
    print(f"{'═'*60}")
    
    # Metadata
    print(f"\n📋 METADATA")
    print(f"{'─'*40}")
    meta = extract_metadata(video_path)
    for k, v in meta.items():
        print(f"  {k}: {v}")
    
    # Scene changes
    print(f"\n🎬 SCENE CHANGES")
    print(f"{'─'*40}")
    scenes = detect_scenes(video_path, threshold=0.2)
    if scenes:
        for s in scenes:
            m, sec = divmod(s, 60)
            print(f"  ⏱  {int(m):02d}:{sec:05.2f}")
    else:
        print("  No major scene changes (single scene)")
    
    # Frame extraction
    tmpdir = tempfile.mkdtemp(prefix='sonic_vision_')
    
    # Every 3 seconds
    print(f"\n📸 FRAME ANALYSIS (every 3s)")
    print(f"{'─'*40}")
    frames = extract_frames(video_path, f"{tmpdir}/frames", interval=3, max_frames=30)
    
    frame_results = []
    for i, fp in enumerate(frames):
        ts = i * 3
        m, sec = divmod(ts, 60)
        analysis = analyze_frame(fp)
        frame_results.append({'time': ts, 'analysis': analysis})
        
        # Compact output
        icons = []
        if analysis['has_person']: icons.append('👤')
        if analysis['green_pct'] > 0.5: icons.append('💚')
        if analysis['red_pct'] > 0.1: icons.append('🔴')
        if analysis['gold_pct'] > 0.5: icons.append('✨')
        
        text_preview = analysis['text'][:60].replace('\n', ' | ') if analysis['text'] else ''
        print(f"  [{int(m):02d}:{sec:02d}] {' '.join(icons)} skin={analysis['skin_pct']}% "
              f"bright={analysis['brightness']}% "
              f"{'📱' if analysis['top_bar_dark'] else ''}"
              f"{text_preview[:50]}")
    
    # Keyframes (scene changes)
    print(f"\n🎯 KEY SCENES")
    print(f"{'─'*40}")
    keyframes = extract_keyframes(video_path, f"{tmpdir}/keyframes", threshold=0.2)
    for fp in keyframes:
        analysis = analyze_frame(fp)
        text = analysis['text'][:80].replace('\n', ' | ') if analysis['text'] else ''
        print(f"  📍 {analysis['size']} | {'👤人有' if analysis['has_person'] else '🖥 screen'} | "
              f"skin={analysis['skin_pct']}% | {text[:60]}")
    
    # ── Summary ──
    print(f"\n📊 SUMMARY")
    print(f"{'─'*40}")
    
    # What's in this video?
    has_person_frames = [f for f in frame_results if f['analysis']['has_person']]
    has_whatsapp = any(f['analysis']['green_pct'] > 0.5 for f in frame_results)
    has_red_btn = any(f['analysis']['red_pct'] > 0.1 for f in frame_results)
    is_dark = all(f['analysis']['brightness'] < 30 for f in frame_results)
    has_text = any(f['analysis']['text_lines'] > 0 for f in frame_results)
    
    print(f"  Duration: {meta['duration_str']}s")
    print(f"  Resolution: {meta.get('resolution', '?')}")
    
    if has_person_frames:
        pct = len(has_person_frames) / len(frame_results) * 100
        print(f"  👤 Person visible: {pct:.0f}% of frames")
    
    # Determine video type
    if has_whatsapp and has_person_frames:
        print(f"  📱 Type: Video call recording (WhatsApp)")
    elif has_person_frames and len(has_person_frames) > len(frame_results) * 0.5:
        print(f"  🎥 Type: Selfie / Person talking to camera")
    elif is_dark:
        print(f"  🖥 Type: Screen recording (dark mode)")
    else:
        print(f"  🖥 Type: Screen recording")
    
    if has_red_btn:
        print(f"  🔴 Red button detected — call interface")
    
    # Extract all text from all frames
    all_text = []
    for f in frame_results:
        if f['analysis']['text']:
            all_text.append(f['analysis']['text'])
    
    if all_text:
        print(f"\n  📝 TEXT DETECTED:")
        seen = set()
        for t in all_text:
            for line in t.split('\n'):
                line = line.strip()
                if line and len(line) > 3 and line not in seen:
                    seen.add(line)
                    print(f"    • {line[:100]}")
    
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    
    print(f"\n{'═'*60}")
    print(f"  ✅ Analysis complete — {len(frames)} frames, {len(keyframes)} key scenes")
    print(f"{'═'*60}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 sonic_vision.py <video_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        sys.exit(1)
    
    analyze_video(path)
