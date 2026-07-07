# Sonic Player 🎵

![Next.js](https://img.shields.io/badge/Next.js-16-black) ![TypeScript](https://img.shields.io/badge/TypeScript-6-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Python-green) ![License](https://img.shields.io/badge/License-MIT-gold)

**Sonic Player** is a modern, feature-rich music streaming application with a sleek dark/gold interface. Search and stream music from YouTube, view synchronized lyrics, manage playlists, and enjoy a premium listening experience.

Built with **Next.js 16** (frontend) + **FastAPI** (backend).

---

## ✨ Features

- 🔍 **Smart Search** — Search music across YouTube with grouped results (artists, albums, tracks)
- ▶️ **Audio Streaming** — Stream high-quality audio directly in the browser
- 🎬 **Video Mode** — Watch music videos inline
- 📜 **Synced Lyrics** — Auto-scrolling lyrics with LRC support (powered by syncedlyrics)
- 📥 **Downloads** — Save tracks and videos locally for offline playback
- ❤️ **Liked Tracks** — Save favorites to your personal library
- 📋 **Playlists** — Create and manage custom playlists
- 🎨 **Visualizer** — Real-time audio visualization with particle effects
- 🌙 **Dark/Gold Theme** — Premium warm-night aesthetic
- ⚡ **Fast Backend** — yt-dlp with intelligent caching for sub-second stream loading

---

## 🖼️ Screenshots

![Sonic Player](https://img.youtube.com/vi/hqdefault.jpg)

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ 
- **Python** 3.10+
- **yt-dlp** — `pip install yt-dlp`
- **ffmpeg** — `sudo apt install ffmpeg`

### Setup

```bash
# 📱 One-command install (recommended)
bash install.sh

# ▶️ Start
bash start.sh
```

### Manual Setup

```bash
# 1. Clone
git clone https://github.com/CYBER-HACKER-Studio/sonic-player.git
cd sonic-player

# 2. Frontend
npm install
npm run build

# 3. Backend
pip install -r backend/requirements.txt

# 4. Run
python3 backend/main.py &
npx next start -p 3004
```

### Termux (Android)

```bash
# Install Termux packages
pkg install nodejs python ffmpeg

# Clone & install
git clone https://github.com/CYBER-HACKER-Studio/sonic-player.git
cd sonic-player
bash install.sh

# Run
bash start.sh
```

Open **http://localhost:3004** in your browser.

> ⚡ Downloaded tracks play from the local folder — no internet needed.

---

## 🏗️ Project Structure

```
sonic-player/
├── app/                    # Next.js frontend
│   ├── components/         # React components
│   │   ├── AudioEngine.tsx    # Audio playback engine
│   │   ├── NowPlaying.tsx     # Now playing screen
│   │   ├── SearchView.tsx     # Search interface
│   │   ├── Sidebar.tsx        # Navigation sidebar
│   │   ├── PlayerBar.tsx      # Bottom player bar
│   │   ├── LyricsPanel.tsx    # Synced lyrics display
│   │   ├── Visualizer.tsx     # Audio visualizer
│   │   ├── LibraryView.tsx    # Library (likes/downloads)
│   │   ├── PlaylistPanel.tsx  # Playlist management
│   │   ├── HomeView.tsx       # Home/landing view
│   │   ├── SettingsPanel.tsx  # Settings panel
│   │   └── VideoModal.tsx     # Video player modal
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Main page
│   └── globals.css         # Global styles
├── backend/                # FastAPI backend
│   ├── main.py             # API server
│   └── downloads/          # Local downloads
├── lib/                    # Shared utilities
│   ├── api.ts              # API client
│   ├── player-store.tsx    # Zustand player state
│   ├── storage.ts          # localStorage helpers
│   └── settings.ts         # App settings
└── public/                 # Static assets
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 18, TypeScript |
| **Styling** | Tailwind CSS 4, Radix UI |
| **State** | Zustand 5 |
| **Animation** | Framer Motion |
| **Backend** | FastAPI (Python) |
| **Streaming** | yt-dlp, FFmpeg |
| **Lyrics** | syncedlyrics LRC |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or pull requests.

---

## ⚠️ Disclaimer

This project uses **yt-dlp** to stream audio from YouTube for **personal and educational use only**.

- 🚫 **Not affiliated with or endorsed by YouTube/Google**
- 🚫 **Does not bypass copyright or replace official streaming**
- ⚠️ **Users are solely responsible** for complying with YouTube's Terms of Service and applicable copyright laws
- 🔍 **yt-dlp** is an optional dependency — the app also supports Jamendo (licensed music) and local file playback

The developer provides this software as-is for educational purposes and assumes **no liability** for misuse or Terms of Service violations. If you have concerns about copyright, please use the Jamendo API or your own local files.

---

<div align="center">
  <sub>Built by <a href="https://cyber-hacker.studio">CYBER·HACKER Studio</a> 🖤</sub>
</div>
