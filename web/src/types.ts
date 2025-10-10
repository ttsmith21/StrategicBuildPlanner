export interface PlanJson {
  [key: string]: unknown;
}

export interface DraftResponseData {
  plan_json: PlanJson;
  plan_markdown: string;
  source_file_names: string[];
  vector_store_id: string;
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
}
