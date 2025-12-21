/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true
  },
  transpilePackages: ['@sakhi/api', '@sakhi/ui', '@sakhi/config']
};

module.exports = nextConfig;
