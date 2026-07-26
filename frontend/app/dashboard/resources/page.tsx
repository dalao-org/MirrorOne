"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "@/app/_components/ui.module.css";
import { SearchIcon, ExternalLinkIcon, InboxIcon } from "@/app/_components/Icons";

interface Resource {
    file_name: string;
    url: string;
    version: string;
    source: string;
    updated_at: string;
}

interface ResourcesResponse {
    total: number;
    resources: Resource[];
}

export default function ResourcesPage() {
    const router = useRouter();
    const [data, setData] = useState<ResourcesResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [filter, setFilter] = useState("");
    const [sourceFilter, setSourceFilter] = useState("");

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
        fetchResources();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    const fetchResources = async () => {
        try {
            const response = await fetch("/api/resources", {
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                router.push("/login");
                return;
            }

            if (!response.ok) throw new Error("Failed to fetch resources");

            const result = await response.json();
            setData(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error loading resources");
        } finally {
            setLoading(false);
        }
    };

    const filteredResources = data?.resources.filter((r) => {
        const matchesName = r.file_name.toLowerCase().includes(filter.toLowerCase());
        const matchesSource = !sourceFilter || r.source === sourceFilter;
        return matchesName && matchesSource;
    }) || [];

    const sources = [...new Set(data?.resources.map((r) => r.source) || [])];

    if (loading) {
        return (
            <div className={styles.stack} style={{ gap: "1.5rem" }}>
                <div className={styles.skeleton} style={{ height: "1.75rem", width: "220px" }} />
                <div className={styles.skeleton} style={{ height: "56px" }} />
                <div className={styles.skeleton} style={{ height: "360px" }} />
            </div>
        );
    }

    return (
        <>
            <div className={styles.pageHeader}>
                <div>
                    <h2 className={styles.pageHeading}>Resources</h2>
                    <p className={styles.pageDescription}>
                        {data?.total ?? 0} mirrored files across {sources.length} sources.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.alert} ${styles.alertDanger}`}>{error}</div>
            )}

            <div className={`${styles.card} ${styles.cardPad}`} style={{ marginBottom: "1.25rem" }}>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                    <div style={{ position: "relative", flex: 1, minWidth: "220px" }}>
                        <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--admin-text-faint)", display: "flex" }}>
                            <SearchIcon size={16} />
                        </span>
                        <input
                            type="text"
                            className={styles.input}
                            placeholder="Filter by filename…"
                            aria-label="Filter by filename"
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            style={{ paddingLeft: "2.25rem" }}
                        />
                    </div>
                    <select
                        className={styles.select}
                        aria-label="Filter by source"
                        value={sourceFilter}
                        onChange={(e) => setSourceFilter(e.target.value)}
                        style={{ width: "auto", minWidth: "160px" }}
                    >
                        <option value="">All sources</option>
                        {sources.map((source) => (
                            <option key={source} value={source}>{source}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className={styles.card}>
                {filteredResources.length === 0 ? (
                    <div className={styles.emptyState}>
                        <span className={styles.emptyIcon}><InboxIcon size={32} /></span>
                        <span className={styles.emptyTitle}>No resources found</span>
                        <span className={styles.emptyText}>
                            {data && data.total > 0 ? "Try a different filter." : "Run a scrape first to populate the mirror."}
                        </span>
                    </div>
                ) : (
                    <div className={styles.tableWrap}>
                        <table className={styles.table}>
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Version</th>
                                    <th>Source</th>
                                    <th>URL</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredResources.map((resource) => (
                                    <tr key={resource.file_name}>
                                        <td className={styles.tdMono}>{resource.file_name}</td>
                                        <td className={`${styles.tdMono} ${styles.tdMuted}`}>{resource.version}</td>
                                        <td>
                                            <span className={`${styles.badge} ${styles.badgeNeutral}`}>{resource.source}</span>
                                        </td>
                                        <td>
                                            <a
                                                href={resource.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className={styles.link}
                                                style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem", fontSize: "0.8125rem" }}
                                            >
                                                View <ExternalLinkIcon size={13} />
                                            </a>
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
