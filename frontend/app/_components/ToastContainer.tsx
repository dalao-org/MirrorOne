"use client";

import styles from "./ui.module.css";
import { CheckIcon, XIcon, AlertTriangleIcon } from "./Icons";
import type { ToastItem } from "./useToast";

export function ToastContainer({
    toasts,
    onDismiss,
}: {
    toasts: ToastItem[];
    onDismiss: (id: number) => void;
}) {
    if (toasts.length === 0) return null;

    return (
        <div className={styles.toastContainer}>
            {toasts.map((toast) => (
                <div
                    key={toast.id}
                    className={`${styles.toast} ${toast.type === "success" ? styles.toastSuccess : styles.toastError}`}
                >
                    <span className={styles.toastIcon}>
                        {toast.type === "success" ? <CheckIcon size={16} /> : <AlertTriangleIcon size={16} />}
                    </span>
                    <span className={styles.grow}>{toast.message}</span>
                    <button
                        type="button"
                        onClick={() => onDismiss(toast.id)}
                        className={`${styles.btn} ${styles.btnGhost}`}
                        style={{ padding: "0.125rem", borderRadius: "999px" }}
                        aria-label="Dismiss notification"
                    >
                        <XIcon size={14} />
                    </button>
                </div>
            ))}
        </div>
    );
}
