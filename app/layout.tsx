import type { Metadata } from 'next'
import { Inter, Space_Grotesk } from 'next/font/google'
import './globals.css'
import { PlayerProvider } from '@/lib/player-store'
import PlayerBar from '@/app/components/PlayerBar'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Sonic — Music Player',
  description: 'Premium music experience',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ar" dir="ltr" className="dark">
      <body className={`${inter.variable} ${spaceGrotesk.variable} antialiased`}>
        <PlayerProvider>
          <div className="flex h-screen w-screen overflow-hidden bg-sonic-base vinyl-noise">
            {children}
          </div>
        </PlayerProvider>
      </body>
    </html>
  )
}
