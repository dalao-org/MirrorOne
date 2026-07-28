"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import styles from "@/app/_components/ui.module.css";
import { useToast } from "@/app/_components/useToast";
import { ToastContainer } from "@/app/_components/ToastContainer";
import {
    ClockIcon,
    GearIcon,
    TerminalIcon,
    PlayIcon,
    DownloadIcon,
    XIcon,
    BoxIcon,
} from "@/app/_components/Icons";

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

interface ManifestStatus {
    state: "healthy" | "degraded" | "disabled";
    revision?: string | null;
    last_success?: string | null;
    last_error?: string | null;
    checksum_coverage_percent?: number;
    cache_coverage_percent?: number;
    statistics?: {
        artifact_count: number;
        with_upstream_checksum: number;
        cached: number;
        conflict_count: number;
    };
    recent_events?: Array<{
        event: string;
        filename?: string;
        timestamp?: string;
    }>;
}

export default function DashboardPage() {
    const router = useRouter();
    const [status, setStatus] = useState<ScraperStatus | null>(null);
    const [manifestStatus, setManifestStatus] = useState<ManifestStatus | null>(null);
    const [rebuildingManifest, setRebuildingManifest] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const { toasts, showToast, dismissToast } = useToast();

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

        // Use current page's host for WebSocket connection
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${wsProtocol}//${window.location.host}/api/scraper/ws/logs?token=${token}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            setWsConnected(true);
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
        };

        ws.onerror = () => {
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
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    const fetchStatus = async () => {
        try {
            const [scraperResult, manifestResult] = await Promise.allSettled([
                fetch("/api/scraper/status", { headers: getAuthHeaders() }),
                fetch("/api/manifests/status", { headers: getAuthHeaders() }),
            ]);

            if (scraperResult.status === "rejected") {
                throw scraperResult.reason;
            }
            const response = scraperResult.value;

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
            if (
                manifestResult.status === "fulfilled"
                && manifestResult.value.ok
            ) {
                setManifestStatus(await manifestResult.value.json());
            } else {
                setManifestStatus(null);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error loading status");
        } finally {
            setLoading(false);
        }
    };

    const handleManifestRebuild = async () => {
        setRebuildingManifest(true);
        try {
            const response = await fetch("/api/manifests/rebuild", {
                method: "POST",
                headers: getAuthHeaders(),
            });
            const data = await response.json();
            setManifestStatus(data);
            if (!response.ok) {
                throw new Error(data.last_error || "Manifest rebuild failed");
            }
            showToast("Manifest rebuilt", "success");
        } catch (err) {
            showToast(err instanceof Error ? err.message : "Manifest rebuild failed", "error");
        } finally {
            setRebuildingManifest(false);
        }
    };

    const handleRunScrape = async () => {
        try {
            setLogs([]);
            setShowLogConsole(true);

            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }

            const response = await fetch("/api/scraper/run", {
                method: "POST",
                headers: getAuthHeaders(),
            });

            if (!response.ok) {
                throw new Error("Failed to start scrape");
            }
            showToast("Scrape started", "success");
        } catch (err) {
            showToast(err instanceof Error ? err.message : "Error starting scrape", "error");
        }
    };

    const handleRecache = async (overwrite: boolean = false) => {
        try {
            setLogs([]);
            setShowLogConsole(true);

            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }

            const response = await fetch(`/api/scraper/recache?overwrite=${overwrite}&max_concurrent=5`, {
                method: "POST",
                headers: getAuthHeaders(),
            });

            if (!response.ok) {
                throw new Error("Failed to start re-cache");
            }
            showToast(overwrite ? "Re-caching all resources" : "Re-caching missing resources", "success");
        } catch (err) {
            showToast(err instanceof Error ? err.message : "Error starting re-cache", "error");
        }
    };

    const getLogColor = (level: string) => {
        switch (level) {
            case "success": return "var(--admin-success)";
            case "warning": return "var(--admin-warning)";
            case "error": return "var(--admin-danger)";
            default: return "var(--admin-text-muted)";
        }
    };

    // Scraper capsule color based on name (brand colors)
    const getCapsuleColor = (name: string) => {
        const colors: Record<string, string> = {
            nginx: "#009639",
            httpd: "#D22128",
            mysql: "#4479A1",
            mariadb: "#c0765a",
            postgresql: "#336791",
            redis: "#DC382D",
            php: "#777BB4",
            python: "#3776AB",
            openssl: "#8a9aa8",
            curl: "#073551",
        };
        return colors[name] || "var(--admin-accent)";
    };

    if (loading) {
        return (
            <div className={styles.stack} style={{ gap: "1.5rem" }}>
                <div className={styles.skeleton} style={{ height: "1.75rem", width: "220px" }} />
                <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "1fr 2fr" }}>
                    <div className={styles.skeleton} style={{ height: "260px" }} />
                    <div className={styles.skeleton} style={{ height: "260px" }} />
                </div>
            </div>
        );
    }

    return (
        <>
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />

            <div className={styles.pageHeader}>
                <div>
                    <h2 className={styles.pageHeading}>Overview</h2>
                    <p className={styles.pageDescription}>
                        Scheduler status, available scrapers, and live scrape activity.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.alert} ${styles.alertDanger}`}>{error}</div>
            )}

            <div style={{ display: "grid", gap: "1.5rem", gridTemplateColumns: "1fr 2fr" }}>
                {/* Scheduler Status */}
                <div className={`${styles.card} ${styles.cardPad}`}>
                    <div className={styles.cardHeader}>
                        <h3 className={styles.cardTitle}>
                            <span className={styles.cardIcon}><ClockIcon size={17} /></span>
                            Scheduler
                        </h3>
                    </div>
                    {status && (
                        <div className={styles.stack} style={{ gap: "0.75rem" }}>
                            <span className={`${styles.badge} ${status.enabled ? styles.badgeSuccess : styles.badgeDanger}`} style={{ width: "fit-content" }}>
                                <span className={`${styles.dot} ${status.enabled ? styles.dotSuccess : styles.dotDanger}`} />
                                {status.enabled ? "Auto-scrape enabled" : "Auto-scrape disabled"}
                            </span>
                            <p style={{ margin: 0, color: "var(--admin-text-muted)", fontSize: "0.875rem" }}>
                                <strong style={{ color: "var(--admin-text)" }}>Interval:</strong> every {status.interval_hours}h
                            </p>
                            <p style={{ margin: 0, color: "var(--admin-text-muted)", fontSize: "0.8125rem" }}>
                                <strong style={{ color: "var(--admin-text)" }}>Last run:</strong><br />
                                {status.last_run ? new Date(status.last_run).toLocaleString() : "Never"}
                            </p>
                            <p style={{ margin: 0, color: "var(--admin-text-muted)", fontSize: "0.8125rem" }}>
                                <strong style={{ color: "var(--admin-text)" }}>Next run:</strong><br />
                                {status.next_run ? new Date(status.next_run).toLocaleString() : "Not scheduled"}
                            </p>
                        </div>
                    )}

                    <button
                        onClick={handleRunScrape}
                        className={`${styles.btn} ${styles.btnPrimary} ${styles.btnBlock}`}
                        style={{ marginTop: "1.25rem" }}
                    >
                        <PlayIcon size={15} />
                        Run scrape now
                    </button>

                    <div style={{ marginTop: "1.125rem" }}>
                        <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.75rem", color: "var(--admin-text-faint)", textAlign: "center" }}>
                            Re-cache (download without re-scraping)
                        </p>
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                                onClick={() => handleRecache(false)}
                                className={`${styles.btn} ${styles.btnSuccess} ${styles.btnSm}`}
                                style={{ flex: 1 }}
                            >
                                Skip existing
                            </button>
                            <button
                                onClick={() => handleRecache(true)}
                                className={`${styles.btn} ${styles.btnDanger} ${styles.btnSm}`}
                                style={{ flex: 1 }}
                            >
                                <DownloadIcon size={13} />
                                Overwrite all
                            </button>
                        </div>
                    </div>
                </div>

                {/* Available Scrapers */}
                <div className={`${styles.card} ${styles.cardPad}`}>
                    <div className={styles.cardHeader}>
                        <h3 className={styles.cardTitle}>
                            <span className={styles.cardIcon}><GearIcon size={17} /></span>
                            Available scrapers
                        </h3>
                        {status && (
                            <span className={`${styles.badge} ${styles.badgeNeutral}`}>
                                {status.available_scrapers.length} total
                            </span>
                        )}
                    </div>
                    {status && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", maxHeight: "280px", overflowY: "auto", padding: "0.25rem 0" }}>
                            {status.available_scrapers.map((scraper) => (
                                <span
                                    key={scraper}
                                    className={styles.pill}
                                    style={{ "--pc": getCapsuleColor(scraper) } as React.CSSProperties}
                                >
                                    <span className={styles.pillDot} />
                                    {scraper}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className={`${styles.card} ${styles.cardPad}`} style={{ marginTop: "1.5rem" }}>
                <div className={styles.cardHeader}>
                    <h3 className={styles.cardTitle}>
                        <span className={styles.cardIcon}><BoxIcon size={17} /></span>
                        Artifact manifest
                    </h3>
                    <span className={`${styles.badge} ${
                        manifestStatus?.state === "healthy"
                            ? styles.badgeSuccess
                            : manifestStatus?.state === "disabled"
                                ? styles.badgeNeutral
                                : styles.badgeDanger
                    }`}>
                        {manifestStatus?.state || "unknown"}
                    </span>
                </div>
                <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
                    <div>
                        <p className={styles.helpText}>Artifacts</p>
                        <strong>{manifestStatus?.statistics?.artifact_count ?? 0}</strong>
                    </div>
                    <div>
                        <p className={styles.helpText}>Checksum coverage</p>
                        <strong>{manifestStatus?.checksum_coverage_percent ?? 0}%</strong>
                    </div>
                    <div>
                        <p className={styles.helpText}>Cache coverage</p>
                        <strong>{manifestStatus?.cache_coverage_percent ?? 0}%</strong>
                    </div>
                    <div>
                        <p className={styles.helpText}>Conflicts</p>
                        <strong>{manifestStatus?.statistics?.conflict_count ?? 0}</strong>
                    </div>
                </div>
                <div style={{ marginTop: "1rem", display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "end" }}>
                    <div style={{ minWidth: 0 }}>
                        <p className={styles.helpText}>
                            Revision: <span className={styles.mono}>{manifestStatus?.revision || "not published"}</span>
                        </p>
                        <p className={styles.helpText}>
                            Last success: {manifestStatus?.last_success
                                ? new Date(manifestStatus.last_success).toLocaleString()
                                : "Never"}
                        </p>
                        {manifestStatus?.last_error && (
                            <p style={{ color: "var(--admin-danger)", fontSize: "0.75rem", margin: "0.25rem 0 0" }}>
                                {manifestStatus.last_error}
                            </p>
                        )}
                        {manifestStatus?.recent_events?.[0] && (
                            <p className={styles.helpText}>
                                Latest integrity event: {manifestStatus.recent_events[0].event}
                                {manifestStatus.recent_events[0].filename
                                    ? ` · ${manifestStatus.recent_events[0].filename}`
                                    : ""}
                            </p>
                        )}
                    </div>
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                        <a
                            href="/manifests/artifacts.json"
                            target="_blank"
                            rel="noreferrer"
                            className={`${styles.btn} ${styles.btnSecondary} ${styles.btnSm}`}
                        >
                            Open manifest
                        </a>
                        <button
                            onClick={handleManifestRebuild}
                            disabled={rebuildingManifest}
                            className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`}
                        >
                            {rebuildingManifest ? "Rebuilding…" : "Rebuild"}
                        </button>
                    </div>
                </div>
            </div>

            {/* Real-time Log Console */}
            {showLogConsole && (
                <div className={`${styles.card} ${styles.cardPad}`} style={{ marginTop: "1.5rem" }}>
                    <div className={styles.cardHeader}>
                        <h3 className={styles.cardTitle}>
                            <span className={styles.cardIcon}><TerminalIcon size={17} /></span>
                            Live logs
                            <span className={`${styles.badge} ${wsConnected ? styles.badgeSuccess : styles.badgeDanger}`}>
                                <span className={`${styles.dot} ${wsConnected ? styles.dotSuccess : styles.dotDanger}`} />
                                {wsConnected ? "Connected" : "Disconnected"}
                            </span>
                        </h3>
                        <button
                            onClick={() => {
                                setShowLogConsole(false);
                                disconnectWebSocket();
                            }}
                            className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`}
                        >
                            <XIcon size={14} />
                            Close
                        </button>
                    </div>
                    <div ref={logContainerRef} className={styles.logConsole}>
                        {logs.length === 0 ? (
                            <p style={{ color: "var(--admin-text-faint)", margin: 0, fontStyle: "italic" }}>
                                Waiting for logs…
                            </p>
                        ) : (
                            logs.map((log, index) => (
                                <div key={index} className={styles.logLine}>
                                    <span className={styles.logTime}>
                                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ""}
                                    </span>
                                    <span style={{ color: getLogColor(log.level) }}>{log.message}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
