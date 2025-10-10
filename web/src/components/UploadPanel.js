import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
function useDebouncedValue(value, delay = 300) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const handle = window.setTimeout(() => setDebounced(value), delay);
        return () => window.clearTimeout(handle);
    }, [value, delay]);
    return debounced;
}
export function UploadPanel({ meta, onMetaChange, onUpload, uploading, sessionId, uploadedFiles, selectedCustomer, selectedFamily, recentCustomers, recentFamilies, onCustomerSelected, onFamilySelected, onFamilyUrlPaste, }) {
    const fileInputRef = useRef(null);
    const [localError, setLocalError] = useState(null);
    const [customerFocused, setCustomerFocused] = useState(false);
    const [familyFocused, setFamilyFocused] = useState(false);
    const [customerQuery, setCustomerQuery] = useState(meta.customer);
    const [familyQuery, setFamilyQuery] = useState(meta.family);
    const debouncedCustomer = useDebouncedValue(customerQuery);
    const debouncedFamily = useDebouncedValue(familyQuery);
    useEffect(() => {
        setCustomerQuery(meta.customer);
    }, [meta.customer]);
    useEffect(() => {
        setFamilyQuery(meta.family);
    }, [meta.family]);
    const handleInputChange = (event, field) => {
        onMetaChange({ [field]: event.target.value });
        if (field === "customer") {
            setCustomerQuery(event.target.value);
            if (selectedCustomer && selectedCustomer.title !== event.target.value) {
                onCustomerSelected(null);
            }
        }
        if (field === "family") {
            setFamilyQuery(event.target.value);
            if (selectedFamily && selectedFamily.title !== event.target.value) {
                onFamilySelected(null);
            }
        }
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
    const { data: customerResults } = useQuery({
        queryKey: ["confluence-customers", debouncedCustomer],
        queryFn: async () => {
            if (!debouncedCustomer) {
                return recentCustomers;
            }
            const { data } = await api.get("/confluence/customers", {
                params: { q: debouncedCustomer },
            });
            return data.length > 0 ? data : recentCustomers;
        },
        enabled: debouncedCustomer.trim().length > 1,
        initialData: recentCustomers,
    });
    const { data: familyResults } = useQuery({
        queryKey: ["confluence-families", debouncedFamily],
        queryFn: async () => {
            if (!debouncedFamily) {
                return recentFamilies;
            }
            const { data } = await api.get("/confluence/families", {
                params: { q: debouncedFamily },
            });
            return data.length > 0 ? data : recentFamilies;
        },
        enabled: debouncedFamily.trim().length > 1,
        initialData: recentFamilies,
    });
    const handleChooseCustomer = (page) => {
        onCustomerSelected(page);
        onMetaChange({ customer: page.title, customerPage: page });
        setCustomerFocused(false);
    };
    const handleChooseFamily = (page) => {
        onFamilySelected(page);
        onMetaChange({ family: page.title, familyPage: page });
        setFamilyFocused(false);
    };
    const handlePasteFamilyUrl = async () => {
        const url = window.prompt("Paste Confluence family page URL");
        if (!url) {
            return;
        }
        await onFamilyUrlPaste(url);
    };
    const customerOptions = customerResults ?? [];
    const familyOptions = familyResults ?? [];
    return (_jsxs("div", { className: "panel", children: [_jsx("h2", { children: "Upload & Session" }), _jsxs("form", { onSubmit: handleSubmit, children: [_jsxs("fieldset", { children: [_jsx("label", { htmlFor: "projectName", children: "Project / Part Family" }), _jsx("input", { id: "projectName", name: "projectName", type: "text", placeholder: "ACME Bracket Demo", value: meta.projectName, onChange: (event) => handleInputChange(event, "projectName"), required: true })] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "customer", children: "Customer" }), _jsx("input", { id: "customer", name: "customer", type: "text", placeholder: "Northern Manufacturing", value: meta.customer, onFocus: () => setCustomerFocused(true), onBlur: () => setTimeout(() => setCustomerFocused(false), 150), onChange: (event) => handleInputChange(event, "customer") }), customerFocused && customerOptions.length > 0 && (_jsx("div", { className: "autocomplete-menu", children: customerOptions.map((option) => (_jsx("button", { type: "button", className: "autocomplete-item", onMouseDown: (event) => event.preventDefault(), onClick: () => handleChooseCustomer(option), children: _jsx("span", { children: option.title }) }, option.id))) })), customerFocused && customerOptions.length === 0 && debouncedCustomer.trim().length > 1 && (_jsx("div", { className: "autocomplete-empty", children: "Can't find it? Try a different keyword." })), selectedCustomer && (_jsxs("div", { className: "badge", style: { marginTop: "0.35rem" }, children: ["Customer page: ", selectedCustomer.title] }))] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "family", children: "Family" }), _jsx("input", { id: "family", name: "family", type: "text", placeholder: "Bracket Assemblies", value: meta.family, onFocus: () => setFamilyFocused(true), onBlur: () => setTimeout(() => setFamilyFocused(false), 150), onChange: (event) => handleInputChange(event, "family") }), familyFocused && familyOptions.length > 0 && (_jsx("div", { className: "autocomplete-menu", children: familyOptions.map((option) => (_jsx("button", { type: "button", className: "autocomplete-item", onMouseDown: (event) => event.preventDefault(), onClick: () => handleChooseFamily(option), children: _jsx("span", { children: option.title }) }, option.id))) })), familyFocused && familyOptions.length === 0 && debouncedFamily.trim().length > 1 && (_jsxs("div", { className: "autocomplete-empty", children: ["Can't find it? ", _jsx("button", { type: "button", className: "link-button", onClick: handlePasteFamilyUrl, children: "Paste the Confluence page URL" })] })), !familyFocused && (_jsx("button", { type: "button", className: "link-button", style: { marginTop: "0.35rem" }, onClick: handlePasteFamilyUrl, children: "Paste Confluence URL" })), selectedFamily && (_jsxs("div", { className: "badge", style: { marginTop: "0.35rem" }, children: ["Selected parent: ", selectedFamily.title, selectedFamily.url && (_jsx("button", { type: "button", className: "link-button", style: { marginLeft: "0.5rem" }, onClick: () => window.open(selectedFamily.url, "_blank", "noopener"), children: "Open \u2197" }))] }))] }), _jsxs("fieldset", { children: [_jsx("label", { htmlFor: "ingest-files", children: "Source Documents" }), _jsx("input", { id: "ingest-files", ref: fileInputRef, type: "file", multiple: true, accept: ".pdf,.txt,.docx,.md,.json" })] }), localError && _jsx("div", { className: "error-banner", children: localError }), _jsx("button", { type: "submit", disabled: uploading, children: uploading ? "Uploading…" : "Upload & Create Session" })] }), _jsxs("section", { children: [_jsxs("div", { className: "status-line", children: ["Session: ", sessionId ? sessionId : "—"] }), _jsx("div", { className: "listing", style: { marginTop: "0.75rem" }, children: uploadedFiles.length === 0 ? (_jsx("span", { className: "small", children: "No files ingested yet." })) : (uploadedFiles.map((file) => (_jsxs("div", { className: "badge", children: ["\uD83D\uDCC4 ", file] }, file)))) })] })] }));
}
