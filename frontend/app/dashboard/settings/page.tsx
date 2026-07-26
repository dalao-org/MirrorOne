"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "@/app/_components/ui.module.css";
import { PlusIcon, XIcon } from "@/app/_components/Icons";

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
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [router]);

    const fetchSettings = async () => {
        try {
            const response = await fetch("/api/settings", {
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
            const response = await fetch(`/api/settings/${key}`, {
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

    const isModified = (setting: Setting) => {
        const original = JSON.stringify(setting.value);
        const edited = JSON.stringify(editedSettings[setting.key]);
        return original !== edited;
    };

    const addTag = (key: string) => {
        const input = newTagInputs[key]?.trim();
        if (!input) return;

        const currentValue = editedSettings[key] as string[];
        if (!currentValue.includes(input)) {
            handleValueChange(key, [...currentValue, input]);
        }
        setNewTagInputs((prev) => ({ ...prev, [key]: "" }));
    };

    const removeTag = (key: string, tag: string) => {
        const currentValue = editedSettings[key] as string[];
        handleValueChange(key, currentValue.filter((t) => t !== tag));
    };

    const renderSettingInput = (setting: Setting) => {
        const value = editedSettings[setting.key];

        if (setting.key === "mirror_type") {
            return (
                <select
                    className={styles.select}
                    aria-label={setting.key}
                    value={typeof value === "string" ? value : ""}
                    onChange={(e) => handleValueChange(setting.key, e.target.value)}
                    style={{ width: "auto" }}
                >
                    <option value="redirect">Redirect (use original URLs)</option>
                    <option value="cache">Cache (download and serve locally)</option>
                </select>
            );
        }

        switch (setting.value_type) {
            case "bool":
                return (
                    <label className={styles.toggle}>
                        <div className={`${styles.toggleTrack} ${value ? styles.toggleTrackOn : ""}`}>
                            <input
                                type="checkbox"
                                className={styles.toggleInput}
                                aria-label={`${setting.key}: ${value ? "enabled" : "disabled"}`}
                                checked={Boolean(value)}
                                onChange={(e) => handleValueChange(setting.key, e.target.checked)}
                            />
                            <div className={`${styles.toggleThumb} ${value ? styles.toggleThumbOn : ""}`} />
                        </div>
                        <span className={styles.toggleLabel} style={{ color: value ? "var(--admin-success)" : "var(--admin-text-muted)" }}>
                            {value ? "Enabled" : "Disabled"}
                        </span>
                    </label>
                );

            case "int":
                return (
                    <input
                        type="number"
                        className={styles.input}
                        aria-label={setting.key}
                        value={typeof value === "number" ? value : 0}
                        onChange={(e) => handleValueChange(setting.key, parseInt(e.target.value) || 0)}
                        style={{ maxWidth: "150px" }}
                    />
                );

            case "json":
                if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
                    return (
                        <div style={{ width: "100%" }}>
                            <div className={styles.tagList}>
                                {(value as string[]).map((tag) => (
                                    <span key={tag} className={styles.tag}>
                                        {tag}
                                        <button
                                            type="button"
                                            onClick={() => removeTag(setting.key, tag)}
                                            className={styles.tagRemove}
                                            aria-label={`Remove ${tag}`}
                                        >
                                            <XIcon size={12} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                            <div className={styles.tagInputRow}>
                                <input
                                    type="text"
                                    className={styles.input}
                                    placeholder="Add new item…"
                                    aria-label={`Add item to ${setting.key}`}
                                    value={newTagInputs[setting.key] || ""}
                                    onChange={(e) => setNewTagInputs((prev) => ({
                                        ...prev,
                                        [setting.key]: e.target.value,
                                    }))}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            e.preventDefault();
                                            addTag(setting.key);
                                        }
                                    }}
                                />
                                <button
                                    type="button"
                                    onClick={() => addTag(setting.key)}
                                    className={`${styles.btn} ${styles.btnSecondary}`}
                                >
                                    <PlusIcon size={14} />
                                    Add
                                </button>
                            </div>
                        </div>
                    );
                }
                return (
                    <textarea
                        className={styles.textarea}
                        aria-label={setting.key}
                        value={JSON.stringify(value, null, 2)}
                        onChange={(e) => {
                            try {
                                const parsed = JSON.parse(e.target.value);
                                handleValueChange(setting.key, parsed);
                            } catch {
                                // Invalid JSON — keep typing until it parses again
                            }
                        }}
                    />
                );

            default:
                return (
                    <input
                        type={setting.key.includes("token") || setting.key.includes("password") ? "password" : "text"}
                        className={styles.input}
                        aria-label={setting.key}
                        value={typeof value === "string" ? value : ""}
                        onChange={(e) => handleValueChange(setting.key, e.target.value)}
                    />
                );
        }
    };

    const getSettingGroup = (key: string): string => {
        const prefixes = ["mysql", "python", "mariadb", "httpd", "apr", "pip", "php", "misc_github", "github"];
        for (const prefix of prefixes) {
            if (key.startsWith(prefix + "_")) {
                return prefix;
            }
        }
        return "general";
    };

    const groupLabels: Record<string, string> = {
        general: "General settings",
        mysql: "MySQL",
        python: "Python",
        mariadb: "MariaDB",
        httpd: "Apache HTTPD",
        apr: "APR",
        pip: "pip / setuptools",
        php: "PHP",
        misc_github: "Misc GitHub projects",
        github: "GitHub",
    };

    const groupedSettings = settings.reduce((acc, setting) => {
        const group = getSettingGroup(setting.key);
        if (!acc[group]) acc[group] = [];
        acc[group].push(setting);
        return acc;
    }, {} as Record<string, Setting[]>);

    const groupOrder = ["general", "mysql", "python", "mariadb", "httpd", "apr", "pip", "php", "misc_github", "github"];
    const sortedGroups = groupOrder.filter((g) => groupedSettings[g]?.length > 0);

    if (loading) {
        return (
            <div className={styles.stack} style={{ gap: "1.5rem" }}>
                <div className={styles.skeleton} style={{ height: "1.75rem", width: "220px" }} />
                <div className={styles.skeleton} style={{ height: "140px" }} />
                <div className={styles.skeleton} style={{ height: "140px" }} />
            </div>
        );
    }

    return (
        <>
            <div className={styles.pageHeader}>
                <div>
                    <h2 className={styles.pageHeading}>Settings</h2>
                    <p className={styles.pageDescription}>
                        Configure the mirror mode and per-scraper behavior.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.alert} ${styles.alertDanger}`}>{error}</div>
            )}

            <div className={styles.stack} style={{ gap: "2rem" }}>
                {sortedGroups.map((group) => (
                    <div key={group}>
                        <h3
                            style={{
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                textTransform: "uppercase",
                                letterSpacing: "0.04em",
                                color: "var(--admin-text-faint)",
                                marginBottom: "0.875rem",
                                paddingBottom: "0.625rem",
                                borderBottom: "1px solid var(--admin-border)",
                            }}
                        >
                            {groupLabels[group] || group}
                        </h3>
                        <div className={styles.stack} style={{ gap: "1rem" }}>
                            {groupedSettings[group].map((setting) => {
                                const modified = isModified(setting);
                                return (
                                    <div
                                        key={setting.key}
                                        className={`${styles.card} ${styles.cardPad}`}
                                        style={{ borderColor: modified ? "var(--admin-warning-border)" : undefined }}
                                    >
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "1rem" }}>
                                            <div>
                                                <h4 className={`${styles.mono}`} style={{ margin: "0 0 0.25rem", fontSize: "0.9375rem", fontWeight: 600 }}>
                                                    {setting.key}
                                                </h4>
                                                {setting.description && (
                                                    <p className={styles.helpText}>
                                                        {setting.description}
                                                    </p>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => saveSetting(setting.key)}
                                                disabled={saving === setting.key || !modified}
                                                className={`${styles.btn} ${styles.btnSm} ${
                                                    saveSuccess === setting.key
                                                        ? styles.btnSuccess
                                                        : modified
                                                            ? styles.btnPrimary
                                                            : styles.btnSecondary
                                                }`}
                                                style={{ minWidth: "84px" }}
                                            >
                                                {saving === setting.key && <span className={styles.spinner} />}
                                                {saving === setting.key
                                                    ? "Saving…"
                                                    : saveSuccess === setting.key
                                                        ? "Saved"
                                                        : "Save"}
                                            </button>
                                        </div>
                                        <div>{renderSettingInput(setting)}</div>
                                        <div style={{ marginTop: "0.75rem", fontSize: "0.75rem", color: "var(--admin-text-faint)", display: "flex", justifyContent: "space-between" }}>
                                            <span>Type: {setting.value_type}</span>
                                            <span>Updated {new Date(setting.updated_at).toLocaleString()}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>
        </>
    );
}
