export type EventType =
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "message"
  | "final";

export interface AgentEvent {
  type: EventType;
  content?: string | null;
  tool?: string | null;
  result?: unknown;
  timestamp?: number;
}

export interface AgentState {
  taskId: string;
  status: string;
  events: AgentEvent[];
  messages: string[];
  result: unknown;
}

export interface TaskRun {
  taskId: string;
  input: string;
  status: string;
  events: AgentEvent[];
  result: unknown;
  error?: string | null;
}

export interface FileMeta {
  file_id: string;
  filename: string;
  relpath?: string;
  size: number;
}

export interface SkillMeta {
  name: string;
  description: string;
}
