import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.evetech.net',
        port: '',
        pathname: '/types/**',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        // The INTERNAL_API_BASE_URL is set in docker-compose.yml for the frontend service.
        // It points to the backend service. Fallback for local development.
        destination: `${process.env.INTERNAL_API_BASE_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;