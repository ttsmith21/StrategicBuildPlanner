import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { UploadPanel } from "./components/UploadPanel";
import { PlanPreview } from "./components/PlanPreview";
import { ChatPanel } from "./components/ChatPanel";
import { StatusBar } from "./components/StatusBar";
import { ToastContainer } from "./components/ToastContainer";
const now = () => new Date().toISOString();
const makeId = () => typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
const RECENT_CUSTOMERS_KEY = "sbp_recent_customers";
const RECENT_FAMILIES_KEY = "sbp_recent_families";
const MAX_RECENT_PAGES = 6;
const SPECIALIST_AGENT_KEYS = [
    "qma",
    "pma",
    "sca",
    "ema",
    "sbpqa",
];
const INITIAL_AGENT_STATUSES = {
    qma: "idle",
    pma: "idle",
    sca: "idle",
    ema: "idle",
    sbpqa: "idle",
};
const makeAgentStatuses = (status, overrides = {}) => {
    const base = Object.fromEntries(SPECIALIST_AGENT_KEYS.map((key) => [key, status]));
    return { ...base, ...overrides };
};
const extractConfluenceDetails = (url) => {
    try {
        const parsed = new URL(url);
        const searchPageId = parsed.searchParams.get("pageId");
        const segments = parsed.pathname.split("/").filter(Boolean);
        let pageId = searchPageId || "";
        if (!pageId) {
            const pageIndex = segments.findIndex((segment) => segment === "pages");
            if (pageIndex >= 0 && segments[pageIndex + 1]) {
                pageId = segments[pageIndex + 1];
            }
        }
        if (!pageId) {
            const match = parsed.pathname.match(/([\d]{4,})$/);
            if (match && match[1]) {
                pageId = match[1];
            }
        }
        if (!pageId) {
            return null;
        }
        let spaceKey;
        const spacesIndex = segments.findIndex((segment) => segment === "spaces");
        if (spacesIndex >= 0 && segments[spacesIndex + 1]) {
            spaceKey = decodeURIComponent(segments[spacesIndex + 1]);
        }
        const titleSegment = segments[segments.length - 1];
        const title = titleSegment ? decodeURIComponent(titleSegment.replace(/\+/g, " ")).replace(/-/g, " ") : undefined;
        return { pageId, spaceKey, title };
    }
    catch (error) {
        console.warn("Failed to parse Confluence URL", error);
        return null;
    }
};
export default function App() {
    const [meta, setMeta] = useState({
        projectName: "",
        customer: "",
        family: "",
        customerPage: null,
        familyPage: null,
    });
    const [sessionId, setSessionId] = useState(null);
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [planJson, setPlanJson] = useState(null);
    const [planMarkdown, setPlanMarkdown] = useState("");
    const [contextPack, setContextPack] = useState(null);
    const [vectorStoreId, setVectorStoreId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [error, setError] = useState(null);
    const [publishResult, setPublishResult] = useState(null);
    const [qaResult, setQaResult] = useState(null);
    const [asanaTasks, setAsanaTasks] = useState([]);
    const [suggestedTasks, setSuggestedTasks] = useState([]);
    const [planConflicts, setPlanConflicts] = useState([]);
    const [knownFingerprints, setKnownFingerprints] = useState([]);
    const [asanaSkippedCount, setAsanaSkippedCount] = useState(0);
    const [confluenceParentId, setConfluenceParentId] = useState("");
    const [selectedCustomerPage, setSelectedCustomerPage] = useState(null);
    const [selectedFamilyPage, setSelectedFamilyPage] = useState(null);
    const [recentCustomers, setRecentCustomers] = useState([]);
    const [recentFamilies, setRecentFamilies] = useState([]);
    const [selectedAsanaProject, setSelectedAsanaProject] = useState(null);
    const [manualAsanaProjectId, setManualAsanaProjectId] = useState("");
    const [statusMessage, setStatusMessage] = useState(null);
    const [isBusy, setIsBusy] = useState(false);
    const [toasts, setToasts] = useState([]);
    const [aboutOpen, setAboutOpen] = useState(false);
    const [projectNameEdited, setProjectNameEdited] = useState(false);
    const [agentStatuses, setAgentStatuses] = useState(INITIAL_AGENT_STATUSES);
    const [qaBlocked, setQaBlocked] = useState(false);
    const defaultProjectName = useMemo(() => {
        const customer = meta.customer || "Customer";
        const family = meta.family || meta.projectName || "Family";
        return `APQP — ${customer} — ${family}`;
    }, [meta.customer, meta.family, meta.projectName]);
    const [newProjectName, setNewProjectName] = useState(defaultProjectName);
    useEffect(() => {
        if (!projectNameEdited) {
            setNewProjectName(defaultProjectName);
        }
    }, [defaultProjectName, projectNameEdited]);
    const pushToast = useCallback((type, message) => {
        setToasts((prev) => [...prev, { id: makeId(), type, message }]);
    }, []);
    const dismissToast = useCallback((id) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, []);
    const healthQuery = useQuery({
        queryKey: ["healthz"],
        queryFn: async () => {
            const { data } = await api.get("/healthz");
            return data;
        },
        retry: false,
    });
    const confluenceAuthQuery = useQuery({
        queryKey: ["auth", "confluence"],
        queryFn: async () => {
            const { data } = await api.get("/auth/confluence/check");
            return data;
        },
        retry: false,
    });
    const asanaAuthQuery = useQuery({
        queryKey: ["auth", "asana"],
        queryFn: async () => {
            const { data } = await api.get("/auth/asana/check");
            return data;
        },
        retry: false,
    });
    const versionQuery = useQuery({
        queryKey: ["version"],
        queryFn: async () => {
            const { data } = await api.get("/version");
            return data;
        },
        staleTime: 60000,
    });
    const healthStatus = useMemo(() => {
        if (healthQuery.isPending) {
            return "unknown";
        }
        if (healthQuery.isError) {
            return "error";
        }
        return healthQuery.data?.status === "ok" ? "ok" : "error";
    }, [healthQuery.data?.status, healthQuery.isError, healthQuery.isPending]);
    const confluenceStatus = useMemo(() => {
        if (confluenceAuthQuery.isError) {
            return { ok: false, reason: "unreachable" };
        }
        return confluenceAuthQuery.data;
    }, [confluenceAuthQuery.data, confluenceAuthQuery.isError]);
    const asanaStatus = useMemo(() => {
        if (asanaAuthQuery.isError) {
            return { ok: false, reason: "unreachable" };
        }
        return asanaAuthQuery.data;
    }, [asanaAuthQuery.data, asanaAuthQuery.isError]);
    const handleRefreshStatuses = useCallback(() => {
        healthQuery.refetch();
        confluenceAuthQuery.refetch();
        asanaAuthQuery.refetch();
        versionQuery.refetch();
    }, [asanaAuthQuery, confluenceAuthQuery, healthQuery, versionQuery]);
    const toggleAbout = useCallback(() => {
        setAboutOpen((prev) => !prev);
    }, []);
    useEffect(() => {
        if (typeof window === "undefined") {
            return;
        }
        try {
            const storedCustomers = window.localStorage.getItem(RECENT_CUSTOMERS_KEY);
            if (storedCustomers) {
                setRecentCustomers(JSON.parse(storedCustomers));
            }
        }
        catch (error) {
            console.warn("Failed to load recent customers", error);
        }
        try {
            const storedFamilies = window.localStorage.getItem(RECENT_FAMILIES_KEY);
            if (storedFamilies) {
                setRecentFamilies(JSON.parse(storedFamilies));
            }
        }
        catch (error) {
            console.warn("Failed to load recent families", error);
        }
    }, []);
    useEffect(() => {
        if (selectedFamilyPage) {
            setConfluenceParentId(selectedFamilyPage.id);
        }
    }, [selectedFamilyPage]);
    const resetForNewPlan = () => {
        setPlanJson(null);
        setPlanMarkdown("");
        setContextPack(null);
        setVectorStoreId(null);
        setPublishResult(null);
        setQaResult(null);
        setQaBlocked(false);
        setAsanaTasks([]);
        setSuggestedTasks([]);
        setPlanConflicts([]);
        setKnownFingerprints([]);
        setAsanaSkippedCount(0);
        setMessages([]);
        setStatusMessage(null);
        setProjectNameEdited(false);
        setAgentStatuses(INITIAL_AGENT_STATUSES);
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
            pushToast("success", data.message || "Session created.");
        },
        onError: (err) => {
            setError(err.message || "Failed to ingest files.");
            pushToast("error", err.message || "Failed to ingest files.");
        },
    });
    const gradePlanSilently = useCallback(async (plan) => {
        try {
            const { data } = await api.post("/qa/grade", { plan_json: plan });
            const blocked = data.blocked ?? data.score < 85;
            const normalized = { ...data, blocked };
            setQaResult(normalized);
            setQaBlocked(blocked);
            return normalized;
        }
        catch (err) {
            console.warn("Failed to refresh QA grade", err);
            return null;
        }
    }, [setQaBlocked, setQaResult]);
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
            setContextPack(data.context_pack);
            setAgentStatuses(INITIAL_AGENT_STATUSES);
            setQaBlocked(false);
            setQaResult(null);
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
            pushToast("success", "Draft completed.");
        },
        onError: (err) => {
            setError(err.message || "Draft failed.");
            pushToast("error", err.message || "Draft failed.");
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
            setSuggestedTasks(data.suggested_tasks ?? []);
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
            pushToast("success", "Meeting notes applied.");
        },
        onError: (err) => {
            setError(err.message || "Failed to apply meeting notes.");
            pushToast("error", err.message || "Failed to apply meeting notes.");
        },
    });
    const publishMutation = useMutation({
        mutationFn: async () => {
            if (!planJson || !planMarkdown) {
                throw new Error("Draft the plan before publishing.");
            }
            const payload = {
                customer: planJson["customer"] ?? meta.customer,
                family: meta.family || planJson["project"],
                project: meta.projectName || planJson["project"],
                markdown: planMarkdown,
                parent_page_id: confluenceParentId || undefined,
            };
            if (selectedFamilyPage) {
                payload.family = {
                    page_id: selectedFamilyPage.id,
                    space_key: selectedFamilyPage.space_key,
                    title: selectedFamilyPage.title,
                    url: selectedFamilyPage.url,
                };
            }
            const { data } = await api.post("/publish", payload);
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
            pushToast("success", "Publish request sent.");
        },
        onError: (err) => {
            setError(err.message || "Publish failed.");
            pushToast("error", err.message || "Publish failed.");
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
            const blocked = data.blocked ?? data.score < 85;
            const normalized = { ...data, blocked };
            setQaResult(normalized);
            setQaBlocked(blocked);
            setStatusMessage("QA grade completed.");
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: `QA Score: ${data.score.toFixed(1)} / 100`,
                    timestamp: now(),
                },
            ]);
            setError(null);
            pushToast("success", "QA grade completed.");
        },
        onError: (err) => {
            setError(err.message || "QA grading failed.");
            pushToast("error", err.message || "QA grading failed.");
        },
    });
    const asanaMutation = useMutation({
        mutationFn: async ({ tasks, planUrl } = {}) => {
            if (!planJson) {
                throw new Error("Draft the plan before creating tasks.");
            }
            const projectId = selectedAsanaProject?.gid || manualAsanaProjectId.trim();
            if (!projectId) {
                throw new Error("Provide an Asana project selection.");
            }
            const body = {
                project_id: projectId,
                plan_json: planJson,
            };
            if (planUrl) {
                body.plan_url = planUrl;
            }
            if (tasks && tasks.length > 0) {
                body.tasks = tasks;
            }
            const { data } = await api.post("/asana/tasks", body);
            return data;
        },
        onSuccess: (data) => {
            setAsanaTasks(data.created);
            const createdFingerprints = data.created
                .map((task) => task.fingerprint)
                .filter((fp) => Boolean(fp));
            const skippedFingerprints = data.skipped
                .map((task) => task.fingerprint)
                .filter((fp) => Boolean(fp));
            setAsanaSkippedCount(data.skipped.length);
            setKnownFingerprints((prev) => {
                const combined = new Set(prev);
                createdFingerprints.forEach((fp) => combined.add(fp));
                skippedFingerprints.forEach((fp) => combined.add(fp));
                return Array.from(combined);
            });
            const consumedFingerprints = new Set([...createdFingerprints, ...skippedFingerprints]);
            setSuggestedTasks((prev) => prev.filter((task) => {
                if (!task.fingerprint) {
                    return true;
                }
                return !consumedFingerprints.has(task.fingerprint);
            }));
            setStatusMessage(`Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`);
            setMessages((prev) => [
                ...prev,
                {
                    id: makeId(),
                    role: "assistant",
                    content: `Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`,
                    timestamp: now(),
                },
            ]);
            setError(null);
            pushToast("success", `Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`);
        },
        onError: (err) => {
            setError(err.message || "Failed to create Asana tasks.");
            pushToast("error", err.message || "Failed to create Asana tasks.");
        },
    });
    const agentsMutation = useMutation({
        mutationFn: async () => {
            if (!planJson || !vectorStoreId || (!sessionId && !contextPack)) {
                throw new Error("Draft the plan before running specialist agents.");
            }
            const payload = {
                vector_store_id: vectorStoreId,
                plan_json: planJson,
            };
            if (sessionId) {
                payload.session_id = sessionId;
            }
            if (contextPack && !payload.context_pack) {
                payload.context_pack = contextPack;
            }
            const { data } = await api.post("/agents/run", payload);
            return data;
        },
        onMutate: () => {
            setAgentStatuses(makeAgentStatuses("pending"));
            setStatusMessage("Running specialist agents…");
        },
        onSuccess: async (data) => {
            setPlanJson(data.plan_json);
            setSuggestedTasks(data.tasks_suggested ?? []);
            setPlanConflicts(data.conflicts ?? []);
            setStatusMessage("Specialist agents completed.");
            setError(null);
            pushToast("success", "Specialist agents completed.");
            const qaPayload = data.qa;
            let qaBlockedState = false;
            if (qaPayload) {
                const score = typeof qaPayload.score === "number" ? qaPayload.score : 0;
                const blocked = qaPayload.blocked ?? score < 85;
                setQaResult({
                    score,
                    reasons: qaPayload.reasons ?? [],
                    fixes: qaPayload.fixes ?? [],
                    blocked,
                });
                setQaBlocked(blocked);
                qaBlockedState = blocked;
            }
            else {
                const refreshed = await gradePlanSilently(data.plan_json);
                qaBlockedState = Boolean(refreshed?.blocked ?? (refreshed ? refreshed.score < 85 : qaBlocked));
            }
            const hasConflicts = (data.conflicts ?? []).length > 0;
            setAgentStatuses(makeAgentStatuses("ok", {
                sbpqa: qaBlockedState ? "warn" : "ok",
                ...(hasConflicts ? { qma: "warn", pma: "warn", sca: "warn", ema: "warn" } : {}),
            }));
        },
        onError: (err) => {
            setAgentStatuses(makeAgentStatuses("warn"));
            setError(err.message || "Failed to run specialist agents.");
            pushToast("error", err.message || "Failed to run specialist agents.");
        },
    });
    const createProjectMutation = useMutation({
        mutationFn: async (name) => {
            const trimmed = name.trim();
            if (!trimmed) {
                throw new Error("Project name is required.");
            }
            const { data } = await api.post("/asana/projects", {
                name: trimmed,
            });
            return data;
        },
        onSuccess: (project) => {
            const summary = {
                gid: project.gid,
                name: project.name,
                url: project.url,
                team: project.team ?? undefined,
            };
            setSelectedAsanaProject(summary);
            setManualAsanaProjectId("");
            setProjectNameEdited(false);
            setStatusMessage(`Created Asana project ${project.name}`);
            pushToast("success", `Created Asana project: ${project.name}`);
        },
        onError: (err) => {
            pushToast("error", err.message || "Failed to create Asana project.");
        },
    });
    const isLoadingAny = useMemo(() => ingestMutation.isPending ||
        draftMutation.isPending ||
        meetingApplyMutation.isPending ||
        publishMutation.isPending ||
        qaMutation.isPending ||
        asanaMutation.isPending ||
        agentsMutation.isPending, [
        ingestMutation.isPending,
        draftMutation.isPending,
        meetingApplyMutation.isPending,
        publishMutation.isPending,
        qaMutation.isPending,
        asanaMutation.isPending,
        agentsMutation.isPending,
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
    const handleRunAgents = async () => {
        if (agentsMutation.isPending) {
            return;
        }
        setStatusMessage(null);
        if (!planJson || !vectorStoreId || (!sessionId && !contextPack)) {
            pushToast("error", "Draft the plan before running specialist agents.");
            return;
        }
        try {
            await agentsMutation.mutateAsync();
        }
        catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            }
        }
    };
    const handleAsana = async () => {
        setStatusMessage(null);
        const fingerprintSet = new Set(knownFingerprints);
        const deduped = suggestedTasks.filter((task) => {
            if (task.fingerprint) {
                return !fingerprintSet.has(task.fingerprint);
            }
            return true;
        });
        if (deduped.length === 0) {
            setStatusMessage("All suggested tasks have already been sent to Asana.");
            pushToast("info", "No new Asana tasks to send.");
            return;
        }
        await asanaMutation.mutateAsync({
            tasks: deduped,
            planUrl: publishResult?.url,
        });
    };
    const handleNewProjectNameChange = (value) => {
        setProjectNameEdited(true);
        setNewProjectName(value);
    };
    const handleCreateProject = async () => {
        const trimmed = newProjectName.trim();
        if (!trimmed) {
            pushToast("error", "Project name is required.");
            return;
        }
        setStatusMessage(null);
        setError(null);
        try {
            await createProjectMutation.mutateAsync(trimmed);
        }
        catch (err) {
            if (err instanceof Error) {
                setError(err.message);
            }
        }
    };
    const handleBrowse = () => {
        if (publishResult?.url) {
            window.open(publishResult.url, "_blank", "noopener");
        }
    };
    const rememberRecentPage = (page, setList, storageKey) => {
        setList((prev) => {
            const existing = prev.filter((entry) => entry.id !== page.id);
            const next = [page, ...existing].slice(0, MAX_RECENT_PAGES);
            if (typeof window !== "undefined") {
                window.localStorage.setItem(storageKey, JSON.stringify(next));
            }
            return next;
        });
    };
    const handleCustomerSelected = (page) => {
        setSelectedCustomerPage(page);
        if (page) {
            rememberRecentPage(page, setRecentCustomers, RECENT_CUSTOMERS_KEY);
            setMeta((prev) => ({ ...prev, customerPage: page, customer: page.title }));
            setProjectNameEdited(false);
        }
        else {
            setMeta((prev) => ({ ...prev, customerPage: null }));
        }
    };
    const handleFamilySelected = (page) => {
        setSelectedFamilyPage(page);
        if (page) {
            rememberRecentPage(page, setRecentFamilies, RECENT_FAMILIES_KEY);
            setConfluenceParentId(page.id);
            setMeta((prev) => ({ ...prev, familyPage: page, family: page.title }));
            setProjectNameEdited(false);
        }
        else {
            setMeta((prev) => ({ ...prev, familyPage: null }));
            setConfluenceParentId("");
        }
    };
    const handleFamilyUrlPaste = async (url) => {
        if (!url) {
            return;
        }
        const details = extractConfluenceDetails(url);
        if (!details?.pageId) {
            const message = "Couldn't parse Confluence page details from URL.";
            setError(message);
            pushToast("error", message);
            return;
        }
        const provisional = {
            id: details.pageId,
            title: details.title || meta.family || "Family Page",
            url,
            space_key: details.spaceKey,
        };
        handleFamilySelected(provisional);
        setError(null);
        pushToast("info", "Family page set from pasted URL.");
        if (confluenceStatus?.ok) {
            try {
                const { data } = await api.get(`/confluence/page/${details.pageId}`);
                handleFamilySelected(data);
                pushToast("success", `Linked to Confluence page: ${data.title}`);
            }
            catch (err) {
                console.warn("Failed to verify Confluence page", err);
                pushToast("error", "Couldn't verify Confluence page with current credentials.");
            }
        }
    };
    const handleManualAsanaProjectIdChange = (value) => {
        setManualAsanaProjectId(value);
        if (value.trim().length > 0 && selectedAsanaProject) {
            setSelectedAsanaProject(null);
        }
    };
    const handleSelectAsanaProject = (project) => {
        setSelectedAsanaProject(project);
        if (project) {
            setManualAsanaProjectId("");
        }
    };
    const handleConfluenceParentIdChange = (value) => {
        setConfluenceParentId(value);
        if (selectedFamilyPage && selectedFamilyPage.id !== value) {
            setSelectedFamilyPage(null);
            setMeta((prev) => ({ ...prev, familyPage: null }));
        }
    };
    const canPublish = Boolean(confluenceParentId.trim());
    const publishDisabled = isBusy || !planJson || !canPublish || qaBlocked;
    const qaSummary = qaResult?.score !== undefined
        ? `Score ${qaResult.score.toFixed(1)} / 100${qaBlocked ? " — Blocked" : ""}`
        : qaBlocked
            ? "Blocked"
            : null;
    const qaTopFixes = qaResult?.fixes?.slice(0, 3) ?? [];
    const actions = [
        {
            label: agentsMutation.isPending ? "Running Agents…" : "Run Specialist Agents",
            onClick: handleRunAgents,
            disabled: isBusy ||
                !planJson ||
                !vectorStoreId ||
                (!sessionId && !contextPack) ||
                agentsMutation.isPending,
        },
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
            disabled: publishDisabled,
        },
        {
            label: "Create Asana Tasks",
            onClick: handleAsana,
            disabled: isBusy || !planJson || (!selectedAsanaProject && !manualAsanaProjectId.trim()),
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
    return (_jsxs("div", { className: "app-wrapper", children: [_jsx(StatusBar, { healthStatus: healthStatus, confluenceStatus: confluenceStatus, asanaStatus: asanaStatus, onRefresh: handleRefreshStatuses, onToggleAbout: toggleAbout, aboutOpen: aboutOpen, versionInfo: versionQuery.data }), _jsxs("div", { className: "app-shell", children: [_jsx(UploadPanel, { meta: meta, onMetaChange: (update) => setMeta((prev) => ({ ...prev, ...update })), onUpload: handleUpload, uploading: ingestMutation.isPending, sessionId: sessionId, uploadedFiles: uploadedFiles, selectedCustomer: selectedCustomerPage, selectedFamily: selectedFamilyPage, recentCustomers: recentCustomers, recentFamilies: recentFamilies, onCustomerSelected: handleCustomerSelected, onFamilySelected: handleFamilySelected, onFamilyUrlPaste: handleFamilyUrlPaste }), _jsx(PlanPreview, { planJson: planJson, planMarkdown: planMarkdown, qaResult: qaResult, asanaTasks: asanaTasks, publishUrl: publishResult?.url, conflicts: planConflicts, qaBlocked: qaBlocked }), _jsx(ChatPanel, { messages: messages, input: chatInput, onInputChange: setChatInput, onSend: handleSendMessage, sending: meetingApplyMutation.isPending, actions: actions, confluenceParentId: confluenceParentId, onConfluenceParentIdChange: handleConfluenceParentIdChange, selectedAsanaProject: selectedAsanaProject, onSelectAsanaProject: handleSelectAsanaProject, manualAsanaProjectId: manualAsanaProjectId, onManualAsanaProjectIdChange: handleManualAsanaProjectIdChange, newProjectName: newProjectName, onNewProjectNameChange: handleNewProjectNameChange, onCreateProject: handleCreateProject, creatingProject: createProjectMutation.isPending, publishUrl: publishResult?.url, qaSummary: qaSummary, qaBlocked: qaBlocked, qaFixes: qaTopFixes, asanaStatus: asanaTasks.length || asanaSkippedCount
                            ? `Created ${asanaTasks.length}, skipped ${asanaSkippedCount}`
                            : null, statusMessage: statusMessage, errorMessage: error, disabled: isBusy, agentStatuses: agentStatuses, agentsRunning: agentsMutation.isPending })] }), _jsx(ToastContainer, { toasts: toasts, onDismiss: dismissToast })] }));
}
