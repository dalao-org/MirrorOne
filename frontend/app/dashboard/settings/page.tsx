"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

interface Setting {
    id: number;
    key: string;
    value: string | number | boolean | string[];
    value_type: string;
    description: string | null;
    updated_at: string;
}

export default function SettingsPage() {
    const router = useRouter();
    const [settings, setSettings] = useState<Setting[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);
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
        fetchSettings();
    }, [router]);

    const fetchSettings = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/settings`, {
                headers: getAuthHeaders(),
            });

            if (response.status === 401) {
                localStorage.removeItem("access_token");
                router.push("/login");
                return;
            }

            if (!response.ok) throw new Error("Failed to fetch settings");

            const data = await response.json();
            setSettings(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error loading settings");
        } finally {
            setLoading(false);
        }
    };

    const updateSetting = async (key: string, value: string | number | boolean | string[]) => {
        setSaving(key);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/settings/${key}`, {
                method: "PUT",
                headers: getAuthHeaders(),
                body: JSON.stringify({ value }),
            });

            if (!response.ok) throw new Error("Failed to update setting");

            await fetchSettings();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error updating setting");
        } finally {
            setSaving(null);
        }
    };

    const renderSettingInput = (setting: Setting) => {
        switch (setting.value_type) {
            case "bool":
                return (
                    <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <input
                            type="checkbox"
                            checked={setting.value as boolean}
                            onChange={(e) => updateSetting(setting.key, e.target.checked)}
                            disabled={saving === setting.key}
                        />
                        {setting.value ? "Enabled" : "Disabled"}
                    </label>
                );
            case "int":
                return (
                    <input
                        type="number"
                        className="input"
                        value={setting.value as number}
                        onChange={(e) => updateSetting(setting.key, parseInt(e.target.value))}
                        disabled={saving === setting.key}
                        style={{ maxWidth: "150px" }}
                    />
                );
            case "json":
                return (
                    <textarea
                        className="input"
                        value={JSON.stringify(setting.value, null, 2)}
                        onChange={(e) => {
                            try {
                                const parsed = JSON.parse(e.target.value);
                                updateSetting(setting.key, parsed);
                            } catch {
                                // Invalid JSON, don't update
                            }
                        }}
                        disabled={saving === setting.key}
                        style={{ minHeight: "80px", fontFamily: "monospace" }}
                    />
                );
            default:
                return (
                    <input
                        type={setting.key.includes("token") || setting.key.includes("password") ? "password" : "text"}
                        className="input"
                        value={setting.value as string}
                        onChange={(e) => updateSetting(setting.key, e.target.value)}
                        disabled={saving === setting.key}
                    />
                );
        }
    };

    if (loading) {
        return <main className="container"><p>Loading...</p></main>;
    }

    return (
        <main className="container">
            <header style={{ marginBottom: "2rem" }}>
                <Link href="/dashboard" style={{ color: "#888" }}>← Back to Dashboard</Link>
                <h1 style={{ marginTop: "1rem" }}>⚙️ Settings</h1>
            </header>

            {error && (
                <div style={{ background: "#dc2626", color: "white", padding: "0.75rem", borderRadius: "8px", marginBottom: "1rem" }}>
                    {error}
                </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                {settings.map((setting) => (
                    <div key={setting.key} className="card">
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "2rem" }}>
                            <div style={{ flex: 1 }}>
                                <h3 style={{ marginBottom: "0.5rem" }}>{setting.key}</h3>
                                {setting.description && (
                                    <p style={{ color: "#888", fontSize: "0.9rem", marginBottom: "0.75rem" }}>
                                        {setting.description}
                                    </p>
                                )}
                            </div>
                            <div style={{ minWidth: "200px" }}>
                                {renderSettingInput(setting)}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </main>
    );
}
