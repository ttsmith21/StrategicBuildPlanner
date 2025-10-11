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
  // Focused outputs from EMA
  exceptional_steps?: EngineeringRoutingStep[];
  dfm_actions?: {
    action: string;
    target?: string | null;
    rationale?: string | null;
    citations?: EngineeringCitation[];
  }[];
  quality_routing?: {
    op_no: number;
    workcenter: string;
    quality_operation: string;
    notes?: string[];
    citations?: EngineeringCitation[];
  }[];
}

export interface PlanRequirement {
  topic: string;
  requirement: string;
  source_hint: string;
  confidence: number;
}

export interface CitationRef {
  source_id: string;
  page_ref?: string | null;
  passage_sha?: string | null;
}

export interface QualityPlan {
  ctqs: string[];
  inspection_levels: string[];
  passivation: string | null;
  cleanliness: string | null;
  hold_points: string[];
  required_tests: string[];
  documentation: string[];
  metrology: string[];
}

export interface PurchasingItem {
  item: string;
  lead_time?: string | null;
  vendor_hint?: string | null;
  citations: CitationRef[];
}

export interface PurchasingAlternate {
  item: string;
  alternate: string;
  rationale?: string | null;
  citations: CitationRef[];
}

export interface PurchasingRfq {
  item: string;
  vendor?: string | null;
  due?: string | null;
  citations: CitationRef[];
}

export interface PurchasingPlan {
  long_leads: PurchasingItem[];
  coo_mtr?: string | null;
  alternates: PurchasingAlternate[];
  rfqs: PurchasingRfq[];
}

export interface ScheduleMilestone {
  name: string;
  start_hint?: string | null;
  end_hint?: string | null;
  owner?: string | null;
  citations: CitationRef[];
}

export interface SchedulePlan {
  milestones: ScheduleMilestone[];
  do_early: string[];
  risks: string[];
}

export interface ExecutionTimebox {
  window: string;
  focus: string;
  owner_hint?: string | null;
  notes: string[];
  citations: CitationRef[];
}

export interface ExecutionStrategy {
  timeboxes: ExecutionTimebox[];
  notes: string[];
}

export interface PlanConflict {
  topic: string;
  issue: string;
  citations: CitationRef[];
}

export interface PlanJson {
  project?: string;
  customer?: string;
  revision?: string;
  summary?: string;
  keys?: string[];
  requirements?: PlanRequirement[];
  process_flow?: string;
  tooling_fixturing?: string;
  materials_finishes?: string;
  ctqs?: string[];
  risks?: string[];
  open_questions?: string[];
  cost_levers?: string[];
  pack_ship?: string;
  source_files_used?: string[];
  engineering_instructions?: EngineeringInstructions;
  quality_plan?: QualityPlan;
  purchasing?: PurchasingPlan;
  release_plan?: SchedulePlan;
  execution_strategy?: ExecutionStrategy;
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

export interface IngestResponseData {
  session_id: string;
  message: string;
  file_count: number;
  file_names: string[];
  vector_store_id: string;
  context_pack: ContextPack;
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
  blocked?: boolean;
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
  filesMeta?: Record<string, {
    doc_type?: string;
    authority?: "mandatory" | "conditional" | "reference" | "internal" | string;
    precedence_rank?: number | "highest" | "high" | "medium" | "low" | string;
  }>;
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

export type SpecialistAgentKey = "qma" | "pma" | "sca" | "ema" | "sbpqa";

export interface AgentsRunResponseData {
  plan_json: PlanJson;
  plan_markdown: string;
  deltas?: AgentDelta[];
  tasks_suggested?: SuggestedTask[];
  tasks?: { suggested: SuggestedTask[]; created: SuggestedTask[]; skipped: (SuggestedTask | string)[] };
  qa?: {
    score?: number;
    blocked?: boolean;
    summary?: string;
    fixes?: string[];
    reasons?: string[];
  };
  conflicts?: PlanConflict[];
  context_pack?: ContextPack;
  session_id?: string;
  vector_store_id?: string;
}

// Session models (for resumable sessions)
export interface SessionMessageRecord {
  ts: number;
  role: string;
  text: string;
  meta?: Record<string, unknown>;
}

export interface SessionSnapshotRecord {
  ts: number;
  plan_json?: Record<string, unknown>;
  context_pack?: ContextPack;
  vector_store_id?: string | null;
  note?: string | null;
}

export interface SessionRecord {
  session_id: string;
  project_name?: string | null;
  created_ts: number;
  updated_ts: number;
  messages: SessionMessageRecord[];
  snapshots: SessionSnapshotRecord[];
}
