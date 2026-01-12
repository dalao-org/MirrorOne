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
    const [editedSettings, setEditedSettings] = useState<Record<string, Setting["value"]>>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);
    const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
    const [error, setError] = useState("");
    const [newTagInputs, setNewTagInputs] = useState<Record<string, string>>({});

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
            // Initialize edited settings with current values
            const edited: Record<string, Setting["value"]> = {};
            data.forEach((s: Setting) => {
                edited[s.key] = s.value;
            });
            setEditedSettings(edited);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error loading settings");
        } finally {
            setLoading(false);
        }
    };

    const handleValueChange = (key: string, value: Setting["value"]) => {
        setEditedSettings((prev) => ({ ...prev, [key]: value }));
    };

    const saveSetting = async (key: string) => {
        setSaving(key);
        setSaveSuccess(null);
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/settings/${key}`, {
                method: "PUT",
                headers: getAuthHeaders(),
                body: JSON.stringify({ value: editedSettings[key] }),
            });

            if (!response.ok) throw new Error("Failed to update setting");

            await fetchSettings();
            setSaveSuccess(key);
            setTimeout(() => setSaveSuccess(null), 2000);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Error updating setting");
        } finally {
            setSaving(null);
        }
    };

    // Check if a setting has been modified
    const isModified = (setting: Setting) => {
        const original = JSON.stringify(setting.value);
        const edited = JSON.stringify(editedSettings[setting.key]);
        return original !== edited;
    };

    // Add tag to JSON array
    const addTag = (key: string) => {
        const input = newTagInputs[key]?.trim();
        if (!input) return;

        const currentValue = editedSettings[key] as string[];
        if (!currentValue.includes(input)) {
            handleValueChange(key, [...currentValue, input]);
        }
        setNewTagInputs((prev) => ({ ...prev, [key]: "" }));
    };

    // Remove tag from JSON array
    const removeTag = (key: string, tag: string) => {
        const currentValue = editedSettings[key] as string[];
        handleValueChange(key, currentValue.filter((t) => t !== tag));
    };

    const renderSettingInput = (setting: Setting) => {
        const value = editedSettings[setting.key];

        // Special case: mirror_type dropdown
        if (setting.key === "mirror_type") {
            return (
                <select
                    value={value as string}
                    onChange={(e) => handleValueChange(setting.key, e.target.value)}
                    style={{
                        background: "#1e293b",
                        border: "1px solid rgba(99,102,241,0.3)",
                        borderRadius: "8px",
                        padding: "0.5rem 0.75rem",
                        color: "#e2e8f0",
                        fontSize: "0.9rem",
                        cursor: "pointer",
                    }}
                >
                    <option value="redirect">🔗 Redirect (use original URLs)</option>
                    <option value="cache">💾 Cache (download and serve locally)</option>
                </select>
            );
        }

        switch (setting.value_type) {
            case "bool":
                return (
                    <label style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.75rem",
                        cursor: "pointer",
                    }}>
                        <div style={{
                            position: "relative",
                            width: "48px",
                            height: "24px",
                            borderRadius: "12px",
                            background: value ? "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)" : "#475569",
                            transition: "all 0.2s",
                            cursor: "pointer",
                        }}>
                            <input
                                type="checkbox"
                                checked={value as boolean}
                                onChange={(e) => handleValueChange(setting.key, e.target.checked)}
                                style={{
                                    opacity: 0,
                                    position: "absolute",
                                    width: "100%",
                                    height: "100%",
                                    cursor: "pointer",
                                }}
                            />
                            <div style={{
                                position: "absolute",
                                top: "2px",
                                left: value ? "26px" : "2px",
                                width: "20px",
                                height: "20px",
                                borderRadius: "50%",
                                background: "white",
                                transition: "all 0.2s",
                                boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
                            }} />
                        </div>
                        <span style={{ color: value ? "#22c55e" : "#94a3b8" }}>
                            {value ? "Enabled" : "Disabled"}
                        </span>
                    </label>
                );

            case "int":
                return (
                    <input
                        type="number"
                        className="input"
                        value={value as number}
                        onChange={(e) => handleValueChange(setting.key, parseInt(e.target.value) || 0)}
                        style={{
                            maxWidth: "150px",
                            background: "#1e293b",
                            border: "1px solid rgba(99,102,241,0.3)",
                            borderRadius: "8px",
                            padding: "0.5rem 0.75rem",
                            color: "#e2e8f0",
                        }}
                    />
                );

            case "json":
                // Check if it's an array of strings (for tags UI)
                if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
                    return (
                        <div style={{ width: "100%" }}>
                            {/* Tags display */}
                            <div style={{
                                display: "flex",
                                flexWrap: "wrap",
                                gap: "0.5rem",
                                marginBottom: "0.75rem",
                            }}>
                                {(value as string[]).map((tag) => (
                                    <span
                                        key={tag}
                                        style={{
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "0.5rem",
                                            padding: "0.375rem 0.75rem",
                                            borderRadius: "9999px",
                                            background: "linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(99,102,241,0.1) 100%)",
                                            border: "1px solid rgba(99,102,241,0.4)",
                                            color: "#c7d2fe",
                                            fontSize: "0.875rem",
                                        }}
                                    >
                                        {tag}
                                        <button
                                            onClick={() => removeTag(setting.key, tag)}
                                            style={{
                                                background: "none",
                                                border: "none",
                                                color: "#ef4444",
                                                cursor: "pointer",
                                                padding: 0,
                                                fontSize: "1rem",
                                                lineHeight: 1,
                                            }}
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                            </div>
                            {/* Add new tag input */}
                            <div style={{ display: "flex", gap: "0.5rem" }}>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="Add new item..."
                                    value={newTagInputs[setting.key] || ""}
                                    onChange={(e) => setNewTagInputs((prev) => ({
                                        ...prev,
                                        [setting.key]: e.target.value
                                    }))}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            e.preventDefault();
                                            addTag(setting.key);
                                        }
                                    }}
                                    style={{
                                        flex: 1,
                                        background: "#1e293b",
                                        border: "1px solid rgba(99,102,241,0.3)",
                                        borderRadius: "8px",
                                        padding: "0.5rem 0.75rem",
                                        color: "#e2e8f0",
                                    }}
                                />
                                <button
                                    onClick={() => addTag(setting.key)}
                                    className="btn"
                                    style={{
                                        background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                                        padding: "0.5rem 1rem",
                                        fontSize: "0.875rem",
                                    }}
                                >
                                    + Add
                                </button>
                            </div>
                        </div>
                    );
                }
                // Fallback to textarea for other JSON
                return (
                    <textarea
                        className="input"
                        value={JSON.stringify(value, null, 2)}
                        onChange={(e) => {
                            try {
                                const parsed = JSON.parse(e.target.value);
                                handleValueChange(setting.key, parsed);
                            } catch {
                                // Invalid JSON, still update the text
                            }
                        }}
                        style={{
                            minHeight: "100px",
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: "0.875rem",
                            background: "#1e293b",
                            border: "1px solid rgba(99,102,241,0.3)",
                            borderRadius: "8px",
                            padding: "0.75rem",
                            color: "#e2e8f0",
                            width: "100%",
                        }}
                    />
                );

            default:
                return (
                    <input
                        type={setting.key.includes("token") || setting.key.includes("password") ? "password" : "text"}
                        className="input"
                        value={value as string}
                        onChange={(e) => handleValueChange(setting.key, e.target.value)}
                        style={{
                            background: "#1e293b",
                            border: "1px solid rgba(99,102,241,0.3)",
                            borderRadius: "8px",
                            padding: "0.5rem 0.75rem",
                            color: "#e2e8f0",
                            width: "100%",
                        }}
                    />
                );
        }
    };

    // Group settings by module prefix
    const getSettingGroup = (key: string): string => {
        const prefixes = ["mysql", "python", "mariadb", "httpd", "apr", "pip", "php", "github"];
        for (const prefix of prefixes) {
            if (key.startsWith(prefix + "_")) {
                return prefix;
            }
        }
        return "general";
    };

    const groupLabels: Record<string, string> = {
        general: "🔧 General Settings",
        mysql: "🐬 MySQL",
        python: "🐍 Python",
        mariadb: "🗄️ MariaDB",
        httpd: "🌐 Apache HTTPD",
        apr: "📦 APR",
        pip: "📦 pip/setuptools",
        php: "🐘 PHP",
        github: "🐙 GitHub",
    };

    const groupedSettings = settings.reduce((acc, setting) => {
        const group = getSettingGroup(setting.key);
        if (!acc[group]) acc[group] = [];
        acc[group].push(setting);
        return acc;
    }, {} as Record<string, Setting[]>);

    // Define group order
    const groupOrder = ["general", "mysql", "python", "mariadb", "httpd", "apr", "pip", "php", "github"];
    const sortedGroups = groupOrder.filter(g => groupedSettings[g]?.length > 0);

    if (loading) {
        return <main className="container"><p>Loading...</p></main>;
    }

    return (
        <main className="container">
            <header style={{ marginBottom: "2rem" }}>
                <Link href="/dashboard" style={{ color: "#94a3b8", textDecoration: "none" }}>
                    ← Back to Dashboard
                </Link>
                <h1 style={{ marginTop: "1rem" }}>⚙️ Settings</h1>
            </header>

            {error && (
                <div style={{
                    background: "linear-gradient(135deg, #dc2626 0%, #991b1b 100%)",
                    color: "white",
                    padding: "0.75rem 1rem",
                    borderRadius: "12px",
                    marginBottom: "1.5rem"
                }}>
                    {error}
                </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
                {sortedGroups.map((group) => (
                    <div key={group}>
                        <h2 style={{
                            color: "#e2e8f0",
                            fontSize: "1.25rem",
                            marginBottom: "1rem",
                            paddingBottom: "0.5rem",
                            borderBottom: "1px solid rgba(99,102,241,0.3)",
                        }}>
                            {groupLabels[group] || group}
                        </h2>
                        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                            {groupedSettings[group].map((setting) => (
                                <div
                                    key={setting.key}
                                    className="card"
                                    style={{
                                        background: "linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)",
                                        border: isModified(setting)
                                            ? "1px solid rgba(234,179,8,0.5)"
                                            : "1px solid rgba(99,102,241,0.2)",
                                    }}
                                >
                                    <div style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "flex-start",
                                        gap: "1rem",
                                        marginBottom: "1rem",
                                    }}>
                                        <div>
                                            <h3 style={{
                                                marginBottom: "0.25rem",
                                                color: "#f1f5f9",
                                                fontFamily: "'JetBrains Mono', monospace",
                                                fontSize: "1rem",
                                            }}>
                                                {setting.key}
                                            </h3>
                                            {setting.description && (
                                                <p style={{
                                                    color: "#f59e0b",
                                                    fontSize: "0.875rem",
                                                    margin: 0,
                                                }}>
                                                    {setting.description}
                                                </p>
                                            )}
                                        </div>
                                        <button
                                            onClick={() => saveSetting(setting.key)}
                                            disabled={saving === setting.key || !isModified(setting)}
                                            className="btn"
                                            style={{
                                                background: saveSuccess === setting.key
                                                    ? "linear-gradient(135deg, #22c55e 0%, #16a34a 100%)"
                                                    : isModified(setting)
                                                        ? "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
                                                        : "linear-gradient(135deg, #475569 0%, #334155 100%)",
                                                border: isModified(setting)
                                                    ? "1px solid #f59e0b"
                                                    : "1px solid #64748b",
                                                padding: "0.375rem 1rem",
                                                fontSize: "0.875rem",
                                                opacity: saving === setting.key ? 0.7 : 1,
                                                cursor: isModified(setting) ? "pointer" : "default",
                                                minWidth: "80px",
                                                color: isModified(setting) ? "#fff" : "#cbd5e1",
                                            }}
                                        >
                                            {saving === setting.key
                                                ? "Saving..."
                                                : saveSuccess === setting.key
                                                    ? "✓ Saved"
                                                    : "Save"}
                                        </button>
                                    </div>
                                    <div>
                                        {renderSettingInput(setting)}
                                    </div>
                                    <div style={{
                                        marginTop: "0.75rem",
                                        fontSize: "0.75rem",
                                        color: "#64748b",
                                        display: "flex",
                                        justifyContent: "space-between",
                                    }}>
                                        <span>Type: {setting.value_type}</span>
                                        <span>Updated: {new Date(setting.updated_at).toLocaleString()}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </main>
    );
}

