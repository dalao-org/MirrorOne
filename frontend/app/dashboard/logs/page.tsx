"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface ScrapeLog {
    id: number;
    scraper_name: string;
    status: string;
    resources_count: number;
    error_message: string | null;
    duration_seconds: number;
    started_at: string;
    finished_at: string | null;
}

interface LogsResponse {
    total: number;
    logs: ScrapeLog[];
}

export default function LogsPage() {
    const router = useRouter();
    const [data, setData] = useState<LogsResponse | null>(null);
    const [loading, setLoading] = useState(true);

    const getAuthHeaders = () => {
        const token = localStorage.getItem("access_token");
        return {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
        };
    };

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) {
            router.push("/login");
            return;
        }
        fetchLogs();
    }, [router]);

    const fetchLogs = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/scraper/logs?limit=100`, {
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                router.push("/login");
                return;
            }

            if (!response.ok) throw new Error("Failed to fetch logs");

            const result = await response.json();
            setData(result);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "success": return "#22c55e";
            case "partial": return "#f59e0b";
            case "failed": return "#ef4444";
            default: return "#888";
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    if (loading) {
        return <main className="container"><p>Loading...</p></main>;
    }

    return (
        <main className="container">
            <header style={{ marginBottom: "2rem" }}>
                <Link href="/dashboard" style={{ color: "#888" }}>← Back to Dashboard</Link>
                <h1 style={{ marginTop: "1rem" }}>📋 Scrape Logs ({data?.total || 0})</h1>
            </header>

            <div className="card">
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Time</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Scraper</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Status</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Resources</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Duration</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Error</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data?.logs.map((log) => (
                            <tr key={log.id} style={{ borderBottom: "1px solid var(--border)" }}>
                                <td style={{ padding: "0.75rem", fontSize: "0.9rem" }}>
                                    {formatDate(log.started_at)}
                                </td>
                                <td style={{ padding: "0.75rem" }}>{log.scraper_name}</td>
                                <td style={{ padding: "0.75rem" }}>
                                    <span style={{
                                        background: getStatusColor(log.status),
                                        color: "white",
                                        padding: "0.25rem 0.5rem",
                                        borderRadius: "4px",
                                        fontSize: "0.8rem",
                                    }}>
                                        {log.status}
                                    </span>
                                </td>
                                <td style={{ padding: "0.75rem" }}>{log.resources_count}</td>
                                <td style={{ padding: "0.75rem" }}>{log.duration_seconds.toFixed(2)}s</td>
                                <td style={{ padding: "0.75rem", fontSize: "0.85rem", color: "#ef4444", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis" }}>
                                    {log.error_message || "-"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {(!data?.logs || data.logs.length === 0) && (
                    <p style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                        No logs yet. Run a scrape to see results here.
                    </p>
                )}
            </div>
        </main>
    );
}
