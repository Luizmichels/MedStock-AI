/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Gera .next/standalone para a imagem Docker de produção.
  output: "standalone",
};

export default nextConfig;
