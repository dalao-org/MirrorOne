"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "@/app/_components/ui.module.css";
import { outfit, jetbrainsMono } from "@/app/_components/fonts";
import { LockIcon, UserIcon, ArrowLeftIcon, AlertTriangleIcon } from "@/app/_components/Icons";

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await fetch("/api/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Login failed");
            }

            const data = await response.json();

            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("token_expires_at", data.expires_at);

            router.push("/dashboard");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={`${styles.root} ${outfit.variable} ${jetbrainsMono.variable}`}>
            <main
                style={{
                    minHeight: "100dvh",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "1.5rem",
                    background:
                        "radial-gradient(circle at 20% 20%, color-mix(in srgb, var(--admin-accent) 6%, transparent), transparent 45%), var(--admin-bg)",
                }}
            >
                <div style={{ width: "100%", maxWidth: "380px" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "1.75rem" }}>
                        <span className={styles.brandMark} style={{ width: "40px", height: "40px", fontSize: "1rem", marginBottom: "0.875rem" }}>
                            M1
                        </span>
                        <h1 style={{ fontSize: "1.25rem", fontWeight: 600, letterSpacing: "-0.01em", margin: 0 }}>
                            MirrorOne Admin
                        </h1>
                        <p style={{ color: "var(--admin-text-muted)", fontSize: "0.875rem", marginTop: "0.375rem" }}>
                            Sign in to manage scrapers and settings
                        </p>
                    </div>

                    <div className={`${styles.card} ${styles.cardPad}`}>
                        <form onSubmit={handleSubmit} className={styles.stack} style={{ gap: "1.125rem" }}>
                            {error && (
                                <div className={`${styles.alert} ${styles.alertDanger}`} style={{ marginBottom: 0 }}>
                                    <span style={{ flexShrink: 0, marginTop: "0.0625rem" }}><AlertTriangleIcon size={15} /></span>
                                    <span>{error}</span>
                                </div>
                            )}

                            <div className={styles.field}>
                                <label className={styles.label} htmlFor="username">Username</label>
                                <div style={{ position: "relative" }}>
                                    <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--admin-text-faint)", display: "flex" }}>
                                        <UserIcon size={15} />
                                    </span>
                                    <input
                                        id="username"
                                        type="text"
                                        className={styles.input}
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        style={{ paddingLeft: "2.25rem" }}
                                        autoComplete="username"
                                        required
                                    />
                                </div>
                            </div>

                            <div className={styles.field}>
                                <label className={styles.label} htmlFor="password">Password</label>
                                <div style={{ position: "relative" }}>
                                    <span style={{ position: "absolute", left: "0.75rem", top: "50%", transform: "translateY(-50%)", color: "var(--admin-text-faint)", display: "flex" }}>
                                        <LockIcon size={15} />
                                    </span>
                                    <input
                                        id="password"
                                        type="password"
                                        className={styles.input}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        style={{ paddingLeft: "2.25rem" }}
                                        autoComplete="current-password"
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                className={`${styles.btn} ${styles.btnPrimary} ${styles.btnBlock}`}
                                disabled={loading}
                                style={{ padding: "0.625rem" }}
                            >
                                {loading && <span className={styles.spinner} />}
                                {loading ? "Signing in…" : "Sign in"}
                            </button>
                        </form>
                    </div>

                    <p style={{ textAlign: "center", marginTop: "1.5rem" }}>
                        <a
                            href="/"
                            className={styles.link}
                            style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem", fontSize: "0.8125rem", color: "var(--admin-text-muted)" }}
                        >
                            <ArrowLeftIcon size={13} />
                            Back to home
                        </a>
                    </p>
                </div>
            </main>
        </div>
    );
}
