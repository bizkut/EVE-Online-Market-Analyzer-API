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
};

export default nextConfig;