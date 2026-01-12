import { NextResponse } from "next/server";

export async function GET() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
        const response = await fetch(`${apiUrl}/resource.json`, { cache: "no-store" });
        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("[resource.json] Backend unavailable:", error);
        return NextResponse.json(
            { error: "Backend unavailable" },
            { status: 503 }
        );
    }
}
