import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
