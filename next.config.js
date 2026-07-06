/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'imgjam.com' },
      { protocol: 'https', hostname: 'freemusicarchive.org' },
      { protocol: 'https', hostname: '*.jamendo.com' },
    ],
  },
}

module.exports = nextConfig