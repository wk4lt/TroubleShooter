export type EventType =
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "message"
  | "final";

export interface AgentEvent {
  type: EventType;
  phase?: string | null;
  status?: string | null;
  content?: string | null;
  tool?: string | null;
  skill?: string | null;
  call_id?: string | null;
  arguments?: Record<string, unknown> | null;
  result?: unknown;
  duration_ms?: number | null;
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

export interface DirectoryMeta {
  name: string;
  path: string;
}

export interface FileDirectory {
  path: string;
  directories: DirectoryMeta[];
  files: FileMeta[];
}

export interface SkillMeta {
  name: string;
  description: string;
}
