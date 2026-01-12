"use client";

import { useEffect, useState } from "react";

interface HealthData {
    status: string;
    version: string;
    mirror_type: string;
    last_scrape: string | null;
    last_success: string | null;
    next_scrape: string | null;
}

interface Resource {
    file_name: string;
    url: string;
    version: string;
    updated_at: string;
}

interface ResourcesData {
    total: number;
    sources: Record<string, Resource[]>;
}

type Theme = "light" | "dark" | "system";

export default function Home() {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [resources, setResources] = useState<ResourcesData | null>(null);
    const [loading, setLoading] = useState(true);
    const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
    const [theme, setTheme] = useState<Theme>("system");
    const [effectiveTheme, setEffectiveTheme] = useState<"light" | "dark">("dark");

    // Detect system theme preference and handle theme changes
    useEffect(() => {
        // Get stored preference or default to system
        const stored = localStorage.getItem("theme") as Theme | null;
        if (stored) {
            setTheme(stored);
        }

        // System preference media query
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

        const updateEffectiveTheme = () => {
            if (theme === "system") {
                setEffectiveTheme(mediaQuery.matches ? "dark" : "light");
            } else {
                setEffectiveTheme(theme);
            }
        };

        updateEffectiveTheme();

        const listener = () => updateEffectiveTheme();
        mediaQuery.addEventListener("change", listener);
        return () => mediaQuery.removeEventListener("change", listener);
    }, [theme]);

    const toggleTheme = () => {
        const next: Theme = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
        setTheme(next);
        localStorage.setItem("theme", next);
    };

    // Theme colors
    const colors = effectiveTheme === "dark" ? {
        bg: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        text: "#e2e8f0",
        textMuted: "#94a3b8",
        cardBg: "linear-gradient(135deg, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.9) 100%)",
        cardBorder: "rgba(99,102,241,0.2)",

        // Specific
        heading: "#f8fafc",
        itemBorder: "rgba(99,102,241,0.1)",
        codeText: "#e2e8f0",

        // Status: Success
        successBg: "rgba(34,197,94,0.15)",
        successBorder: "rgba(34,197,94,0.4)",
        successText: "#22c55e",

        // Status: Error
        errorBg: "rgba(239,68,68,0.15)",
        errorBorder: "rgba(239,68,68,0.4)",
        errorText: "#ef4444",

        // Redirect/Blue Mode
        blueBg: "rgba(99,102,241,0.15)",
        blueBorder: "rgba(99,102,241,0.4)",
        blueText: "#818cf8",

        // Elements
        buttonBg: "rgba(255,255,255,0.1)",
        buttonText: "#94a3b8",
        toggleBg: "rgba(255,255,255,0.1)",

    } : {
        bg: "#f1f5f9",
        text: "#334155",
        textMuted: "#64748b",
        cardBg: "#ffffff",
        cardBorder: "#e2e8f0",

        // Specific
        heading: "#1e293b",
        itemBorder: ("#e2e8f0"),
        codeText: "#0f172a",

        // Status: Success
        successBg: "#dcfce7",
        successBorder: "#bbf7d0",
        successText: "#166534",

        // Status: Error
        errorBg: "#fee2e2",
        errorBorder: "#fecaca",
        errorText: "#991b1b",

        // Redirect/Blue Mode
        blueBg: "#e0e7ff",
        blueBorder: "#c7d2fe",
        blueText: "#4338ca",

        // Elements
        buttonBg: "#ffffff",
        buttonText: "#475569",
        toggleBg: "rgba(0,0,0,0.05)",
    };

    useEffect(() => {
        const fetchData = async () => {
            // Use relative URLs - Next.js rewrites will proxy to backend

            try {
                const [healthRes, resourcesRes] = await Promise.all([
                    fetch("/health", { cache: "no-store" }),
                    fetch("/api/resources/public", { cache: "no-store" }),
                ]);

                if (healthRes.ok) {
                    setHealth(await healthRes.json());
                }
                if (resourcesRes.ok) {
                    setResources(await resourcesRes.json());
                }
            } catch {
                // Silently fail
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const formatTime = (isoString: string | null) => {
        if (!isoString) return "Never";
        try {
            return new Date(isoString).toLocaleString();
        } catch {
            return isoString;
        }
    };

    const toggleSource = (source: string) => {
        setExpandedSources(prev => {
            const next = new Set(prev);
            if (next.has(source)) {
                next.delete(source);
            } else {
                next.add(source);
            }
            return next;
        });
    };

    const logoMap: Record<string, string> = {
        nginx: "/packages/nginx.svg",
        mysql: "/packages/mysql.svg",
        php: "/packages/php.svg",
        python: "/packages/python.svg",
        mariadb: "/packages/MariaDB.svg",
        redis: "/packages/redis.svg",
        postgresql: "/packages/postgresql.svg",
        httpd: "/packages/httpd.svg",
        openssl: "/packages/openssl.svg",
        curl: "/packages/curl.svg",
        memcached: "/packages/memcached.svg",
        pip: "/packages/pip.svg",
        imagemagick: "/packages/ImageMagick.svg",
        phpmyadmin: "/packages/PhpMyAdmin.svg",
        openresty: "/packages/openresty.svg",
        "pure-ftpd": "/packages/Pure-ftpd.webp",
        fail2ban: "/packages/fail2ban.webp",
        htop: "/packages/htop.svg",
        php_patches: "/packages/php.svg",
        php_plugins: "/packages/php.svg",
        misc_github: "/github.webp",
    };

    const sourceNames: Record<string, string> = {
        nginx: "Nginx",
        mysql: "MySQL",
        php: "PHP",
        python: "Python",
        mariadb: "MariaDB",
        redis: "Redis",
        postgresql: "PostgreSQL",
        httpd: "Apache HTTPD",
        apr: "APR",
        openssl: "OpenSSL",
        curl: "cURL",
        memcached: "Memcached",
        pip: "pip",
        imagemagick: "ImageMagick",
        phpmyadmin: "phpMyAdmin",
        openresty: "OpenResty",
        tengine: "Tengine",
        "pure-ftpd": "Pure-FTPd",
        fail2ban: "Fail2Ban",
        htop: "htop",
        php_patches: "PHP Patches",
        php_plugins: "PHP Plugins",
        misc_github: "GitHub Misc",
    };

    const sourceEmojis: Record<string, string> = {
        nginx: "🌐",
        mysql: "🐬",
        php: "🐘",
        python: "🐍",
        mariadb: "🗄️",
        redis: "🔴",
        postgresql: "🐘",
        httpd: "🌐",
        apr: "📦",
        openssl: "🔐",
        curl: "📡",
        memcached: "💾",
        pip: "📦",
        imagemagick: "🖼️",
        phpmyadmin: "📊",
        openresty: "🌐",
        tengine: "🌐",
    };

    const isHealthy = health?.status === "healthy";

    return (
        <main style={{
            minHeight: "100vh",
            background: colors.bg,
            padding: "2rem",
            color: colors.text,
            transition: "all 0.3s ease",
            fontFamily: "Inter, system-ui, sans-serif",
        }}>
            <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
                <header style={{ textAlign: "center", marginBottom: "2rem", position: "relative" }}>
                    {/* Theme Toggle */}
                    <button
                        onClick={toggleTheme}
                        style={{
                            position: "absolute",
                            top: 0,
                            right: 0,
                            padding: "0.5rem 0.75rem",
                            background: colors.toggleBg,
                            border: "none",
                            borderRadius: "8px",
                            cursor: "pointer",
                            fontSize: "1rem",
                            color: colors.text,
                            transition: "background 0.2s",
                        }}
                        title={`Current: ${theme} mode`}
                    >
                        {theme === "system" ? "🌗" : theme === "light" ? "☀️" : "🌙"}
                    </button>

                    <div style={{ display: "flex", justifyContent: "center", marginBottom: "0.5rem" }}>
                        <img
                            src={effectiveTheme === "light" ? "/OneMirror-Light.webp" : "/OneMirror-Dark.webp"}
                            alt="MirrorinOne"
                            style={{ height: "80px", width: "auto" }}
                        />
                    </div>
                    <p style={{ color: colors.textMuted }}>
                        Your trusted mirror for your Linux web development essentials
                    </p>
                </header>

                {/* Status Section */}
                <div style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "1rem",
                    marginBottom: "2rem",
                }}>
                    {/* System Status */}
                    <div style={{
                        background: isHealthy ? colors.successBg : colors.errorBg,
                        border: `1px solid ${isHealthy ? colors.successBorder : colors.errorBorder}`,
                        borderRadius: "12px",
                        padding: "1rem",
                        textAlign: "center",
                    }}>
                        <div style={{ fontSize: "2rem" }}>{loading ? "⏳" : isHealthy ? "✅" : "❌"}</div>
                        <div style={{ fontSize: "0.875rem", color: colors.textMuted }}>System</div>
                        <div style={{ fontWeight: 600, color: isHealthy ? colors.successText : colors.errorText }}>
                            {loading ? "Loading..." : isHealthy ? "Healthy" : "Unhealthy"}
                        </div>
                    </div>

                    {/* Mirror Type */}
                    <div style={{
                        background: health?.mirror_type === "cache" ? colors.successBg : colors.blueBg,
                        border: `1px solid ${health?.mirror_type === "cache" ? colors.successBorder : colors.blueBorder}`,
                        borderRadius: "12px",
                        padding: "1rem",
                        textAlign: "center",
                    }}>
                        <div style={{ fontSize: "2rem" }}>
                            {health?.mirror_type === "cache" ? "💾" : "🔗"}
                        </div>
                        <div style={{ fontSize: "0.875rem", color: colors.textMuted }}>Mode</div>
                        <div style={{
                            fontWeight: 600,
                            color: health?.mirror_type === "cache" ? colors.successText : colors.blueText,
                            textTransform: "capitalize",
                        }}>
                            {health?.mirror_type || "redirect"}
                        </div>
                    </div>

                    {/* Last Scrape */}
                    <div style={{
                        background: colors.cardBg,
                        border: `1px solid ${colors.cardBorder}`,
                        borderRadius: "12px",
                        padding: "1rem",
                        textAlign: "center",
                        boxShadow: effectiveTheme === "light" ? "0 2px 4px rgba(0,0,0,0.05)" : "none",
                    }}>
                        <div style={{ fontSize: "2rem" }}>⏱️</div>
                        <div style={{ fontSize: "0.875rem", color: colors.textMuted }}>Last Scrape</div>
                        <div style={{ fontWeight: 600, fontSize: "0.8rem", color: colors.text }}>
                            {formatTime(health?.last_scrape || null)}
                        </div>
                    </div>

                    {/* Last Success */}
                    <div style={{
                        background: colors.cardBg,
                        border: `1px solid ${colors.cardBorder}`,
                        borderRadius: "12px",
                        padding: "1rem",
                        textAlign: "center",
                        boxShadow: effectiveTheme === "light" ? "0 2px 4px rgba(0,0,0,0.05)" : "none",
                    }}>
                        <div style={{ fontSize: "2rem" }}>✅</div>
                        <div style={{ fontSize: "0.875rem", color: colors.textMuted }}>Last Success</div>
                        <div style={{ fontWeight: 600, fontSize: "0.8rem", color: colors.successText }}>
                            {formatTime(health?.last_success || null)}
                        </div>
                    </div>

                    {/* Total Resources */}
                    <div style={{
                        background: colors.cardBg,
                        border: `1px solid ${colors.cardBorder}`,
                        borderRadius: "12px",
                        padding: "1rem",
                        textAlign: "center",
                        boxShadow: effectiveTheme === "light" ? "0 2px 4px rgba(0,0,0,0.05)" : "none",
                    }}>
                        <div style={{ fontSize: "2rem" }}>📦</div>
                        <div style={{ fontSize: "0.875rem", color: colors.textMuted }}>Total Resources</div>
                        <div style={{ fontWeight: 600, fontSize: "1.25rem", color: colors.blueText }}>
                            {resources?.total || 0}
                        </div>
                    </div>
                </div>

                {/* Quick Links */}
                <div style={{
                    display: "flex",
                    gap: "0.75rem",
                    justifyContent: "center",
                    marginBottom: "2rem",
                    flexWrap: "wrap",
                }}>
                    <a
                        href="/suggest_versions.txt"
                        style={{
                            padding: "0.5rem 1rem",
                            background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                            borderRadius: "8px",
                            color: "#fff",
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            boxShadow: "0 2px 4px rgba(99,102,241,0.3)",
                        }}
                    >
                        📄 versions.txt
                    </a>
                    <a
                        href="/latest_meta.json"
                        style={{
                            padding: "0.5rem 1rem",
                            background: colors.blueBg,
                            border: `1px solid ${colors.blueBorder}`,
                            borderRadius: "8px",
                            color: colors.blueText,
                            textDecoration: "none",
                            fontSize: "0.875rem",
                        }}
                    >
                        📋 latest_meta.json
                    </a>
                    <a
                        href="/resource.json"
                        style={{
                            padding: "0.5rem 1rem",
                            background: colors.blueBg,
                            border: `1px solid ${colors.blueBorder}`,
                            borderRadius: "8px",
                            color: colors.blueText,
                            textDecoration: "none",
                            fontSize: "0.875rem",
                        }}
                    >
                        📦 resource.json
                    </a>
                    <a
                        href="/_redirects"
                        style={{
                            padding: "0.5rem 1rem",
                            background: colors.blueBg,
                            border: `1px solid ${colors.blueBorder}`,
                            borderRadius: "8px",
                            color: colors.blueText,
                            textDecoration: "none",
                            fontSize: "0.875rem",
                        }}
                    >
                        🔗 _redirects
                    </a>
                    <a
                        href="https://github.com/dalao-org/oneinstack-mirror-generator"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                            padding: "0.5rem 1rem",
                            background: colors.buttonBg,
                            border: effectiveTheme === "light" ? "1px solid #e2e8f0" : "none",
                            borderRadius: "8px",
                            color: colors.buttonText,
                            textDecoration: "none",
                            fontSize: "0.875rem",
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                        }}
                    >
                        <img
                            src="/github.webp"
                            alt="GitHub"
                            style={{
                                height: "20px",
                                width: "auto",
                                opacity: effectiveTheme === "dark" ? 0.8 : 1
                            }}
                        />
                        GitHub Repo
                    </a>
                </div>

                {/* Usage Tip */}
                <div style={{
                    background: colors.blueBg,
                    border: `1px solid ${colors.blueBorder}`,
                    borderRadius: "8px",
                    padding: "0.75rem 1rem",
                    marginBottom: "1.5rem",
                    fontSize: "0.875rem",
                    color: colors.blueText,
                }}>
                    💡 <strong>Tip:</strong> Add <code style={{
                        background: effectiveTheme === "light" ? "rgba(0,0,0,0.05)" : "rgba(255,255,255,0.1)",
                        padding: "0.1rem 0.3rem",
                        borderRadius: "4px"
                    }}>?force_redirect=true</code> to bypass cache and redirect to the original URL, e.g. <code style={{
                        background: effectiveTheme === "light" ? "rgba(0,0,0,0.05)" : "rgba(255,255,255,0.1)",
                        padding: "0.1rem 0.3rem",
                        borderRadius: "4px"
                    }}>/src/nginx-1.27.4.tar.gz?force_redirect=true</code>
                </div>

                {/* Resources List */}
                <div>
                    <h2 style={{ marginBottom: "1rem", fontSize: "1.5rem", color: colors.heading }}>
                        📦 Mirrored Resources
                    </h2>

                    {loading ? (
                        <p style={{ color: colors.textMuted }}>Loading resources...</p>
                    ) : resources && Object.keys(resources.sources).length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                            {Object.entries(resources.sources)
                                .sort(([a], [b]) => a.localeCompare(b))
                                .map(([source, items]) => (
                                    <div
                                        key={source}
                                        style={{
                                            background: colors.cardBg,
                                            border: `1px solid ${colors.cardBorder}`,
                                            borderRadius: "12px",
                                            overflow: "hidden",
                                            boxShadow: effectiveTheme === "light" ? "0 2px 4px rgba(0,0,0,0.05)" : "none",
                                        }}
                                    >
                                        <button
                                            onClick={() => toggleSource(source)}
                                            style={{
                                                width: "100%",
                                                padding: "1rem",
                                                background: "none",
                                                border: "none",
                                                color: colors.text,
                                                cursor: "pointer",
                                                display: "flex",
                                                justifyContent: "space-between",
                                                alignItems: "center",
                                                fontSize: "1rem",
                                            }}
                                        >
                                            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                                                {logoMap[source] ? (
                                                    <img
                                                        src={logoMap[source]}
                                                        alt={source}
                                                        style={{
                                                            width: "24px",
                                                            height: "24px",
                                                            objectFit: "contain"
                                                        }}
                                                    />
                                                ) : (
                                                    <span style={{ fontSize: "1.25rem" }}>
                                                        {sourceEmojis[source] || "📦"}
                                                    </span>
                                                )}
                                                <span style={{ fontWeight: 600 }}>
                                                    {sourceNames[source] || source}
                                                </span>
                                            </div>
                                            <span style={{ color: colors.textMuted }}>
                                                {items.length} files {expandedSources.has(source) ? "▲" : "▼"}
                                            </span>
                                        </button>

                                        {expandedSources.has(source) && (
                                            <div style={{
                                                borderTop: `1px solid ${colors.itemBorder}`,
                                                padding: "0.5rem 1rem",
                                                maxHeight: "400px",
                                                overflowY: "auto",
                                            }}>
                                                {items.map((item, idx) => (
                                                    <div
                                                        key={idx}
                                                        style={{
                                                            padding: "0.5rem 0",
                                                            borderBottom: idx < items.length - 1 ? `1px solid ${colors.itemBorder}` : "none",
                                                            display: "flex",
                                                            justifyContent: "space-between",
                                                            alignItems: "center",
                                                            gap: "0.75rem",
                                                            flexWrap: "wrap",
                                                        }}
                                                    >
                                                        <div style={{
                                                            display: "flex",
                                                            alignItems: "center",
                                                            gap: "1rem",
                                                            flex: 1,
                                                            minWidth: "200px"
                                                        }}>
                                                            <span style={{
                                                                fontFamily: "'JetBrains Mono', monospace",
                                                                fontSize: "0.875rem",
                                                                color: colors.codeText,
                                                            }}>
                                                                {item.file_name}
                                                            </span>

                                                            <div style={{ display: "flex", gap: "0.5rem" }}>
                                                                <a
                                                                    href={`/src/${item.file_name}`}
                                                                    style={{
                                                                        padding: "0.25rem 0.5rem",
                                                                        background: colors.successBg,
                                                                        border: `1px solid ${colors.successBorder}`,
                                                                        borderRadius: "4px",
                                                                        color: colors.successText,
                                                                        textDecoration: "none",
                                                                        fontSize: "0.7rem",
                                                                        whiteSpace: "nowrap",
                                                                    }}
                                                                >
                                                                    Mirror
                                                                </a>
                                                                <a
                                                                    href={item.url}
                                                                    target="_blank"
                                                                    rel="noopener noreferrer"
                                                                    style={{
                                                                        padding: "0.25rem 0.5rem",
                                                                        background: colors.blueBg,
                                                                        border: `1px solid ${colors.blueBorder}`,
                                                                        borderRadius: "4px",
                                                                        color: colors.blueText,
                                                                        textDecoration: "none",
                                                                        fontSize: "0.7rem",
                                                                        whiteSpace: "nowrap",
                                                                    }}
                                                                >
                                                                    Source
                                                                </a>
                                                            </div>
                                                        </div>

                                                        <span style={{
                                                            color: colors.textMuted,
                                                            fontSize: "0.75rem",
                                                            whiteSpace: "nowrap",
                                                        }}>
                                                            v{item.version}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                        </div>
                    ) : (
                        <p style={{ color: colors.textMuted }}>No resources available. Run a scrape first.</p>
                    )}
                </div>

                {/* Footer */}
                <footer style={{
                    marginTop: "3rem",
                    textAlign: "center",
                    color: colors.textMuted,
                    fontSize: "0.75rem",
                }}>
                    Version {health?.version || "2.0.0"} • Powered by <a href="https://github.com/Masterain98" target="_blank" rel="noopener noreferrer" style={{ color: "inherit", textDecoration: "underline" }}>Masterain</a>
                </footer>
            </div>
        </main>
    );
}
