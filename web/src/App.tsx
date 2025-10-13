import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { UploadPanel } from "./components/UploadPanel";
import { PlanPreview } from "./components/PlanPreview";
import { ChatFloat } from "./components/ChatFloat";
import { ChatPanel } from "./components/ChatPanel";
import { StatusBar } from "./components/StatusBar";
import { SessionBar } from "./components/SessionBar";
import { SessionHistory } from "./components/SessionHistory";
import { SessionHistoryCompact } from "./components/SessionHistoryCompact";
import { Toast, ToastContainer } from "./components/ToastContainer";
import {
  AsanaProjectSummary,
  AsanaTaskSummary,
  AgentsRunResponseData,
  AsanaTasksResponseData,
  AsanaProjectCreateResponse,
  AuthStatusResponse,
  ChatMessage,
  ConfluencePageSummary,
  ContextPack,
  IngestResponseData,
  MeetingApplyResponseData,
  PlannerMeta,
  PlanConflict,
  PlanJson,
  PublishResponseData,
  QAGradeResponseData,
  SpecialistAgentKey,
  SuggestedTask,
  VersionInfo,
  SessionRecord,
} from "./types";

// Local UI types/utilities
type AgentStatus = "idle" | "pending" | "ok" | "warn";
type AgentStatusMap = Record<SpecialistAgentKey, AgentStatus>;
const SPECIALIST_AGENT_KEYS: SpecialistAgentKey[] = [
  "qma",
  "pma",
  "sca",
  "ema",
  "sbpqa",
];
const RECENT_CUSTOMERS_KEY = "apqp_recent_customers";
const RECENT_FAMILIES_KEY = "apqp_recent_families";
const MAX_RECENT_PAGES = 8;
const makeId = () => Math.random().toString(36).slice(2);
const now = () => new Date().toISOString();

const INITIAL_AGENT_STATUSES: AgentStatusMap = {
  qma: "idle",
  pma: "idle",
  sca: "idle",
  ema: "idle",
  sbpqa: "idle",
};

const makeAgentStatuses = (
  status: AgentStatus,
  overrides: Partial<AgentStatusMap> = {}
): AgentStatusMap => {
  const base = Object.fromEntries(
    SPECIALIST_AGENT_KEYS.map((key) => [key, status])
  ) as AgentStatusMap;
  return { ...base, ...overrides };
};

const extractConfluenceDetails = (
  url: string
): { pageId: string; spaceKey?: string; title?: string } | null => {
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
    let spaceKey: string | undefined;
    const spacesIndex = segments.findIndex((segment) => segment === "spaces");
    if (spacesIndex >= 0 && segments[spacesIndex + 1]) {
      spaceKey = decodeURIComponent(segments[spacesIndex + 1]);
    }
    const titleSegment = segments[segments.length - 1];
    const title = titleSegment ? decodeURIComponent(titleSegment.replace(/\+/g, " ")).replace(/-/g, " ") : undefined;
    return { pageId, spaceKey, title };
  } catch (error) {
    console.warn("Failed to parse Confluence URL", error);
    return null;
  }
};

export default function App() {
  const [meta, setMeta] = useState<PlannerMeta>({
    projectName: "",
    customer: "",
    family: "",
    customerPage: null,
    familyPage: null,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [planJson, setPlanJson] = useState<PlanJson | null>(null);
  const [planMarkdown, setPlanMarkdown] = useState<string>("");
  const [contextPack, setContextPack] = useState<ContextPack | null>(null);
  const [vectorStoreId, setVectorStoreId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [publishResult, setPublishResult] = useState<PublishResponseData | null>(null);
  const [qaResult, setQaResult] = useState<QAGradeResponseData | null>(null);
  const [asanaTasks, setAsanaTasks] = useState<AsanaTaskSummary[]>([]);
  const [suggestedTasks, setSuggestedTasks] = useState<SuggestedTask[]>([]);
  const [planConflicts, setPlanConflicts] = useState<PlanConflict[]>([]);
  const [knownFingerprints, setKnownFingerprints] = useState<string[]>([]);
  const [asanaSkippedCount, setAsanaSkippedCount] = useState<number>(0);
  const [confluenceParentId, setConfluenceParentId] = useState<string>("");
  const [selectedCustomerPage, setSelectedCustomerPage] = useState<ConfluencePageSummary | null>(null);
  const [selectedFamilyPage, setSelectedFamilyPage] = useState<ConfluencePageSummary | null>(null);
  const [recentCustomers, setRecentCustomers] = useState<ConfluencePageSummary[]>([]);
  const [recentFamilies, setRecentFamilies] = useState<ConfluencePageSummary[]>([]);
  const [selectedAsanaProject, setSelectedAsanaProject] = useState<AsanaProjectSummary | null>(null);
  const [manualAsanaProjectId, setManualAsanaProjectId] = useState<string>("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState<boolean>(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [aboutOpen, setAboutOpen] = useState<boolean>(false);
  const [projectNameEdited, setProjectNameEdited] = useState<boolean>(false);
  const [agentStatuses, setAgentStatuses] = useState(INITIAL_AGENT_STATUSES);
  const [qaBlocked, setQaBlocked] = useState<boolean>(false);
  const defaultProjectName = useMemo(() => {
    const customer = meta.customer || "Customer";
    const family = meta.family || meta.projectName || "Family";
    return `APQP — ${customer} — ${family}`;
  }, [meta.customer, meta.family, meta.projectName]);
  const [newProjectName, setNewProjectName] = useState<string>(defaultProjectName);

  useEffect(() => {
    if (!projectNameEdited) {
      setNewProjectName(defaultProjectName);
    }
  }, [defaultProjectName, projectNameEdited]);

  const pushToast = useCallback((type: Toast["type"], message: string) => {
    setToasts((prev) => [...prev, { id: makeId(), type, message }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const healthQuery = useQuery({
    queryKey: ["healthz"],
    queryFn: async () => {
      const { data } = await api.get<{ status: string }>("/healthz");
      return data;
    },
    retry: false,
  });

  const confluenceAuthQuery = useQuery<AuthStatusResponse>({
    queryKey: ["auth", "confluence"],
    queryFn: async () => {
      const { data } = await api.get<AuthStatusResponse>("/auth/confluence/check");
      return data;
    },
    retry: false,
  });

  const asanaAuthQuery = useQuery<AuthStatusResponse>({
    queryKey: ["auth", "asana"],
    queryFn: async () => {
      const { data } = await api.get<AuthStatusResponse>("/auth/asana/check");
      return data;
    },
    retry: false,
  });

  const versionQuery = useQuery<VersionInfo>({
    queryKey: ["version"],
    queryFn: async () => {
      const { data } = await api.get<VersionInfo>("/version");
      return data;
    },
    staleTime: 60_000,
  });

  const sessionsQuery = useQuery<SessionRecord[]>({
    queryKey: ["sessions"],
    queryFn: async () => {
      const { data } = await api.get<SessionRecord[]>("/sessions", { params: { limit: 12 } });
      return data;
    },
    staleTime: 30_000,
  });

  const sessionDetailQuery = useQuery<SessionRecord | null>({
    queryKey: ["session", sessionId],
    queryFn: async () => {
      if (!sessionId) return null;
      const { data } = await api.get<SessionRecord>(`/sessions/${sessionId}`);
      return data;
    },
    enabled: Boolean(sessionId),
    staleTime: 10_000,
  });

  const healthStatus: "unknown" | "ok" | "error" = useMemo(() => {
    if (healthQuery.isPending) {
      return "unknown";
    }
    if (healthQuery.isError) {
      return "error";
    }
    return healthQuery.data?.status === "ok" ? "ok" : "error";
  }, [healthQuery.data?.status, healthQuery.isError, healthQuery.isPending]);

  const confluenceStatus: AuthStatusResponse | undefined = useMemo(() => {
    if (confluenceAuthQuery.isError) {
      return { ok: false, reason: "unreachable" };
    }
    return confluenceAuthQuery.data;
  }, [confluenceAuthQuery.data, confluenceAuthQuery.isError]);

  const asanaStatus: AuthStatusResponse | undefined = useMemo(() => {
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
    } catch (error) {
      console.warn("Failed to load recent customers", error);
    }
    try {
      const storedFamilies = window.localStorage.getItem(RECENT_FAMILIES_KEY);
      if (storedFamilies) {
        setRecentFamilies(JSON.parse(storedFamilies));
      }
    } catch (error) {
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

  const ingestMutation = useMutation<IngestResponseData, Error, FileList>({
    mutationFn: async (files: FileList) => {
      // Only require a project name when creating a new vector store
      if (!vectorStoreId && !meta.projectName.trim()) {
        throw new Error("Project name is required before ingesting files.");
      }

      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append("files", file);
      });
      // Required only for new vector store creation
      if (!vectorStoreId) {
        formData.append("project_name", meta.projectName);
      }
      if (sessionId) formData.append("session_id", sessionId);
      if (vectorStoreId) formData.append("vector_store_id", vectorStoreId);
      formData.append("append", "true");
      
      // Optional metadata
      if (meta.customer) {
        formData.append("customer", meta.customer);
      }
      if (meta.family) {
        formData.append("family", meta.family);
      }

      // Optional: upload presets for doc types/authority/precedence
      if (meta.filesMeta && Object.keys(meta.filesMeta).length > 0) {
        formData.append("files_meta", JSON.stringify(meta.filesMeta));
      }

      const { data } = await api.post<IngestResponseData>("/ingest", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (data) => {
      // Do not blow away context on append; preserve state, only update what changed
      if (!sessionId) {
        resetForNewPlan();
      }
      setSessionId(data.session_id);
      setUploadedFiles(data.file_names);
      
      // New: Store vector_store_id and context_pack from /ingest
      if (data.vector_store_id) {
        setVectorStoreId(data.vector_store_id);
      }
      if (data.context_pack) setContextPack(data.context_pack);
      
      setStatusMessage(data.message);
      setError(null);
      pushToast("success", data.message || "Session created. Ready to run specialist agents!");
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to ingest files.");
      pushToast("error", err.message || "Failed to ingest files.");
    },
  });

  const gradePlanSilently = useCallback(
    async (plan: PlanJson) => {
      try {
        const { data } = await api.post<QAGradeResponseData>("/qa/grade", { plan_json: plan });
        const blocked = data.blocked ?? data.score < 85;
        const normalized: QAGradeResponseData = { ...data, blocked };
        setQaResult(normalized);
        setQaBlocked(blocked);
        return normalized;
      } catch (err) {
        console.warn("Failed to refresh QA grade", err);
        return null;
      }
    },
    [setQaBlocked, setQaResult]
  );

  const meetingApplyMutation = useMutation<MeetingApplyResponseData, Error, string>({
    mutationFn: async (transcript: string) => {
      if (!planJson) {
        throw new Error("Run specialist agents before applying meeting notes.");
      }
      const payload: Record<string, unknown> = {
        plan_json: planJson,
        transcript_texts: [transcript],
      };
      if (sessionId) {
        payload.session_id = sessionId;
      }
      const { data } = await api.post<MeetingApplyResponseData>("/meeting/apply", payload);
      return data;
    },
    onSuccess: (data, transcript) => {
      setPlanJson(data.updated_plan_json);
      setPlanMarkdown(data.updated_plan_markdown);
      setSuggestedTasks(data.suggested_tasks ?? []);
      const postSessionMessage = async (role: string, text: string) => {
        try {
          if (sessionId) {
            await api.post(`/sessions/${sessionId}/messages`, { role, text });
          }
        } catch (err) {
          // non-fatal
        }
      };
      setMessages((prev: ChatMessage[]) => [
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
      // Persist chat into session history when available
      void postSessionMessage("user", transcript);
      void postSessionMessage("assistant", data.changes_summary);
      setStatusMessage("Meeting notes applied.");
      setChatInput("");
      setError(null);
      pushToast("success", "Meeting notes applied.");
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to apply meeting notes.");
      pushToast("error", err.message || "Failed to apply meeting notes.");
    },
  });

  const publishMutation = useMutation<PublishResponseData, Error>({
    mutationFn: async () => {
      if (!planJson || !planMarkdown) {
        throw new Error("Run specialist agents before publishing.");
      }
      const payload: Record<string, unknown> = {
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
      const { data } = await api.post<PublishResponseData>("/publish", payload);
      return data;
    },
    onSuccess: (data) => {
      setPublishResult(data);
      setStatusMessage(`Published to Confluence page ${data.title}.`);
      setMessages((prev: ChatMessage[]) => [
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
    onError: (err: Error) => {
      setError(err.message || "Publish failed.");
      pushToast("error", err.message || "Publish failed.");
    },
  });

  const qaMutation = useMutation<QAGradeResponseData, Error>({
    mutationFn: async () => {
      if (!planJson) {
        throw new Error("Run specialist agents before running QA.");
      }
      const { data } = await api.post<QAGradeResponseData>("/qa/grade", {
        plan_json: planJson,
      });
      return data;
    },
    onSuccess: (data) => {
      const blocked = data.blocked ?? data.score < 85;
      const normalized: QAGradeResponseData = { ...data, blocked };
      setQaResult(normalized);
      setQaBlocked(blocked);
      setStatusMessage("QA grade completed.");
      setMessages((prev: ChatMessage[]) => [
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
    onError: (err: Error) => {
      setError(err.message || "QA grading failed.");
      pushToast("error", err.message || "QA grading failed.");
    },
  });

  const asanaMutation = useMutation<
    AsanaTasksResponseData,
    Error,
    { tasks?: SuggestedTask[]; planUrl?: string }
  >({
    mutationFn: async ({ tasks, planUrl } = {}) => {
      if (!planJson) {
        throw new Error("Run specialist agents before creating tasks.");
      }
      const projectId = selectedAsanaProject?.gid || manualAsanaProjectId.trim();
      if (!projectId) {
        throw new Error("Provide an Asana project selection.");
      }
      const body: Record<string, unknown> = {
        project_id: projectId,
        plan_json: planJson,
      };
      if (planUrl) {
        body.plan_url = planUrl;
      }
      if (tasks && tasks.length > 0) {
        body.tasks = tasks;
      }

      const { data } = await api.post<AsanaTasksResponseData>("/asana/tasks", body);
      return data;
    },
    onSuccess: (data) => {
      setAsanaTasks(data.created);
      const createdFingerprints = data.created
        .map((task) => task.fingerprint)
        .filter((fp): fp is string => Boolean(fp));
      const skippedFingerprints = data.skipped
        .map((task) => task.fingerprint)
        .filter((fp): fp is string => Boolean(fp));
      setAsanaSkippedCount(data.skipped.length);
      setKnownFingerprints((prev) => {
        const combined = new Set(prev);
        createdFingerprints.forEach((fp) => combined.add(fp));
        skippedFingerprints.forEach((fp) => combined.add(fp));
        return Array.from(combined);
      });
      const consumedFingerprints = new Set([...createdFingerprints, ...skippedFingerprints]);
      setSuggestedTasks((prev) =>
        prev.filter((task) => {
          if (!task.fingerprint) {
            return true;
          }
          return !consumedFingerprints.has(task.fingerprint);
        })
      );
      setStatusMessage(`Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`);
      setMessages((prev: ChatMessage[]) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          content: `Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`,
          timestamp: now(),
        },
      ]);
      setError(null);
      pushToast(
        "success",
        `Created ${data.created.length}, skipped ${data.skipped.length} duplicate task(s).`
      );
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to create Asana tasks.");
      pushToast("error", err.message || "Failed to create Asana tasks.");
    },
  });

  const agentsMutation = useMutation<AgentsRunResponseData, Error>({
    mutationFn: async () => {
      if (!vectorStoreId || (!sessionId && !contextPack)) {
        throw new Error("Upload documents first to create a session.");
      }
      const payload: Record<string, unknown> = {
        vector_store_id: vectorStoreId,
      };
      // Optional: include existing plan_json if available (for refinement)
      if (planJson) {
        payload.plan_json = planJson;
      }
      if (sessionId) {
        payload.session_id = sessionId;
      }
      if (contextPack && !payload.context_pack) {
        payload.context_pack = contextPack;
      }
      const { data } = await api.post<AgentsRunResponseData>("/agents/run", payload);
      return data;
    },
    onMutate: () => {
      setAgentStatuses(makeAgentStatuses("pending"));
      setStatusMessage("Running specialist agents…");
    },
    onSuccess: async (data) => {
      setPlanJson(data.plan_json);
      setPlanMarkdown(data.plan_markdown);
      setSuggestedTasks((data as any).tasks?.suggested ?? data.tasks_suggested ?? []);
      setPlanConflicts(data.conflicts ?? []);
      if (data.context_pack) {
        setContextPack(data.context_pack as unknown as ContextPack);
      }
      if (data.vector_store_id) {
        setVectorStoreId(data.vector_store_id);
      }
      if ((data as any).session_id) {
        setSessionId((data as any).session_id as string);
      }
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
      } else {
        const refreshed = await gradePlanSilently(data.plan_json);
        qaBlockedState = Boolean(refreshed?.blocked ?? (refreshed ? refreshed.score < 85 : qaBlocked));
      }

      const hasConflicts = (data.conflicts ?? []).length > 0;
      setAgentStatuses(
        makeAgentStatuses("ok", {
          sbpqa: qaBlockedState ? "warn" : "ok",
          ...(hasConflicts ? { qma: "warn", pma: "warn", sca: "warn", ema: "warn" } : {}),
        })
      );
    },
    onError: (err: Error) => {
      setAgentStatuses(makeAgentStatuses("warn"));
      setError(err.message || "Failed to run specialist agents.");
      pushToast("error", err.message || "Failed to run specialist agents.");
    },
  });

  const createProjectMutation = useMutation<AsanaProjectCreateResponse, Error, string>({
    mutationFn: async (name: string) => {
      const trimmed = name.trim();
      if (!trimmed) {
        throw new Error("Project name is required.");
      }
      const { data } = await api.post<AsanaProjectCreateResponse>("/asana/projects", {
        name: trimmed,
      });
      return data;
    },
    onSuccess: (project) => {
      const summary: AsanaProjectSummary = {
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
    onError: (err: Error) => {
      pushToast("error", err.message || "Failed to create Asana project.");
    },
  });

  const isLoadingAny = useMemo(
    () =>
      ingestMutation.isPending ||
      meetingApplyMutation.isPending ||
      publishMutation.isPending ||
      qaMutation.isPending ||
      asanaMutation.isPending ||
      agentsMutation.isPending,
    [
      ingestMutation.isPending,
      meetingApplyMutation.isPending,
      publishMutation.isPending,
      qaMutation.isPending,
      asanaMutation.isPending,
      agentsMutation.isPending,
    ]
  );

  useEffect(() => {
    setIsBusy(isLoadingAny);
  }, [isLoadingAny]);

  const handleUpload = async (files: FileList) => {
    setStatusMessage(null);
    await ingestMutation.mutateAsync(files);
  };

  const handleResumeSession = async (sid: string) => {
    try {
      const { data } = await api.get<SessionRecord>(`/sessions/${sid}`);
      setSessionId(data.session_id);
      const last = (data.snapshots || []).slice(-1)[0];
      if (last) {
        if (last.plan_json && Object.keys(last.plan_json).length > 0) {
          setPlanJson(last.plan_json as any);
        }
        if (last.context_pack) {
          setContextPack(last.context_pack);
        }
        if (last.vector_store_id) {
          setVectorStoreId(last.vector_store_id);
        }
        // Hydrate meta fields from snapshot so uploads don't block on empty project name
        try {
          const pj = (last as any).plan_json?.project || (last as any).context_pack?.project?.title || meta.projectName;
          const cust = (last as any).plan_json?.customer || (last as any).context_pack?.project?.customer || meta.customer;
          // Use family from plan/context if available; fall back to project when reasonable
          const fam = (last as any).plan_json?.family || (last as any).context_pack?.project?.family || (last as any).plan_json?.project || meta.family;
          setMeta((prev) => ({
            ...prev,
            projectName: pj || prev.projectName,
            customer: cust || prev.customer,
            family: fam || prev.family,
          }));
        } catch {
          // non-fatal
        }
        setStatusMessage("Session resumed from last snapshot.");
        pushToast("success", "Session resumed.");
      } else {
        setStatusMessage("Session loaded. No snapshots yet.");
      }
    } catch (err) {
      pushToast("error", "Failed to resume session.");
    }
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
    if (!vectorStoreId || (!sessionId && !contextPack)) {
      pushToast("error", "Upload documents first to create a session.");
      return;
    }
    try {
      await agentsMutation.mutateAsync();
    } catch (err) {
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

  const handleNewProjectNameChange = (value: string) => {
    setProjectNameEdited(true);
    setNewProjectName(value);
    // Update meta.projectName so it's available for /ingest
    setMeta((prev) => ({ ...prev, projectName: value }));
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
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleBrowse = () => {
    if (publishResult?.url) {
      try {
        window.open(publishResult.url, "_blank", "noopener");
      } catch (error) {
        pushToast("error", "Failed to open URL. Popup may be blocked.");
      }
    } else {
      pushToast("error", "No URL available to open");
    }
  };

  const rememberRecentPage = (
    page: ConfluencePageSummary,
    setList: typeof setRecentCustomers,
    storageKey: string
  ) => {
    setList((prev) => {
      const existing = prev.filter((entry) => entry.id !== page.id);
      const next = [page, ...existing].slice(0, MAX_RECENT_PAGES);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      }
      return next;
    });
  };

  const handleCustomerSelected = (page: ConfluencePageSummary | null) => {
    setSelectedCustomerPage(page);
    if (page) {
      rememberRecentPage(page, setRecentCustomers, RECENT_CUSTOMERS_KEY);
      setMeta((prev) => ({ ...prev, customerPage: page, customer: page.title }));
      setProjectNameEdited(false);
    } else {
      setMeta((prev) => ({ ...prev, customerPage: null }));
    }
  };

  const handleFamilySelected = (page: ConfluencePageSummary | null) => {
    setSelectedFamilyPage(page);
    if (page) {
      rememberRecentPage(page, setRecentFamilies, RECENT_FAMILIES_KEY);
      setConfluenceParentId(page.id);
      setMeta((prev) => ({ ...prev, familyPage: page, family: page.title }));
      setProjectNameEdited(false);
    } else {
      setMeta((prev) => ({ ...prev, familyPage: null }));
      setConfluenceParentId("");
    }
  };

  const handleFamilyUrlPaste = async (url: string) => {
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

    const provisional: ConfluencePageSummary = {
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
        const { data } = await api.get<ConfluencePageSummary>(`/confluence/page/${details.pageId}`);
        handleFamilySelected(data);
        pushToast("success", `Linked to Confluence page: ${data.title}`);
      } catch (err) {
        console.warn("Failed to verify Confluence page", err);
        pushToast("error", "Couldn't verify Confluence page with current credentials.");
      }
    }
  };

  const handleManualAsanaProjectIdChange = (value: string) => {
    setManualAsanaProjectId(value);
    if (value.trim().length > 0 && selectedAsanaProject) {
      setSelectedAsanaProject(null);
    }
  };

  const handleSelectAsanaProject = (project: AsanaProjectSummary | null) => {
    setSelectedAsanaProject(project);
    if (project) {
      setManualAsanaProjectId("");
    }
  };

  const handleConfluenceParentIdChange = (value: string) => {
    setConfluenceParentId(value);
    if (selectedFamilyPage && selectedFamilyPage.id !== value) {
      setSelectedFamilyPage(null);
      setMeta((prev) => ({ ...prev, familyPage: null }));
    }
  };

  const canPublish = Boolean(confluenceParentId.trim());
  const publishDisabled = isBusy || !planJson || !canPublish || qaBlocked;
  const qaSummary =
    qaResult?.score !== undefined
      ? `Score ${qaResult.score.toFixed(1)} / 100${qaBlocked ? " — Blocked" : ""}`
      : qaBlocked
      ? "Blocked"
      : null;
  const qaTopFixes = qaResult?.fixes?.slice(0, 3) ?? [];

  const actions = [
    {
      label: agentsMutation.isPending ? "Running Agents…" : "Run Specialist Agents",
      onClick: handleRunAgents,
      disabled:
        isBusy ||
        !vectorStoreId ||
        (!sessionId && !contextPack) ||
        agentsMutation.isPending,
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
      variant: "secondary" as const,
    },
  ];

  // Keyboard shortcuts: R=Run, P=Publish, Q=QA (ignored when typing in inputs/textareas)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      try {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        const el = e.target as HTMLElement | null;
        const tag = (el?.tagName || "").toUpperCase();
        if (tag === "INPUT" || tag === "TEXTAREA" || (el as any)?.isContentEditable) return;
        const k = e.key?.toLowerCase?.() || "";
        if (k === "r") {
          e.preventDefault();
          handleRunAgents();
        } else if (k === "p") {
          e.preventDefault();
          handlePublish();
        } else if (k === "q") {
          e.preventDefault();
          handleQa();
        }
      } catch {
        // noop
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleRunAgents, handlePublish, handleQa]);

  return (
    <div className="app-wrapper">
      <StatusBar
        healthStatus={healthStatus}
        confluenceStatus={confluenceStatus}
        asanaStatus={asanaStatus}
        onRefresh={handleRefreshStatuses}
        onToggleAbout={toggleAbout}
        aboutOpen={aboutOpen}
        versionInfo={versionQuery.data}
      />

      <SessionBar
        sessions={sessionsQuery.data || []}
        currentSessionId={sessionId}
        onResume={handleResumeSession}
      />

      <div className="app-shell">
        <div className="left-col">
          <UploadPanel
          meta={meta}
          onMetaChange={(update) => setMeta((prev) => ({ ...prev, ...update }))}
          onUpload={handleUpload}
          uploading={ingestMutation.isPending}
          sessionId={sessionId}
          vectorStoreId={vectorStoreId}
          uploadedFiles={uploadedFiles}
          selectedCustomer={selectedCustomerPage}
          selectedFamily={selectedFamilyPage}
          recentCustomers={recentCustomers}
          recentFamilies={recentFamilies}
          onCustomerSelected={handleCustomerSelected}
          onFamilySelected={handleFamilySelected}
          onFamilyUrlPaste={handleFamilyUrlPaste}
          pushToast={pushToast}
          />
          {sessionId && (
            <div style={{ marginTop: "0.75rem" }}>
              <SessionHistoryCompact messages={sessionDetailQuery.data?.messages || []} />
            </div>
          )}
        </div>

        <PlanPreview
          planJson={planJson}
          planMarkdown={planMarkdown}
          qaResult={qaResult}
          asanaTasks={asanaTasks}
          publishUrl={publishResult?.url}
          conflicts={planConflicts}
          qaBlocked={qaBlocked}
          suggestedTasks={suggestedTasks}
          contextPack={contextPack}
          sessionId={sessionId || undefined}
          sessionSnapshots={sessionDetailQuery.data?.snapshots || []}
          onRestoreSnapshot={(json, md, cp) => {
            setPlanJson(json as any);
            if (md) setPlanMarkdown(md);
            if (cp) setContextPack(cp as any);
          }}
          creatingTasks={asanaMutation.isPending}
          onCreateTasks={async (tasks) => {
            try {
              await asanaMutation.mutateAsync({ tasks, planUrl: publishResult?.url });
            } catch (err) {
              // error toasts already handled in mutation
            }
          }}
        />

        <ChatFloat
          messages={messages}
          input={chatInput}
          onInputChange={setChatInput}
          onSend={handleSendMessage}
          sending={meetingApplyMutation.isPending}
          actions={actions}
          confluenceParentId={confluenceParentId}
          onConfluenceParentIdChange={handleConfluenceParentIdChange}
          selectedAsanaProject={selectedAsanaProject}
          onSelectAsanaProject={handleSelectAsanaProject}
          manualAsanaProjectId={manualAsanaProjectId}
          onManualAsanaProjectIdChange={handleManualAsanaProjectIdChange}
          newProjectName={newProjectName}
          onNewProjectNameChange={handleNewProjectNameChange}
          onCreateProject={handleCreateProject}
          creatingProject={createProjectMutation.isPending}
          publishUrl={publishResult?.url}
          qaSummary={qaSummary}
          qaBlocked={qaBlocked}
          qaFixes={qaTopFixes}
          asanaStatus={
            asanaTasks.length || asanaSkippedCount
              ? `Created ${asanaTasks.length}, skipped ${asanaSkippedCount}`
              : null
          }
          statusMessage={statusMessage}
          errorMessage={error}
          disabled={isBusy}
          agentStatuses={agentStatuses}
          agentsRunning={agentsMutation.isPending}
          pushToast={pushToast}
        />
        <ChatPanel
          messages={messages}
          input={chatInput}
          onInputChange={setChatInput}
          onSend={handleSendMessage}
          sending={meetingApplyMutation.isPending}
          actions={actions}
          confluenceParentId={confluenceParentId}
          onConfluenceParentIdChange={handleConfluenceParentIdChange}
          selectedAsanaProject={selectedAsanaProject}
          onSelectAsanaProject={handleSelectAsanaProject}
          manualAsanaProjectId={manualAsanaProjectId}
          onManualAsanaProjectIdChange={handleManualAsanaProjectIdChange}
          newProjectName={newProjectName}
          onNewProjectNameChange={handleNewProjectNameChange}
          onCreateProject={handleCreateProject}
          creatingProject={createProjectMutation.isPending}
          publishUrl={publishResult?.url}
          qaSummary={qaSummary}
          qaBlocked={qaBlocked}
          qaFixes={qaTopFixes}
          asanaStatus={
            asanaTasks.length || asanaSkippedCount
              ? `Created ${asanaTasks.length}, skipped ${asanaSkippedCount}`
              : null
          }
          statusMessage={statusMessage}
          errorMessage={error}
          disabled={isBusy}
          agentStatuses={agentStatuses}
          agentsRunning={agentsMutation.isPending}
          hideChat
          pushToast={pushToast}
        />
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
