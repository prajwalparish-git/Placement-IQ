/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // No ESLint dependency: `next build` type-checks; ruff and pytest guard the Python side.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
