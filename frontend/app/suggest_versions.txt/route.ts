import { NextResponse } from "next/server";

export async function GET() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
        const response = await fetch(`${apiUrl}/suggest_versions.txt`, {
            cache: "no-store",
        });

        if (!response.ok) {
            return new NextResponse("# Error: Could not fetch versions\n", {
                status: response.status,
                headers: { "Content-Type": "text/plain; charset=utf-8" },
            });
        }

        const text = await response.text();
        return new NextResponse(text, {
            status: 200,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
    } catch {
        return new NextResponse("# Error: Backend unavailable\n", {
            status: 503,
            headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
    }
}
