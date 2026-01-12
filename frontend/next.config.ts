import type { NextConfig } from "next";

// Read backend URL from environment variable
const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
    output: "standalone",
    reactStrictMode: true,
    async rewrites() {
        return [
            // Proxy /src (file downloads)
            {
                source: "/src/:path*",
                destination: `${backendUrl}/src/:path*`,
            },
            // Proxy /api (REST API)
            {
                source: "/api/:path*",
                destination: `${backendUrl}/api/:path*`,
            },
            // Proxy /health
            {
                source: "/health",
                destination: `${backendUrl}/health`,
            },
            // Proxy static files served by backend
            {
                source: "/suggest_versions.txt",
                destination: `${backendUrl}/suggest_versions.txt`,
            },
            {
                source: "/latest_meta.json",
                destination: `${backendUrl}/latest_meta.json`,
            },
            {
                source: "/resource.json",
                destination: `${backendUrl}/resource.json`,
            },
            {
                source: "/_redirects",
                destination: `${backendUrl}/_redirects`,
            },
        ];
    },
};

export default nextConfig;
