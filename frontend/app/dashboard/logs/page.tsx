"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "@/app/_components/ui.module.css";
import { InboxIcon } from "@/app/_components/Icons";

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
        fetchLogs();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    const fetchLogs = async () => {
        try {
            const response = await fetch("/api/scraper/logs?limit=100", {
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
            setError(err instanceof Error ? err.message : "Error loading logs");
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "success": return styles.badgeSuccess;
            case "partial": return styles.badgeWarning;
            case "failed": return styles.badgeDanger;
            default: return styles.badgeNeutral;
        }
    };

    const getStatusDot = (status: string) => {
        switch (status) {
            case "success": return styles.dotSuccess;
            case "partial": return styles.dotWarning;
            case "failed": return styles.dotDanger;
            default: return styles.dotNeutral;
        }
    };

    const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString();

    if (loading) {
        return (
            <div className={styles.stack} style={{ gap: "1.5rem" }}>
                <div className={styles.skeleton} style={{ height: "1.75rem", width: "220px" }} />
                <div className={styles.skeleton} style={{ height: "400px" }} />
            </div>
        );
    }

    return (
        <>
            <div className={styles.pageHeader}>
                <div>
                    <h2 className={styles.pageHeading}>Scrape logs</h2>
                    <p className={styles.pageDescription}>
                        Last {data?.total ?? 0} scrape runs, most recent first.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.alert} ${styles.alertDanger}`}>{error}</div>
            )}

            <div className={styles.card}>
                {!data?.logs || data.logs.length === 0 ? (
                    <div className={styles.emptyState}>
                        <span className={styles.emptyIcon}><InboxIcon size={32} /></span>
                        <span className={styles.emptyTitle}>No logs yet</span>
                        <span className={styles.emptyText}>Run a scrape to see results here.</span>
                    </div>
                ) : (
                    <div className={styles.tableWrap}>
                        <table className={styles.table}>
                            <thead>
                                <tr>
                                    <th>Time</th>
                                    <th>Scraper</th>
                                    <th>Status</th>
                                    <th>Resources</th>
                                    <th>Duration</th>
                                    <th>Error</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.logs.map((log) => (
                                    <tr key={log.id}>
                                        <td className={styles.tdMuted} style={{ fontSize: "0.8125rem" }}>
                                            {formatDate(log.started_at)}
                                        </td>
                                        <td>{log.scraper_name}</td>
                                        <td>
                                            <span className={`${styles.badge} ${getStatusBadge(log.status)}`}>
                                                <span className={`${styles.dot} ${getStatusDot(log.status)}`} />
                                                {log.status}
                                            </span>
                                        </td>
                                        <td className={styles.tdMono}>{log.resources_count}</td>
                                        <td className={`${styles.tdMono} ${styles.tdMuted}`}>{log.duration_seconds.toFixed(2)}s</td>
                                        <td
                                            style={{
                                                fontSize: "0.8125rem",
                                                color: "var(--admin-danger)",
                                                maxWidth: "300px",
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }}
                                            title={log.error_message ?? undefined}
                                        >
                                            {log.error_message || "—"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </>
    );
}
