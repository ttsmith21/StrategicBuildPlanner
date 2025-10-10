import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "./api";
import { UploadPanel } from "./components/UploadPanel";
import { PlanPreview } from "./components/PlanPreview";
import { ChatPanel } from "./components/ChatPanel";
const now = () => new Date().toISOString();
const makeId = () => (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
export default function App() {
    const [meta, setMeta] = useState({ projectName: "", customer: "", family: "" });
    const [sessionId, setSessionId] = useState(null);
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [planJson, setPlanJson] = useState(null);
    const [planMarkdown, setPlanMarkdown] = useState("");
    const [vectorStoreId, setVectorStoreId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [error, setError] = useState(null);
    const [publishResult, setPublishResult] = useState(null);
    const [qaResult, setQaResult] = useState(null);
    const [asanaTasks, setAsanaTasks] = useState([]);
    const [confluenceParentId, setConfluenceParentId] = useState("");
    const [asanaProjectId, setAsanaProjectId] = useState("");
    const [statusMessage, setStatusMessage] = useState(null);
    const [isBusy, setIsBusy] = useState(false);
    const resetForNewPlan = () => {
        setPlanJson(null);
        setPlanMarkdown("");
        setVectorStoreId(null);
        setPublishResult(null);
        setQaResult(null);
        setAsanaTasks([]);
        setMessages([]);
        setStatusMessage(null);
    };
    const ingestMutation = useMutation({
        mutationFn: async (files) => {
            if (!meta.projectName.trim()) {
                throw new Error("Project name is required before drafting.");
            }
            const formData = new FormData();
            Array.from(files).forEach((file) => {
                formData.append("files", file);
            });
            if (meta.customer) {
                formData.append("customer", meta.customer);
            }
            if (meta.family) {
                formData.append("family", meta.family);
            }
            const { data } = await api.post("/ingest", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            return data;
        },
        onSuccess: (data) => {
            setSessionId(data.session_id);
            setUploadedFiles(data.file_names);
            resetForNewPlan();
            setStatusMessage(data.message);
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "Failed to ingest files.");
        },
    });
    const draftMutation = useMutation({
        mutationFn: async () => {
            if (!sessionId) {
                throw new Error("Upload documents first to create a session.");
            }
            const { data } = await api.post("/draft", {
                session_id: sessionId,
                project_name: meta.projectName,
                customer: meta.customer || undefined,
                family: meta.family || undefined,
            });
            return data;
        },
        onSuccess: (data) => {
            setPlanJson(data.plan_json);
            setPlanMarkdown(data.plan_markdown);
            setVectorStoreId(data.vector_store_id);
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: "Draft completed — review the plan preview for Markdown and JSON outputs.",
                    timestamp: now(),
                },
            ]);
            setStatusMessage(`Drafted plan from ${uploadedFiles.length} source file(s).`);
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "Draft failed.");
        },
    });
    const meetingApplyMutation = useMutation({
        mutationFn: async (transcript) => {
            if (!planJson) {
                throw new Error("Draft a plan before applying meeting notes.");
            }
            const { data } = await api.post("/meeting/apply", {
                plan_json: planJson,
                transcript_texts: [transcript],
            });
            return data;
        },
        onSuccess: (data, transcript) => {
            setPlanJson(data.updated_plan_json);
            setPlanMarkdown(data.updated_plan_markdown);
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "user",
                    content: transcript,
                    timestamp: now(),
                },
                {
                    id: makeId(),
                    role: "assistant",
                    content: data.changes_summary,
                    timestamp: now(),
                },
            ]);
            setStatusMessage("Meeting notes applied.");
            setChatInput("");
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "Failed to apply meeting notes.");
        },
    });
    const publishMutation = useMutation({
        mutationFn: async () => {
            if (!planJson || !planMarkdown) {
                throw new Error("Draft the plan before publishing.");
            }
            const { data } = await api.post("/publish", {
                customer: planJson["customer"] ?? meta.customer,
                family: meta.family || planJson["project"],
                project: meta.projectName || planJson["project"],
                markdown: planMarkdown,
                parent_page_id: confluenceParentId || undefined,
            });
            return data;
        },
        onSuccess: (data) => {
            setPublishResult(data);
            setStatusMessage(`Published to Confluence page ${data.title}.`);
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: `Published to Confluence: ${data.url}`,
                    timestamp: now(),
                },
            ]);
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "Publish failed.");
        },
    });
    const qaMutation = useMutation({
        mutationFn: async () => {
            if (!planJson) {
                throw new Error("Draft the plan before running QA.");
            }
            const { data } = await api.post("/qa/grade", {
                plan_json: planJson,
            });
            return data;
        },
        onSuccess: (data) => {
            setQaResult(data);
            setStatusMessage("QA grade completed.");
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: `QA Overall Score: ${data.overall_score.toFixed(1)} / 100`,
                    timestamp: now(),
                },
            ]);
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "QA grading failed.");
        },
    });
    const asanaMutation = useMutation({
        mutationFn: async () => {
            if (!planJson) {
                throw new Error("Draft the plan before creating tasks.");
            }
            if (!asanaProjectId.trim()) {
                throw new Error("Provide an Asana project ID.");
            }
            const { data } = await api.post("/asana/tasks", {
                project_id: asanaProjectId,
                plan_json: planJson,
            });
            return data;
        },
        onSuccess: (data) => {
            setAsanaTasks(data.created);
            setStatusMessage(`Created ${data.created.length} Asana task(s).`);
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: `Created ${data.created.length} Asana task(s).`,
                    timestamp: now(),
                },
            ]);
            setError(null);
        },
        onError: (err) => {
            setError(err.message || "Failed to create Asana tasks.");
        },
    });
    const isLoadingAny = useMemo(() => ingestMutation.isPending ||
        draftMutation.isPending ||
        meetingApplyMutation.isPending ||
        publishMutation.isPending ||
        qaMutation.isPending ||
        asanaMutation.isPending, [
        ingestMutation.isPending,
        draftMutation.isPending,
        meetingApplyMutation.isPending,
        publishMutation.isPending,
        qaMutation.isPending,
        asanaMutation.isPending,
    ]);
    useEffect(() => {
        setIsBusy(isLoadingAny);
    }, [isLoadingAny]);
    const handleUpload = async (files) => {
        setStatusMessage(null);
        await ingestMutation.mutateAsync(files);
    };
    const handleDraft = async () => {
        setStatusMessage(null);
        await draftMutation.mutateAsync();
    };
    const handleSendMessage = async () => {
        if (!chatInput.trim()) {
            return;
        }
        setStatusMessage(null);
        await meetingApplyMutation.mutateAsync(chatInput.trim());
    };
    const handlePublish = async () => {
        setStatusMessage(null);
        await publishMutation.mutateAsync();
    };
    const handleQa = async () => {
        setStatusMessage(null);
        await qaMutation.mutateAsync();
    };
    const handleAsana = async () => {
        setStatusMessage(null);
        await asanaMutation.mutateAsync();
    };
    const handleBrowse = () => {
        if (publishResult?.url) {
            window.open(publishResult.url, "_blank", "noopener");
        }
    };
    const actions = [
        {
            label: "Draft",
            onClick: handleDraft,
            disabled: isBusy || !sessionId || ingestMutation.isPending,
        },
        {
            label: "Apply Meeting Notes",
            onClick: handleSendMessage,
            disabled: isBusy || !planJson || !chatInput.trim(),
        },
        {
            label: "Publish",
            onClick: handlePublish,
            disabled: isBusy || !planJson,
        },
        {
            label: "Create Asana Tasks",
            onClick: handleAsana,
            disabled: isBusy || !planJson || !asanaProjectId.trim(),
        },
        {
            label: "QA Grade",
            onClick: handleQa,
            disabled: isBusy || !planJson,
        },
        {
            label: "Browse to Page",
            onClick: handleBrowse,
            disabled: !publishResult?.url,
            variant: "secondary",
        },
    ];
    return (_jsxs("div", { className: "app-shell", children: [_jsx(UploadPanel, { meta: meta, onMetaChange: (update) => setMeta((prev) => ({ ...prev, ...update })), onUpload: handleUpload, uploading: ingestMutation.isPending, sessionId: sessionId, uploadedFiles: uploadedFiles }), _jsx(PlanPreview, { planJson: planJson, planMarkdown: planMarkdown, qaResult: qaResult, asanaTasks: asanaTasks }), _jsx(ChatPanel, { messages: messages, input: chatInput, onInputChange: setChatInput, onSend: handleSendMessage, sending: meetingApplyMutation.isPending, actions: actions, confluenceParentId: confluenceParentId, onConfluenceParentIdChange: setConfluenceParentId, asanaProjectId: asanaProjectId, onAsanaProjectIdChange: setAsanaProjectId, publishUrl: publishResult?.url, qaSummary: qaResult ? `Overall ${qaResult.overall_score.toFixed(1)} / 100` : null, asanaStatus: asanaTasks.length ? `${asanaTasks.length} task(s) created` : null, statusMessage: statusMessage, errorMessage: error, disabled: isBusy })] }));
}
