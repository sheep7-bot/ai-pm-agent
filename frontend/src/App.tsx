import { useEffect, useRef, useState } from "react";
import Chat from "./components/Chat";
import Sidebar from "./components/Sidebar";
import { getHealth, getPrd, getSession, listSessions, streamChat } from "./api";
import type { Message, PRD, PrdEnvelope, SessionMeta, StepEvent } from "./types";

export default function App() {
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [sid, setSid] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [flow, setFlow] = useState<StepEvent[]>([]);
  const [streaming, setStreaming] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<{ llm_enabled: boolean; search_enabled: boolean } | null>(null);

  const sidRef = useRef<string | null>(null);
  const streamRef = useRef("");
  const flowRef = useRef<StepEvent[]>([]);
  const prdRef = useRef<PrdEnvelope | null>(null);

  const refreshSessions = () => {
    listSessions().then(setSessions).catch(() => {});
  };

  useEffect(() => {
    refreshSessions();
    getHealth().then(setHealth).catch(() => {});
  }, []);

  const selectSession = async (id: string) => {
    if (busy) return;
    setSid(id);
    sidRef.current = id;
    try {
      const detail = await getSession(id);
      const msgs: Message[] = detail.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        events: m.events || [],
      }));
      // 把该会话最新的 PRD 挂到最后一条助手消息上
      const env = await getPrd(id);
      if (env.version > 0 && env.data) {
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === "assistant") {
            msgs[i].prd = env;
            break;
          }
        }
      }
      setMessages(msgs);
      const lastBot = [...msgs].reverse().find((m) => m.role === "assistant");
      setFlow(lastBot?.events || []);
      flowRef.current = lastBot?.events || [];
      setStreaming("");
      streamRef.current = "";
    } catch {
      /* ignore */
    }
  };

  const newChat = () => {
    if (busy) return;
    setSid(null);
    sidRef.current = null;
    setMessages([]);
    setFlow([]);
    flowRef.current = [];
    setStreaming("");
    streamRef.current = "";
    prdRef.current = null;
  };

  const onSend = async (text: string) => {
    if (busy) return;
    setMessages((m) => [...m, { id: -Date.now(), role: "user", content: text, events: [] }]);
    setBusy(true);
    setStreaming("");
    streamRef.current = "";
    setFlow([]);
    flowRef.current = [];
    prdRef.current = null;

    try {
      await streamChat(
        { session_id: sidRef.current ?? undefined, message: text },
        {
          session: (d) => {
            sidRef.current = d.session_id;
            setSid(d.session_id);
          },
          step: (d) => {
            flowRef.current = [...flowRef.current, d];
            setFlow(flowRef.current);
          },
          prd: (d) => {
            prdRef.current = {
              version: d.version,
              data: d.data as PRD,
              change_summary: d.change_summary,
              changed_sections: d.changed_sections,
            };
          },
          message_delta: (d) => {
            streamRef.current += d.text;
            setStreaming(streamRef.current);
          },
          done: () => {
            const finalText = streamRef.current;
            const finalFlow = flowRef.current;
            const finalPrd = prdRef.current;
            setMessages((m) => [
              ...m,
              {
                id: Date.now(),
                role: "assistant",
                content: finalText || "（无文字回复）",
                events: finalFlow,
                prd: finalPrd,
              },
            ]);
            setStreaming("");
            streamRef.current = "";
            setBusy(false);
            refreshSessions();
          },
          error: (d) => {
            setMessages((m) => [
              ...m,
              { id: Date.now(), role: "assistant", content: "⚠ 出错了：" + d.message, events: [] },
            ]);
            setBusy(false);
          },
        }
      );
    } catch (e) {
      setMessages((m) => [
        ...m,
        { id: Date.now(), role: "assistant", content: "⚠ 请求失败：" + (e as Error).message, events: [] },
      ]);
      setBusy(false);
    }
  };

  const currentTitle = sessions.find((s) => s.id === sid)?.title || "";

  return (
    <div className="app">
      <div className="grain" aria-hidden />
      <Sidebar sessions={sessions} currentId={sid} busy={busy} onSelect={selectSession} onNew={newChat} />
      <Chat
        messages={messages}
        streaming={streaming}
        flow={flow}
        busy={busy}
        title={currentTitle}
        health={health}
        onSend={onSend}
      />
    </div>
  );
}
