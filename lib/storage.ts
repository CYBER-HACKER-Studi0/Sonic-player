// Local storage for Sonic Player - Favorites, History, Playlists, Play Stats

import type { Track } from './player-store'

const KEYS = {
  likes: 'sonic_likes',
  history: 'sonic_history',
  playStats: 'sonic_playstats',
  playlists: 'sonic_playlists',
  downloads: 'sonic_downloads',
  searchCache: 'sonic_search_cache',
}

// ─── Favorites / Likes ───

export function getLikes(): string[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(KEYS.likes) || '[]') } catch { return [] }
}

export function isLiked(trackId: string): boolean {
  return getLikes().includes(trackId)
}

export function getLikedTracks(allTracks: Track[]): Track[] {
  const ids = getLikes()
  const history = getHistory()
  const matched: Track[] = []
  const seen = new Set<string>()
  for (const id of ids) {
    const t = history.find(h => h.id === id)
    if (t && !seen.has(t.id)) { matched.push(t); seen.add(t.id) }
  }
  return matched
}

export function toggleLike(trackId: string): boolean {
  const likes = getLikes()
  const idx = likes.indexOf(trackId)
  if (idx >= 0) likes.splice(idx, 1)
  else likes.push(trackId)
  localStorage.setItem(KEYS.likes, JSON.stringify(likes))
  return idx < 0
}

// ─── Play Stats (Smart History) ───

export interface PlayRecord {
  track: Track
  count: number
  lastPlayed: number
  firstPlayed: number
}

export function getPlayStats(): PlayRecord[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(KEYS.playStats) || '[]') } catch { return [] }
}

export function recordPlay(track: Track) {
  const stats = getPlayStats()
  const existing = stats.find(s => s.track.id === track.id)
  if (existing) {
    existing.count++
    existing.lastPlayed = Date.now()
  } else {
    stats.unshift({
      track,
      count: 1,
      lastPlayed: Date.now(),
      firstPlayed: Date.now(),
    })
  }
  // Keep top 100
  const trimmed = stats.slice(0, 100)
  localStorage.setItem(KEYS.playStats, JSON.stringify(trimmed))
}

/** Last N unique played tracks (for "آخر ما سمعته") */
export function getRecentTracks(limit = 10): Track[] {
  return getPlayStats()
    .sort((a, b) => b.lastPlayed - a.lastPlayed)
    .slice(0, limit)
    .map(s => s.track)
}

/** Most played tracks (for "الأكثر استماعاً") */
export function getTopTracks(limit = 10): Track[] {
  return getPlayStats()
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
    .map(s => s.track)
}

/** Extract genre tags from play history for recommendations */
export function getListeningGenres(): string[] {
  const stats = getPlayStats()
  const genreCount = new Map<string, number>()
  for (const s of stats) {
    // From Jamendo tags in track ID (jam_ prefix)
    const tags = s.track.id.split('_')
    // Try to extract genre from track source or album name
    const words = `${s.track.album} ${s.track.artist} ${s.track.title}`.toLowerCase()
    const knownGenres = ['pop', 'rock', 'jazz', 'electronic', 'hip hop', 'rap', 'classical',
      'rnb', 'soul', 'blues', 'country', 'folk', 'metal', 'punk', 'reggae',
      'dance', 'latin', 'ambient', 'lo fi', 'indie', 'alternative', 'acoustic',
      'edm', 'techno', 'house', 'trap', 'drill', 'afro', 'arabic', 'oriental',
      'trap', 'drill', 'grime', 'garage', 'synth', 'dubstep', 'dnb',
    ]
    for (const genre of knownGenres) {
      if (words.includes(genre)) {
        genreCount.set(genre, (genreCount.get(genre) || 0) + s.count)
      }
    }
    // Give bonus to sources
    if (s.track.source === 'Jamendo') {
      genreCount.set('jamendo', (genreCount.get('jamendo') || 0) + s.count)
    }
  }
  return [...genreCount.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(e => e[0])
}

export function clearPlayStats() {
  localStorage.setItem(KEYS.playStats, '[]')
}

// ─── Recently Played (legacy) ───

export function getHistory(): Track[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(KEYS.history) || '[]') } catch { return [] }
}

export function addToHistory(track: Track) {
  const history = getHistory()
  const filtered = history.filter(t => t.id !== track.id)
  filtered.unshift(track)
  const trimmed = filtered.slice(0, 50)
  localStorage.setItem(KEYS.history, JSON.stringify(trimmed))
}

export function clearHistory() {
  localStorage.setItem(KEYS.history, '[]')
}

// ─── Downloads ───

export function trackDownload(track: Track) {
  const downloads = getDownloads()
  if (downloads.find(t => t.id === track.id)) return
  downloads.unshift(track)
  localStorage.setItem(KEYS.downloads, JSON.stringify(downloads.slice(0, 50)))
}

/** Download to folder and update track to play locally */
const BACKEND = 'http://localhost:8005'
export async function downloadToFolder(track: Track): Promise<boolean> {
  if (!track.videoId) return false
  try {
    const res = await fetch(`${BACKEND}/download_local/${track.videoId}?title=${encodeURIComponent(track.title)}`)
    const data = await res.json()
    if (data.success && data.path) {
      // Update the track's audio to local path
      const updatedTrack = { ...track, audio: `${BACKEND}${data.path}`, source: 'Local' as const }
      // Update in downloads list
      const downloads = getDownloads()
      const idx = downloads.findIndex(t => t.id === track.id)
      if (idx >= 0) {
        downloads[idx] = updatedTrack
        localStorage.setItem(KEYS.downloads, JSON.stringify(downloads))
      }
      return true
    }
    return false
  } catch {
    return false
  }
}

export function getDownloads(): Track[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(KEYS.downloads) || '[]') } catch { return [] }
}

// ─── Search Cache (keep last query) ───

export function saveSearchQuery(query: string, results: any[]) {
  try {
    localStorage.setItem(KEYS.searchCache, JSON.stringify({ query, results, time: Date.now() }))
  } catch {}
}

export function getSearchCache(): { query: string; results: any[] } | null {
  try {
    const raw = localStorage.getItem(KEYS.searchCache)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (Date.now() - data.time > 3600000) return null // 1 hour expiry
    return data
  } catch { return null }
}

// ─── Playlists ───

export interface Playlist {
  id: string
  name: string
  description: string
  tracks: Track[]
  created: number
  updated: number
}

export function getPlaylists(): Playlist[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(KEYS.playlists) || '[]') } catch { return [] }
}

export function createPlaylist(name: string, description = ''): Playlist {
  const playlists = getPlaylists()
  const pl: Playlist = {
    id: `pl_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name,
    description,
    tracks: [],
    created: Date.now(),
    updated: Date.now(),
  }
  playlists.push(pl)
  localStorage.setItem(KEYS.playlists, JSON.stringify(playlists))
  return pl
}

export function deletePlaylist(id: string) {
  const playlists = getPlaylists().filter(p => p.id !== id)
  localStorage.setItem(KEYS.playlists, JSON.stringify(playlists))
}

export function addToPlaylist(playlistId: string, track: Track) {
  const playlists = getPlaylists()
  const pl = playlists.find(p => p.id === playlistId)
  if (!pl) return
  if (pl.tracks.find(t => t.id === track.id)) return // no dupes
  pl.tracks.push(track)
  pl.updated = Date.now()
  localStorage.setItem(KEYS.playlists, JSON.stringify(playlists))
}

export function removeFromPlaylist(playlistId: string, trackId: string) {
  const playlists = getPlaylists()
  const pl = playlists.find(p => p.id === playlistId)
  if (!pl) return
  pl.tracks = pl.tracks.filter(t => t.id !== trackId)
  pl.updated = Date.now()
  localStorage.setItem(KEYS.playlists, JSON.stringify(playlists))
}

export function renamePlaylist(id: string, name: string) {
  const playlists = getPlaylists()
  const pl = playlists.find(p => p.id === id)
  if (!pl) return
  pl.name = name
  pl.updated = Date.now()
  localStorage.setItem(KEYS.playlists, JSON.stringify(playlists))
}
