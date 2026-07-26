"use client";

import { useCallback, useRef, useState } from "react";

export type ToastType = "success" | "error";

export interface ToastItem {
    id: number;
    type: ToastType;
    message: string;
}

export function useToast() {
    const [toasts, setToasts] = useState<ToastItem[]>([]);
    const nextId = useRef(0);

    const showToast = useCallback((message: string, type: ToastType = "success") => {
        const id = ++nextId.current;
        setToasts((prev) => [...prev, { id, type, message }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 4000);
    }, []);

    const dismissToast = useCallback((id: number) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return { toasts, showToast, dismissToast };
}
