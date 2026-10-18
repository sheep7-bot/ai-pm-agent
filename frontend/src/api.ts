import type { PrdEnvelope, SessionMeta, StepEvent, VersionMeta } from "./types";

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return (await res.json()) as T;
}

export const listSessions = () => getJSON<SessionMeta[]>("/api/sessions");
export const getPrd = (sid: string) => getJSON<PrdEnvelope>(`/api/sessions/${sid}/prd`);
export const getVersions = (sid: string) => getJSON<VersionMeta[]>(`/api/sessions/${sid}/prd/versions`);
export const getHealth = () =>
  getJSON<{ status: string; llm_enabled: boolean; search_enabled: boolean }>("/api/health");

export interface SessionDetail {
  id: string;
  title: string;
  messages: Array<{ id: number; role: "user" | "assistant"; content: string; events: StepEvent[] }>;
}

export const getSession = (sid: string) => getJSON<SessionDetail>(`/api/sessions/${sid}`);

export interface ChatHandlers {
  session?: (d: { session_id: string; mode: string }) => void;
  step?: (d: StepEvent) => void;
  prd?: (d: { version: number; data: unknown; change_summary: string; changed_sections: string[] }) => void;
  message_delta?: (d: { text: string }) => void;
  done?: (d: { session_id: string; mode: string }) => void;
  error?: (d: { message: string }) => void;
}

/**
 * 用 fetch + ReadableStream 手动解析 SSE（因为需要 POST）。
 */
export async function streamChat(
  body: { session_id?: string; message: string },
  handlers: ChatHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.body) throw new Error("no response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  const dispatch = (raw: string) => {
    const evMatch = raw.match(/^event:\s*(.+)$/m);
    const dataMatch = raw.match(/^data:\s*(.+)$/m);
    if (!evMatch || !dataMatch) return;
    const name = evMatch[1].trim() as keyof ChatHandlers;
    const payload = JSON.parse(dataMatch[1]);
    handlers[name]?.(payload as never);
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      dispatch(buf.slice(0, idx));
      buf = buf.slice(idx + 2);
    }
  }
}
