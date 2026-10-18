import { useEffect, useRef, useState } from "react";
import type { Message, StepEvent } from "../types";
import AgentSteps from "./AgentSteps";
import PrdPanel from "./PrdPanel";

interface Props {
  messages: Message[];
  streaming: string;
  flow: StepEvent[];
  busy: boolean;
  title: string;
  health: { llm_enabled: boolean; search_enabled: boolean } | null;
  onSend: (text: string) => void;
}

const SUGGESTIONS = [
  "做一个给宠物主人的遛狗社交 App，能找附近的遛狗搭子",
  "为一二线城市独居青年做一个「一人食」智能菜谱 App",
  "做一个面向中小电商的 AI 客服 Agent 后台",
];

export default function Chat({ messages, streaming, flow, busy, title, health, onSend }: Props) {
  const [text, setText] = useState("");
  const threadRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true); // 是否"粘底"：只有贴底时才自动滚动，避免跟用户抢滚轮

  const onScroll = () => {
    const el = threadRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };

  useEffect(() => {
    const el = threadRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [messages.length, streaming, flow.length, busy]);

  const submit = () => {
    const t = text.trim();
    if (!t || busy) return;
    stickRef.current = true; // 主动发送时回到底部
    onSend(t);
    setText("");
  };

  const sendSuggestion = (s: string) => {
    stickRef.current = true;
    onSend(s);
  };

  return (
    <section className="chat">
      <header className="chat-head">
        <div>
          <div className="chat-title">{title || "新的产品想法"}</div>
          <div className="chat-sub">输入产品想法，Agent 将规划 → 调研 → 生成 PRD</div>
        </div>
        <div className="health">
          <span className={"hdot " + (health?.llm_enabled ? "on" : "off")} /> LLM
          <span className={"hdot " + (health?.search_enabled ? "on" : "off")} /> 搜索
        </div>
      </header>

      <div className="thread" ref={threadRef} onScroll={onScroll} tabIndex={0}>
        <div className="thread-inner">
          {messages.length === 0 && !busy && (
            <div className="welcome">
              <h2>
                把一句<span className="em">产品想法</span>，<br />
                变成一个<span className="em">结构化 PRD</span>。
              </h2>
              <p className="welcome-desc">
                Agent 会先做需求分析、规划任务，调用竞品搜索与知识库工具，再生成可编辑、可版本化的 PRD。
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => sendSuggestion(s)} disabled={busy}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div className="msg user" key={m.id ?? i} style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}>
                <div className="bubble user-bubble">{m.content}</div>
              </div>
            ) : (
              <div className="msg bot" key={m.id ?? i} style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}>
                <div className="avatar">PM</div>
                <div className="bot-body">
                  <AgentSteps events={m.events || []} />
                  {m.content && <div className="bubble bot-bubble">{m.content}</div>}
                  {m.prd?.data && <PrdPanel envelope={m.prd} versions={[]} inline />}
                </div>
              </div>
            )
          )}

          {busy && (
            <div className="msg bot">
              <div className="avatar">PM</div>
              <div className="bot-body">
                <AgentSteps events={flow} running />
                {streaming ? (
                  <div className="bubble bot-bubble">
                    {streaming}
                    <span className="caret" />
                  </div>
                ) : flow.length === 0 ? (
                  <div className="bubble bot-bubble">
                    <span className="thinking">
                      <i /> <i /> <i /> 正在思考
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="composer">
        <div className="composer-inner">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="描述你的产品想法，例如：做一个帮助大学生管理时间的 App…"
            rows={2}
            disabled={busy}
          />
          <button className="send-btn" onClick={submit} disabled={busy || !text.trim()}>
            {busy ? "生成中" : "发送 ↗"}
          </button>
        </div>
      </div>
    </section>
  );
}
