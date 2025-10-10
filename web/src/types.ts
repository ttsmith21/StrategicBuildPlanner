export interface EngineeringCitation {
  source_id: string;
  page_ref?: string | null;
  passage_sha?: string | null;
}

export interface EngineeringRoutingStep {
  op_no: number;
  workcenter: string;
  input: string;
  program: string;
  notes: string[];
  qc: string[];
  sources: EngineeringCitation[];
}

export interface EngineeringFixture {
  name: string;
  purpose: string;
  citations: EngineeringCitation[];
}

export interface EngineeringProgram {
  machine: string;
  program_id: string;
  notes: string;
  citations: EngineeringCitation[];
}

export interface EngineeringCtqCallout {
  ctq: string;
  measurement_plan: string;
  citations: EngineeringCitation[];
}

export interface EngineeringOpenItem {
  issue: string;
  owner: string;
  due: string | null;
  citations: EngineeringCitation[];
}

export interface EngineeringInstructions {
  routing: EngineeringRoutingStep[];
  fixtures: EngineeringFixture[];
  programs: EngineeringProgram[];
  ctqs_for_routing: EngineeringCtqCallout[];
  open_items: EngineeringOpenItem[];
}

export interface PlanJson {
  engineering_instructions?: EngineeringInstructions;
  [key: string]: unknown;
}

export interface ContextPackSource {
  id: string;
  title: string;
  kind: string;
  authority: string;
  precedence_rank: number;
  scope?: string[];
}

export interface ContextPackFact {
  id: string;
  topic: string;
  claim: string;
  status: string;
  authority: string;
  precedence_rank: number;
  citation?: EngineeringCitation;
}

export interface ContextPack {
  project?: Record<string, unknown>;
  sources: ContextPackSource[];
  facts: ContextPackFact[];
  precedence_policy?: string;
}

export interface DraftResponseData {
  plan_json: PlanJson;
  plan_markdown: string;
  source_file_names: string[];
  vector_store_id: string;
  context_pack: ContextPack;
}

export interface IngestResponseData {
  session_id: string;
  message: string;
  file_count: number;
  file_names: string[];
}

export interface PublishResponseData {
  page_id: string;
  url: string;
  title: string;
}

export interface QAGradeResponseData {
  score: number;
  reasons: string[];
  fixes: string[];
}

export interface SuggestedTask {
  name: string;
  notes?: string;
  due_on?: string;
  assignee?: string;
  priority?: string;
  source_hint?: string;
  plan_url?: string;
  section?: string;
  fingerprint?: string;
  owner_hint?: string;
  cost_impact?: string;
  schedule_impact?: string;
}

export interface MeetingApplyResponseData {
  updated_plan_json: PlanJson;
  updated_plan_markdown: string;
  changes_summary: string;
  suggested_tasks: SuggestedTask[];
}

export interface AsanaTaskSummary {
  gid?: string;
  name?: string;
  permalink_url?: string;
  fingerprint?: string;
}

export interface AsanaTasksResponseData {
  created: AsanaTaskSummary[];
  skipped: SuggestedTask[];
}

export interface ConfluencePageSummary {
  id: string;
  title: string;
  url: string;
  space_key?: string;
}

export interface FamilySelectionPayload {
  page_id: string;
  space_key?: string;
  title?: string;
  url?: string;
}

export interface AsanaProjectSummary {
  gid: string;
  name: string;
  url?: string;
  archived?: boolean;
  team?: {
    gid?: string;
    name?: string;
  } | null;
}

export interface AsanaTeamSummary {
  gid: string;
  name: string;
}

export interface AsanaProjectCreateResponse {
  gid: string;
  name: string;
  url?: string;
  team?: {
    gid?: string;
    name?: string;
  } | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface PlannerMeta {
  projectName: string;
  customer: string;
  family: string;
  customerPage?: ConfluencePageSummary | null;
  familyPage?: ConfluencePageSummary | null;
}

export interface AuthStatusResponse {
  ok: boolean;
  reason?: string;
}

export interface VersionInfo {
  version: string;
  build_sha: string;
  build_time?: string;
  model?: string;
  prompt_version?: string;
  schema_version?: string;
}

export interface AgentDelta {
  topic: string;
  delta_type: string;
  delta_summary: string;
  recommended_action: string;
  cost_impact: string;
  schedule_impact: string;
  citation?: EngineeringCitation;
}

export interface AgentsRunResponseData {
  plan_json: PlanJson;
  deltas?: AgentDelta[];
  ema_patch?: { engineering_instructions?: EngineeringInstructions };
  tasks_suggested?: SuggestedTask[];
  qa?: {
    score?: number;
    blocked?: boolean;
    summary?: string;
    fixes?: string[];
  };
}
