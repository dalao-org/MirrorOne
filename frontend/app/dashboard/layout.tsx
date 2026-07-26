import type { Metadata } from "next";
import { AdminShell } from "@/app/_components/AdminShell";

export const metadata: Metadata = {
    title: "Dashboard – MirrorOne Admin",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return <AdminShell>{children}</AdminShell>;
}
