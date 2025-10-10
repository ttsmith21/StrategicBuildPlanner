import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from "react";
export function ToastContainer({ toasts, onDismiss }) {
    useEffect(() => {
        if (toasts.length === 0) {
            return;
        }
        const timers = toasts.map((toast) => window.setTimeout(() => {
            onDismiss(toast.id);
        }, 4000));
        return () => {
            timers.forEach((timer) => window.clearTimeout(timer));
        };
    }, [toasts, onDismiss]);
    if (toasts.length === 0) {
        return null;
    }
    return (_jsx("div", { className: "toast-container", children: toasts.map((toast) => (_jsxs("div", { className: `toast ${toast.type}`, children: [_jsx("span", { children: toast.message }), _jsx("button", { type: "button", onClick: () => onDismiss(toast.id), children: "\u00D7" })] }, toast.id))) }));
}
