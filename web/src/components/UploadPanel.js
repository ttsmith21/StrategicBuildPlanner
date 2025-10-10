import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useRef, useState } from "react";
export function UploadPanel({ meta, onMetaChange, onUpload, uploading, sessionId, uploadedFiles, }) {
    const fileInputRef = useRef(null);
    const [localError, setLocalError] = useState(null);
    const handleInputChange = (event, field) => {
        onMetaChange({ [field]: event.target.value });
    };
    const handleSubmit = async (event) => {
        event.preventDefault();
        const files = fileInputRef.current?.files;
        if (!files || files.length === 0) {
            setLocalError("Please select one or more files to ingest.");
            return;
        }
        setLocalError(null);
        await onUpload(files);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };
    return (_jsxs("div", { className: "panel", children: [_jsx("h2", { children: "Upload & Session" }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("fieldset", { children: [_jsx("label", { htmlFor: "projectName", children: "Project / Part Family" }), _jsx("input", { id: "projectName", name: "projectName", type: "text", placeholder: "ACME Bracket Demo", value: meta.projectName, onChange: (event) => handleInputChange(event, "projectName"), required: true })] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "customer", children: "Customer" }), _jsx("input", { id: "customer", name: "customer", type: "text", placeholder: "Northern Manufacturing", value: meta.customer, onChange: (event) => handleInputChange(event, "customer") })] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "family", children: "Family" }), _jsx("input", { id: "family", name: "family", type: "text", placeholder: "Bracket Assemblies", value: meta.family, onChange: (event) => handleInputChange(event, "family") })] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "ingest-files", children: "Source Documents" }), _jsx("input", { id: "ingest-files", ref: fileInputRef, type: "file", multiple: true, accept: ".pdf,.txt,.docx,.md,.json" })] }), localError && _jsx("div", { className: "error-banner", children: localError }), _jsx("button", { type: "submit", disabled: uploading, children: uploading ? "Uploading…" : "Upload & Create Session" })] }), _jsxs("section", { children: [_jsxs("div", { className: "status-line", children: ["Session: ", sessionId ? sessionId : "—"] }), _jsx("div", { className: "listing", style: { marginTop: "0.75rem" }, children: uploadedFiles.length === 0 ? (_jsx("span", { className: "small", children: "No files ingested yet." })) : (uploadedFiles.map((file) => (_jsxs("div", { className: "badge", children: ["\uD83D\uDCC4 ", file] }, file)))) })] })] }));
}
