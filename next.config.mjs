/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: { optimizePackageImports: ['lucide-react'] },
  allowedDevOrigins: ['*.e2b.app', '127.0.0.1', 'localhost']
};
export default nextConfig;
