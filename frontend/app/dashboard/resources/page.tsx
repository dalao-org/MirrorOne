"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

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
    }, [router]);

    const fetchResources = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/resources`, {
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
            console.error(err);
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
        return <main className="container"><p>Loading...</p></main>;
    }

    return (
        <main className="container">
            <header style={{ marginBottom: "2rem" }}>
                <Link href="/dashboard" style={{ color: "#888" }}>← Back to Dashboard</Link>
                <h1 style={{ marginTop: "1rem" }}>📦 Resources ({data?.total || 0})</h1>
            </header>

            <div className="card" style={{ marginBottom: "1.5rem" }}>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                    <input
                        type="text"
                        className="input"
                        placeholder="Filter by filename..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        style={{ flex: 1, minWidth: "200px" }}
                    />
                    <select
                        className="input"
                        value={sourceFilter}
                        onChange={(e) => setSourceFilter(e.target.value)}
                        style={{ width: "auto" }}
                    >
                        <option value="">All Sources</option>
                        {sources.map((source) => (
                            <option key={source} value={source}>{source}</option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="card">
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                        <tr style={{ borderBottom: "1px solid var(--border)" }}>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Filename</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Version</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>Source</th>
                            <th style={{ textAlign: "left", padding: "0.75rem" }}>URL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredResources.map((resource) => (
                            <tr key={resource.file_name} style={{ borderBottom: "1px solid var(--border)" }}>
                                <td style={{ padding: "0.75rem", fontFamily: "monospace", fontSize: "0.9rem" }}>
                                    {resource.file_name}
                                </td>
                                <td style={{ padding: "0.75rem" }}>{resource.version}</td>
                                <td style={{ padding: "0.75rem" }}>
                                    <span style={{
                                        background: "#333",
                                        padding: "0.25rem 0.5rem",
                                        borderRadius: "4px",
                                        fontSize: "0.8rem",
                                    }}>
                                        {resource.source}
                                    </span>
                                </td>
                                <td style={{ padding: "0.75rem" }}>
                                    <a href={resource.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "0.9rem" }}>
                                        View →
                                    </a>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {filteredResources.length === 0 && (
                    <p style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                        No resources found
                    </p>
                )}
            </div>
        </main>
    );
}
