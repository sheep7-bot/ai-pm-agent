export type Priority = "P0" | "P1" | "P2";

export interface StepEvent {
  node: string;
  status: "running" | "done" | "error";
  title: string;
  detail: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  events: StepEvent[];
  prd?: PrdEnvelope | null;
  created_at?: string;
}

export interface Persona {
  name: string;
  description: string;
  needs: string[];
}

export interface Feature {
  name: string;
  description: string;
  priority: Priority;
  rationale?: string;
}

export interface Competitor {
  name: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  source_url?: string | null;
}

export interface Metric {
  name: string;
  target: string;
  how_to_measure: string;
}

export interface Milestone {
  phase: string;
  timeline: string;
  deliverables: string[];
}

export interface PRD {
  product_name: string;
  one_liner: string;
  background: string;
  goals: string[];
  target_users: Persona[];
  features: Feature[];
  competitors: Competitor[];
  metrics: Metric[];
  milestones: Milestone[];
  risks: string[];
  open_questions: string[];
}

export interface PrdEnvelope {
  version: number;
  data: PRD | null;
  change_summary?: string;
  changed_sections?: string[];
  created_at?: string;
}

export interface SessionMeta {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface VersionMeta {
  version: number;
  change_summary: string;
  changed_sections: string[];
  created_at: string;
}
