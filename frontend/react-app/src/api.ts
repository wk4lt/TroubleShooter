import { FileMeta, SkillMeta } from "./types";

let sessionId = "";

export function setSessionId(id: string) {
  sessionId = id;
}

export function getSessionId() {
  return sessionId;
}

function headers(): Record<string, string> {
  return { "X-Session-Id": sessionId };
}

export async function createTask(input: string, skill?: string | null): Promise<string> {
  const resp = await fetch("/api/task", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers() },
    body: JSON.stringify({ input, skill: skill ?? null }),
  });
  if (!resp.ok) {
    throw new Error(`创建任务失败: ${resp.status}`);
  }
  const data = await resp.json();
  return data.task_id;
}

export async function fetchTask(taskId: string) {
  const resp = await fetch(`/api/task/${taskId}`, { headers: headers() });
  if (!resp.ok) {
    throw new Error(`获取任务失败: ${resp.status}`);
  }
  return resp.json();
}

export async function uploadFile(file: File, relpath?: string): Promise<FileMeta> {
  const form = new FormData();
  form.append("file", file);
  if (relpath) form.append("relpath", relpath);
  const resp = await fetch("/api/files", { method: "POST", headers: headers(), body: form });
  if (!resp.ok) {
    throw new Error(`上传失败: ${resp.status}`);
  }
  return resp.json();
}

export async function listFiles(): Promise<FileMeta[]> {
  const resp = await fetch("/api/files", { headers: headers() });
  if (!resp.ok) {
    throw new Error(`获取文件列表失败: ${resp.status}`);
  }
  const data = await resp.json();
  return data.files;
}

export async function deleteFile(fileId: string): Promise<void> {
  await fetch(`/api/files/${fileId}`, { method: "DELETE", headers: headers() });
}

export const fileDownloadUrl = (fileId: string) =>
  `/api/files/${fileId}?session=${encodeURIComponent(sessionId)}`;

export async function listSkills(): Promise<SkillMeta[]> {
  const resp = await fetch("/api/skills", { headers: headers() });
  if (!resp.ok) {
    throw new Error(`获取技能列表失败: ${resp.status}`);
  }
  const data = await resp.json();
  return data.skills;
}
