import { NextResponse } from "next/server";

export async function GET() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
        const response = await fetch(`${apiUrl}/health`, {
            cache: "no-store",
        });

        if (!response.ok) {
            return NextResponse.json(
                {
                    status: "unhealthy",
                    error: "Backend unavailable",
                    last_scrape: null,
                    last_success: null,
                    next_scrape: null,
                },
                { status: 503 }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch {
        return NextResponse.json(
            {
                status: "unhealthy",
                error: "Cannot connect to backend",
                last_scrape: null,
                last_success: null,
                next_scrape: null,
            },
            { status: 503 }
        );
    }
}
