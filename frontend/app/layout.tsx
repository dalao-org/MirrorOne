import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "Oneinstack Mirror Generator",
    description: "Mirror generator for OneinStack software packages",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
