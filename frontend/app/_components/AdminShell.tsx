"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import styles from "./ui.module.css";
import { outfit, jetbrainsMono } from "./fonts";
import { GaugeIcon, BoxIcon, ListIcon, GearIcon, LogoutIcon } from "./Icons";

const NAV_ITEMS = [
    { href: "/dashboard", label: "Overview", icon: GaugeIcon, exact: true },
    { href: "/dashboard/resources", label: "Resources", icon: BoxIcon, exact: false },
    { href: "/dashboard/logs", label: "Logs", icon: ListIcon, exact: false },
    { href: "/dashboard/settings", label: "Settings", icon: GearIcon, exact: false },
];

export function AdminShell({ children }: { children: ReactNode }) {
    const pathname = usePathname();
    const router = useRouter();

    const isActive = (href: string, exact: boolean) => (exact ? pathname === href : pathname.startsWith(href));
    const current = NAV_ITEMS.find((item) => isActive(item.href, item.exact));

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("token_expires_at");
        router.push("/login");
    };

    return (
        <div className={`${styles.root} ${outfit.variable} ${jetbrainsMono.variable}`}>
            <div className={styles.shell}>
                <aside className={styles.sidebar}>
                    <div className={styles.brand}>
                        <span className={styles.brandMark}>M1</span>
                        <span className={styles.brandText}>
                            <span className={styles.brandTitle}>MirrorOne</span>
                            <span className={styles.brandSubtitle}>Admin console</span>
                        </span>
                    </div>
                    <nav className={styles.nav}>
                        {NAV_ITEMS.map((item) => {
                            const active = isActive(item.href, item.exact);
                            const Icon = item.icon;
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
                                >
                                    <span className={styles.navIcon}>
                                        <Icon size={17} />
                                    </span>
                                    {item.label}
                                </Link>
                            );
                        })}
                    </nav>
                </aside>
                <div style={{ minWidth: 0, display: "flex", flexDirection: "column" }}>
                    <header className={styles.topbar}>
                        <div className={styles.topbarTitleGroup}>
                            <h1 className={styles.topbarTitle}>{current?.label ?? "Dashboard"}</h1>
                        </div>
                        <div className={styles.topbarActions}>
                            <button
                                type="button"
                                onClick={handleLogout}
                                className={`${styles.btn} ${styles.btnGhost} ${styles.btnSm}`}
                            >
                                <LogoutIcon size={15} />
                                Log out
                            </button>
                        </div>
                    </header>
                    <main className={styles.content}>{children}</main>
                </div>
            </div>
        </div>
    );
}
