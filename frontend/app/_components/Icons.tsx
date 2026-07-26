import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base(props: IconProps) {
    const { size = 18, ...rest } = props;
    return {
        width: size,
        height: size,
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: 1.75,
        strokeLinecap: "round" as const,
        strokeLinejoin: "round" as const,
        ...rest,
    };
}

export function GaugeIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M12 14 15.5 9.5" />
            <path d="M3.5 14a8.5 7 0 0 1 17 0" />
            <path d="M3.5 14h17" />
        </svg>
    );
}

export function BoxIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M12 3 20.5 7.5v9L12 21 3.5 16.5v-9Z" />
            <path d="M3.5 7.5 12 12l8.5-4.5" />
            <path d="M12 12v9" />
        </svg>
    );
}

export function ListIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M8 6h13" />
            <path d="M8 12h13" />
            <path d="M8 18h13" />
            <path d="M3 6h.01" />
            <path d="M3 12h.01" />
            <path d="M3 18h.01" />
        </svg>
    );
}

export function GearIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
        </svg>
    );
}

export function LogoutIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="M16 17 21 12 16 7" />
            <path d="M21 12H9" />
        </svg>
    );
}

export function PlayIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M7 4.5v15l13-7.5Z" />
        </svg>
    );
}

export function ClockIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3.2 2" />
        </svg>
    );
}

export function TerminalIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="m5 7 5 5-5 5" />
            <path d="M12 17h7" />
        </svg>
    );
}

export function SearchIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
        </svg>
    );
}

export function ExternalLinkIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <path d="M15 3h6v6" />
            <path d="M10 14 21 3" />
        </svg>
    );
}

export function CheckIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="m4 12 6 6L20 6" />
        </svg>
    );
}

export function XIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M18 6 6 18" />
            <path d="M6 6l12 12" />
        </svg>
    );
}

export function PlusIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M12 5v14" />
            <path d="M5 12h14" />
        </svg>
    );
}

export function AlertTriangleIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
            <path d="M12 9v4" />
            <path d="M12 17h.01" />
        </svg>
    );
}

export function DownloadIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M12 3v12" />
            <path d="m7 10 5 5 5-5" />
            <path d="M5 21h14" />
        </svg>
    );
}

export function LockIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <rect x="4" y="10.5" width="16" height="10" rx="2" />
            <path d="M8 10.5V7a4 4 0 0 1 8 0v3.5" />
        </svg>
    );
}

export function UserIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <circle cx="12" cy="8" r="3.5" />
            <path d="M4.5 20a7.5 6 0 0 1 15 0" />
        </svg>
    );
}

export function ArrowLeftIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M19 12H5" />
            <path d="m12 19-7-7 7-7" />
        </svg>
    );
}

export function InboxIcon(props: IconProps) {
    return (
        <svg {...base(props)}>
            <path d="M22 12h-6l-2 3h-4l-2-3H2" />
            <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" />
        </svg>
    );
}
