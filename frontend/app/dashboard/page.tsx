"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface ScraperStatus {
    enabled: boolean;
    interval_hours: number;
    last_run: string | null;
    next_run: string | null;
    available_scrapers: string[];
}

export default function DashboardPage() {
    const router = useRouter();
    const [status, setStatus] = useState<ScraperStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

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

        fetchStatus();
    }, [router]);

    const fetchStatus = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/scraper/status`, {
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                router.push("/login");
                return;
            }

            if (!response.ok) {
                throw new Error("Failed to fetch status");
            }

            const data = await response.json();
            setStatus(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error loading status");
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("token_expires_at");
        router.push("/login");
    };

    const handleRunScrape = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/scraper/run`, {
                method: "POST",
                headers: getAuthHeaders(),
            });

            if (!response.ok) {
                throw new Error("Failed to start scrape");
            }

            alert("Scrape job started in background!");
        } catch (err) {
            alert(err instanceof Error ? err.message : "Error starting scrape");
        }
    };

    if (loading) {
        return (
            <main className="container">
                <p>Loading...</p>
            </main>
        );
    }

    return (
        <main className="container">
            <header style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "2rem",
            }}>
                <h1>Dashboard</h1>
                <button onClick={handleLogout} className="btn" style={{ background: "#333" }}>
                    Logout
                </button>
            </header>

            {error && (
                <div style={{
                    background: "#dc2626",
                    color: "white",
                    padding: "0.75rem",
                    borderRadius: "8px",
                    marginBottom: "1rem",
                }}>
                    {error}
                </div>
            )}

            <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
                {/* Scheduler Status */}
                <div className="card">
                    <h2 style={{ marginBottom: "1rem" }}>⏰ Scheduler Status</h2>
                    {status && (
                        <div>
                            <p><strong>Auto-scrape:</strong> {status.enabled ? "✅ Enabled" : "❌ Disabled"}</p>
                            <p><strong>Interval:</strong> {status.interval_hours} hours</p>
                            <p><strong>Last run:</strong> {status.last_run || "Never"}</p>
                            <p><strong>Next run:</strong> {status.next_run || "Not scheduled"}</p>
                        </div>
                    )}
                    <button
                        onClick={handleRunScrape}
                        className="btn btn-primary"
                        style={{ marginTop: "1rem" }}
                    >
                        Run Scrape Now
                    </button>
                </div>

                {/* Available Scrapers */}
                <div className="card">
                    <h2 style={{ marginBottom: "1rem" }}>🔧 Available Scrapers</h2>
                    {status && (
                        <ul style={{ listStyle: "none" }}>
                            {status.available_scrapers.map((scraper) => (
                                <li key={scraper} style={{ padding: "0.5rem 0" }}>
                                    • {scraper}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Quick Links */}
                <div className="card">
                    <h2 style={{ marginBottom: "1rem" }}>🔗 Quick Links</h2>
                    <ul style={{ listStyle: "none" }}>
                        <li style={{ padding: "0.5rem 0" }}>
                            <Link href="/dashboard/settings">⚙️ Settings</Link>
                        </li>
                        <li style={{ padding: "0.5rem 0" }}>
                            <Link href="/dashboard/resources">📦 Resources</Link>
                        </li>
                        <li style={{ padding: "0.5rem 0" }}>
                            <Link href="/dashboard/logs">📋 Scrape Logs</Link>
                        </li>
                    </ul>
                </div>
            </div>
        </main>
    );
}
