"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface ScraperStatus {
    enabled: boolean;
    interval_hours: number;
    last_run: string | null;
    next_run: string | null;
    available_scrapers: string[];
}

interface LogMessage {
    level: "info" | "success" | "warning" | "error";
    message: string;
    scraper: string | null;
    timestamp: string | null;
    type?: string;
}

export default function DashboardPage() {
    const router = useRouter();
    const [status, setStatus] = useState<ScraperStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // WebSocket log console state
    const [showLogConsole, setShowLogConsole] = useState(false);
    const [logs, setLogs] = useState<LogMessage[]>([]);
    const [wsConnected, setWsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const logContainerRef = useRef<HTMLDivElement | null>(null);

    const getAuthHeaders = () => {
        const token = localStorage.getItem("access_token");
        return {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
        };
    };

    // Connect to WebSocket
    const connectWebSocket = useCallback(() => {
        const token = localStorage.getItem("access_token");
        if (!token) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const wsUrl = apiUrl.replace(/^http/, "ws") + `/api/scraper/ws/logs?token=${token}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsConnected(true);
            console.log("WebSocket connected");
        };

        ws.onmessage = (event) => {
            try {
                const msg: LogMessage = JSON.parse(event.data);
                if (msg.type === "ping") return;

                setLogs((prev) => [...prev, msg]);

                setTimeout(() => {
                    if (logContainerRef.current) {
                        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
                    }
                }, 50);
            } catch (e) {
                console.error("Failed to parse WebSocket message:", e);
            }
        };

        ws.onclose = () => {
            setWsConnected(false);
            console.log("WebSocket disconnected");
        };

        ws.onerror = (err) => {
            console.error("WebSocket error:", err);
            setWsConnected(false);
        };
    }, []);

    const disconnectWebSocket = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
    }, []);

    useEffect(() => {
        return () => {
            disconnectWebSocket();
        };
    }, [disconnectWebSocket]);

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
        disconnectWebSocket();
        localStorage.removeItem("access_token");
        localStorage.removeItem("token_expires_at");
        router.push("/login");
    };

    const handleRunScrape = async () => {
        try {
            setLogs([]);
            setShowLogConsole(true);

            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/scraper/run`, {
                method: "POST",
                headers: getAuthHeaders(),
            });

            if (!response.ok) {
                throw new Error("Failed to start scrape");
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : "Error starting scrape");
        }
    };

    const getLogColor = (level: string) => {
        switch (level) {
            case "success": return "#22c55e";
            case "warning": return "#f59e0b";
            case "error": return "#ef4444";
            default: return "#94a3b8";
        }
    };

    // Scraper capsule color based on name
    const getCapsuleColor = (name: string) => {
        const colors: Record<string, string> = {
            nginx: "#009639",
            httpd: "#D22128",
            mysql: "#4479A1",
            mariadb: "#003545",
            postgresql: "#336791",
            redis: "#DC382D",
            php: "#777BB4",
            python: "#3776AB",
            openssl: "#721412",
            curl: "#073551",
        };
        return colors[name] || "#6366f1";
    };

    if (loading) {
        return (
            <main className="container">
                <p>Loading...</p>
            </main>
        );
    }

    return (
        <main className="container" style={{ paddingTop: 0 }}>
            {/* Top Navigation Bar */}
            <nav style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 0",
                borderBottom: "1px solid rgba(255,255,255,0.1)",
                marginBottom: "2rem",
            }}>
                <h1 style={{ margin: 0, fontSize: "1.5rem" }}>📊 Dashboard</h1>

                {/* Navigation Links */}
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                    <Link
                        href="/dashboard/settings"
                        style={{
                            padding: "0.5rem 1rem",
                            borderRadius: "8px",
                            background: "rgba(255,255,255,0.05)",
                            color: "#e2e8f0",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            transition: "all 0.2s",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                        }}
                    >
                        ⚙️ Settings
                    </Link>
                    <Link
                        href="/dashboard/resources"
                        style={{
                            padding: "0.5rem 1rem",
                            borderRadius: "8px",
                            background: "rgba(255,255,255,0.05)",
                            color: "#e2e8f0",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            transition: "all 0.2s",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                        }}
                    >
                        📦 Resources
                    </Link>
                    <Link
                        href="/dashboard/logs"
                        style={{
                            padding: "0.5rem 1rem",
                            borderRadius: "8px",
                            background: "rgba(255,255,255,0.05)",
                            color: "#e2e8f0",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            transition: "all 0.2s",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                        }}
                    >
                        📋 Logs
                    </Link>
                    <button
                        onClick={handleLogout}
                        className="btn"
                        style={{
                            background: "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)",
                            padding: "0.5rem 1rem",
                            fontSize: "0.875rem",
                            marginLeft: "0.5rem",
                        }}
                    >
                        Logout
                    </button>
                </div>
            </nav>

            {error && (
                <div style={{
                    background: "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)",
                    color: "white",
                    padding: "0.75rem 1rem",
                    borderRadius: "12px",
                    marginBottom: "1.5rem",
                }}>
                    {error}
                </div>
            )}

            <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "1fr 2fr" }}>
                {/* Scheduler Status */}
                <div className="card" style={{
                    background: "linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)",
                    border: "1px solid rgba(99,102,241,0.2)",
                }}>
                    <h2 style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "1.5rem" }}>⏰</span>
                        <span>Scheduler Status</span>
                    </h2>
                    {status && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                            <div style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "0.5rem",
                                padding: "0.5rem 0.75rem",
                                background: status.enabled ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                                borderRadius: "8px",
                                border: `1px solid ${status.enabled ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
                            }}>
                                <span style={{
                                    width: "8px",
                                    height: "8px",
                                    borderRadius: "50%",
                                    background: status.enabled ? "#22c55e" : "#ef4444",
                                    boxShadow: `0 0 8px ${status.enabled ? "#22c55e" : "#ef4444"}`,
                                }} />
                                <span style={{ color: status.enabled ? "#22c55e" : "#ef4444", fontWeight: 500 }}>
                                    {status.enabled ? "Auto-scrape Enabled" : "Auto-scrape Disabled"}
                                </span>
                            </div>
                            <p style={{ margin: 0, color: "#94a3b8" }}>
                                <strong style={{ color: "#e2e8f0" }}>Interval:</strong> {status.interval_hours} hours
                            </p>
                            <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.875rem" }}>
                                <strong style={{ color: "#e2e8f0" }}>Last run:</strong><br />
                                {status.last_run ? new Date(status.last_run).toLocaleString() : "Never"}
                            </p>
                            <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.875rem" }}>
                                <strong style={{ color: "#e2e8f0" }}>Next run:</strong><br />
                                {status.next_run ? new Date(status.next_run).toLocaleString() : "Not scheduled"}
                            </p>
                        </div>
                    )}
                    <button
                        onClick={handleRunScrape}
                        className="btn btn-primary"
                        style={{
                            marginTop: "1.5rem",
                            width: "100%",
                            background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                            padding: "0.75rem",
                            fontSize: "1rem",
                            fontWeight: 600,
                        }}
                    >
                        🚀 Run Scrape Now
                    </button>
                </div>

                {/* Available Scrapers - Capsule Style */}
                <div className="card" style={{
                    background: "linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)",
                    border: "1px solid rgba(99,102,241,0.2)",
                }}>
                    <h2 style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "1.5rem" }}>🔧</span>
                        <span>Available Scrapers</span>
                        {status && (
                            <span style={{
                                marginLeft: "auto",
                                fontSize: "0.875rem",
                                padding: "0.25rem 0.75rem",
                                borderRadius: "9999px",
                                background: "rgba(99,102,241,0.2)",
                                color: "#a5b4fc",
                            }}>
                                {status.available_scrapers.length} scrapers
                            </span>
                        )}
                    </h2>
                    {status && (
                        <div style={{
                            display: "flex",
                            flexWrap: "wrap",
                            gap: "0.5rem",
                            maxHeight: "280px",
                            overflowY: "auto",
                            padding: "0.5rem 0",
                        }}>
                            {status.available_scrapers.map((scraper) => (
                                <span
                                    key={scraper}
                                    style={{
                                        display: "inline-flex",
                                        alignItems: "center",
                                        padding: "0.375rem 0.875rem",
                                        borderRadius: "9999px",
                                        background: `linear-gradient(135deg, ${getCapsuleColor(scraper)}33 0%, ${getCapsuleColor(scraper)}22 100%)`,
                                        border: `1px solid ${getCapsuleColor(scraper)}66`,
                                        color: "#e2e8f0",
                                        fontSize: "0.8125rem",
                                        fontWeight: 500,
                                        transition: "all 0.2s",
                                        cursor: "default",
                                    }}
                                >
                                    <span style={{
                                        width: "6px",
                                        height: "6px",
                                        borderRadius: "50%",
                                        background: getCapsuleColor(scraper),
                                        marginRight: "0.5rem",
                                        boxShadow: `0 0 6px ${getCapsuleColor(scraper)}`,
                                    }} />
                                    {scraper}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Real-time Log Console */}
            {showLogConsole && (
                <div className="card" style={{
                    marginTop: "1.5rem",
                    background: "linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.98) 100%)",
                    border: "1px solid rgba(99,102,241,0.2)",
                }}>
                    <div style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "1rem",
                    }}>
                        <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.75rem" }}>
                            <span>📺 Live Logs</span>
                            <span style={{
                                fontSize: "0.75rem",
                                padding: "0.25rem 0.75rem",
                                borderRadius: "9999px",
                                background: wsConnected
                                    ? "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)"
                                    : "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                                color: "white",
                                fontWeight: 500,
                            }}>
                                {wsConnected ? "● Connected" : "○ Disconnected"}
                            </span>
                        </h2>
                        <button
                            onClick={() => {
                                setShowLogConsole(false);
                                disconnectWebSocket();
                            }}
                            className="btn"
                            style={{
                                background: "rgba(239,68,68,0.2)",
                                border: "1px solid rgba(239,68,68,0.5)",
                                color: "#fca5a5",
                                padding: "0.375rem 1rem",
                                fontSize: "0.875rem",
                            }}
                        >
                            ✕ Close
                        </button>
                    </div>
                    <div
                        ref={logContainerRef}
                        style={{
                            background: "#020617",
                            borderRadius: "8px",
                            padding: "1rem",
                            maxHeight: "400px",
                            overflowY: "auto",
                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                            fontSize: "0.8125rem",
                            lineHeight: "1.6",
                            border: "1px solid rgba(255,255,255,0.05)",
                        }}
                    >
                        {logs.length === 0 ? (
                            <p style={{ color: "#475569", margin: 0, fontStyle: "italic" }}>
                                Waiting for logs...
                            </p>
                        ) : (
                            logs.map((log, index) => (
                                <div key={index} style={{ marginBottom: "0.25rem" }}>
                                    <span style={{ color: "#475569" }}>
                                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ""}
                                    </span>
                                    {" "}
                                    <span style={{ color: getLogColor(log.level) }}>
                                        {log.message}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </main>
    );
}
