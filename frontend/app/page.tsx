import Link from "next/link";

export default function Home() {
    return (
        <main className="container" style={{ textAlign: "center", paddingTop: "4rem" }}>
            <h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>
                Oneinstack Mirror Generator
            </h1>
            <p style={{ fontSize: "1.25rem", color: "#888", marginBottom: "2rem" }}>
                Trusted mirror for OneinStack software packages
            </p>

            <div className="card" style={{ maxWidth: "600px", margin: "0 auto" }}>
                <h2 style={{ marginBottom: "1rem" }}>🚀 Version 2.0</h2>
                <p style={{ marginBottom: "1.5rem", color: "#aaa" }}>
                    This mirror provides automatic redirect rules for downloading software packages
                    from their official sources.
                </p>

                <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
                    <Link href="/login" className="btn btn-primary">
                        Admin Login
                    </Link>
                    <a
                        href="/suggest_versions.txt"
                        className="btn"
                        style={{ background: "#333", color: "#fff" }}
                    >
                        View Versions
                    </a>
                </div>
            </div>

            <div style={{ marginTop: "3rem" }}>
                <h3 style={{ marginBottom: "1rem" }}>Quick Links</h3>
                <div style={{ display: "flex", gap: "2rem", justifyContent: "center", flexWrap: "wrap" }}>
                    <a href="/health" style={{ color: "#888" }}>Health Check</a>
                    <a href="https://github.com/dalao-org/oneinstack-mirror-generator" style={{ color: "#888" }}>
                        GitHub Repository
                    </a>
                </div>
            </div>
        </main>
    );
}
