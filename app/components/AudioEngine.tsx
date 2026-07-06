'use client'

import { useRef, useEffect } from 'react'
import { usePlayerStore } from '@/lib/player-store'
import { addToHistory } from '@/lib/storage'
import { preloadNextTrack, getPreloadedUrl } from '@/lib/preloader'

const BACKEND = 'http://localhost:8005'

export default function AudioEngine() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const nextAudioRef = useRef<HTMLAudioElement | null>(null) // Pre-buffer audio
  const currentTrack = usePlayerStore((s) => s.currentTrack)
  const isPlaying = usePlayerStore((s) => s.isPlaying)
  const volume = usePlayerStore((s) => s.volume)
  const setProgress = usePlayerStore((s) => s.setProgress)
  const setDuration = usePlayerStore((s) => s.setDuration)
  const next = usePlayerStore((s) => s.next)
  const setLoading = usePlayerStore((s) => s.setLoading)
  const queue = usePlayerStore((s) => s.queue)
  const queueIndex = usePlayerStore((s) => s.queueIndex)

  // Init both audio elements
  useEffect(() => {
    if (!audioRef.current) {
      const a = new Audio()
      a.preload = 'auto'
      audioRef.current = a
    }
    if (!nextAudioRef.current) {
      const na = new Audio()
      na.preload = 'auto'
      nextAudioRef.current = na
    }
    const audio = audioRef.current
    audio.volume = volume
    nextAudioRef.current.volume = volume
  }, [volume])

  // Load & play current track
  useEffect(() => {
    const audio = audioRef.current
    const nextAudio = nextAudioRef.current
    if (!audio || !currentTrack) return

    const loadAudio = async () => {
      setLoading(true)

      // Detach old listeners on nextAudio
      if (nextAudio) {
        nextAudio.pause()
        nextAudio.src = ''
        nextAudio.load()
      }

      if (currentTrack.source === 'YouTube') {
        try {
          const cachedUrl = getPreloadedUrl(currentTrack.id)
          if (cachedUrl) {
            audio.crossOrigin = 'anonymous'
            audio.src = `${BACKEND}/proxy?url=${encodeURIComponent(cachedUrl)}`
          } else {
            const res = await fetch(currentTrack.audio)
            const data = await res.json()
            if (data.audio_url) {
              audio.crossOrigin = 'anonymous'
              audio.src = `${BACKEND}/proxy?url=${encodeURIComponent(data.audio_url)}`
            } else {
              audio.src = currentTrack.audio
            }
          }
        } catch {
          audio.src = currentTrack.audio
        }
      } else if (currentTrack.source === 'Jamendo' || currentTrack.source === 'Local') {
        audio.crossOrigin = 'anonymous'
        audio.src = currentTrack.audio
      } else {
        audio.src = ''
      }

      audio.load()
      try {
        if (isPlaying) await audio.play()
      } catch {}

      // Start preloading next track — use a hidden audio element for real pre-buffering
      const nextIdx = queueIndex + 1
      if (nextIdx < queue.length) {
        const nextTrack = queue[nextIdx]
        if (nextTrack) {
          preloadNextTrack(queue, queueIndex)
          // Actually pre-buffer audio data
          prebufferTrack(nextTrack, nextAudio!)
        }
      }
    }

    loadAudio()
  }, [currentTrack?.id])

  // Helper: pre-buffer a track's audio in the background
  const prebufferTrack = async (track: any, audioEl: HTMLAudioElement) => {
    try {
      let src = ''
      if (track.source === 'YouTube') {
        const cachedUrl = getPreloadedUrl(track.id)
        if (cachedUrl) {
          src = `${BACKEND}/proxy?url=${encodeURIComponent(cachedUrl)}`
        } else {
          const res = await fetch(track.audio)
          const data = await res.json()
          if (data.audio_url) {
            src = `${BACKEND}/proxy?url=${encodeURIComponent(data.audio_url)}`
          }
        }
      } else if (track.source === 'Jamendo' || track.source === 'Local') {
        src = track.audio
      }
      if (src) {
        audioEl.crossOrigin = 'anonymous'
        audioEl.src = src
        audioEl.load()
        // Start buffering but don't play
        audioEl.play().then(() => {
          audioEl.pause() // Buffer then pause
        }).catch(() => {})
      }
    } catch {}
  }

  // Handle play/pause
  useEffect(() => {
    const audio = audioRef.current
    if (!audio || !currentTrack) return

    if (isPlaying) {
      audio.play().catch(() => {})
    } else {
      audio.pause()
    }
  }, [isPlaying])

  // Event listeners
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const onTimeUpdate = () => setProgress(audio.currentTime)
    const onLoadedMeta = () => {
      setDuration(audio.duration || 0)
      setLoading(false)
      if (currentTrack) addToHistory(currentTrack)
    }
    const onEnded = () => {
      // Switch: if next pre-buffered, swap audio elements
      const nextAudio = nextAudioRef.current
      if (nextAudio && nextAudio.src && nextAudio.readyState >= 2) {
        // Swap refs: next becomes current
        const oldSrc = audio.src
        audio.src = nextAudio.src
        audio.load()
        audio.play().catch(() => {})
        nextAudio.src = ''
        nextAudio.load()
        // Still call next() to update state
        next()
      } else {
        next()
      }
    }
    const onError = () => {
      setLoading(false)
      if (currentTrack?.source === 'Demo') {
        setTimeout(() => next(), 1000)
      }
    }
    const onWaiting = () => setLoading(true)
    const onCanPlay = () => setLoading(false)

    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('loadedmetadata', onLoadedMeta)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError)
    audio.addEventListener('waiting', onWaiting)
    audio.addEventListener('canplay', onCanPlay)

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('loadedmetadata', onLoadedMeta)
      audio.removeEventListener('ended', onEnded)
      audio.removeEventListener('error', onError)
      audio.removeEventListener('waiting', onWaiting)
      audio.removeEventListener('canplay', onCanPlay)
    }
  }, [currentTrack?.id])

  return null
}
