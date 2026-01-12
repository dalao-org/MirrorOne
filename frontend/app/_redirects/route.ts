import { NextResponse } from "next/server";

export async function GET() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
        const response = await fetch(`${apiUrl}/_redirects`, { cache: "no-store" });
        const text = await response.text();
        return new NextResponse(text, {
            status: response.status,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
    } catch {
        return new NextResponse("# Error: Backend unavailable\n", {
            status: 503,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
    }
}
