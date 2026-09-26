import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (see frontend/Dockerfile)
  output: "standalone",
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "date-fns",
      "@tanstack/react-table",
      "@tanstack/react-query",
    ],
  },
};

export default nextConfig;
