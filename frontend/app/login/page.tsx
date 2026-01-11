"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiUrl}/api/auth/login`, {
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

            // Store token in localStorage
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("token_expires_at", data.expires_at);

            // Redirect to dashboard
            router.push("/dashboard");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="container" style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
        }}>
            <div className="card" style={{ width: "100%", maxWidth: "400px" }}>
                <h1 style={{ textAlign: "center", marginBottom: "2rem" }}>Admin Login</h1>

                <form onSubmit={handleSubmit}>
                    {error && (
                        <div style={{
                            background: "#dc2626",
                            color: "white",
                            padding: "0.75rem",
                            borderRadius: "8px",
                            marginBottom: "1rem",
                        }}>
                            {error}
                        </div>
                    )}

                    <div style={{ marginBottom: "1rem" }}>
                        <label style={{ display: "block", marginBottom: "0.5rem" }}>
                            Username
                        </label>
                        <input
                            type="text"
                            className="input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>

                    <div style={{ marginBottom: "1.5rem" }}>
                        <label style={{ display: "block", marginBottom: "0.5rem" }}>
                            Password
                        </label>
                        <input
                            type="password"
                            className="input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ width: "100%" }}
                        disabled={loading}
                    >
                        {loading ? "Logging in..." : "Login"}
                    </button>
                </form>

                <p style={{ textAlign: "center", marginTop: "1.5rem", color: "#888" }}>
                    <a href="/">← Back to Home</a>
                </p>
            </div>
        </main>
    );
}
