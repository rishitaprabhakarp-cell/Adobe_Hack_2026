import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the frontend to call the backend API from any origin during development
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "X-Frame-Options", value: "DENY" }],
      },
    ];
  },
};

export default nextConfig;
