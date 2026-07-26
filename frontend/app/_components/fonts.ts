import { Outfit, JetBrains_Mono } from "next/font/google";

// Scoped via CSS variables on a wrapper element inside admin routes only —
// never applied at the root <html>/<body> so the public site's typography
// is untouched.
export const outfit = Outfit({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700"],
    variable: "--font-admin-sans",
    display: "swap",
});

export const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    weight: ["400", "500", "600"],
    variable: "--font-admin-mono",
    display: "swap",
});
