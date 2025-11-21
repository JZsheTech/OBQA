import { createContext, useCallback, useContext, useMemo, useState } from "react"

const ToastContext = createContext(null)
let counter = 0

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([])

    const removeToast = useCallback((id) => {
        setToasts((current) => current.filter((toast) => toast.id !== id))
    }, [])

    const addToast = useCallback(
        ({ title, message, type = "info", duration = 3600 }) => {
            const id = ++counter
            setToasts((current) => [...current, { id, title, message, type }])
            window.setTimeout(() => removeToast(id), duration)
            return id
        },
        [removeToast],
    )

    const value = useMemo(() => ({ addToast }), [addToast])

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="toast-container" role="status" aria-live="polite">
                {toasts.map((toast) => (
                    <div key={toast.id} className={`toast ${toast.type}`}>
                        <span
                            className="status-dot"
                            style={{
                                background:
                                    toast.type === "error"
                                        ? "var(--color-danger)"
                                        : toast.type === "success"
                                        ? "var(--color-success)"
                                        : "var(--color-brand)",
                            }}
                        ></span>
                        <div>
                            <div className="label">{toast.title ?? "提示"}</div>
                            {toast.message && <div className="caption">{toast.message}</div>}
                        </div>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    )
}

export function useToast() {
    const context = useContext(ToastContext)
    if (!context) {
        throw new Error("useToast must be used within ToastProvider")
    }
    return context
}
