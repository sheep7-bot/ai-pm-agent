import type { SessionMeta } from "../types";

interface Props {
  sessions: SessionMeta[];
  currentId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export default function Sidebar({ sessions, currentId, busy, onSelect, onNew }: Props) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">PRD</span>
        <span className="brand-slash">/</span>
        <span className="brand-os">OS</span>
      </div>
      <div className="brand-sub">AI 产品经理 · 需求 → PRD</div>

      <button className="new-btn" onClick={onNew} disabled={busy}>
        <span className="plus">＋</span> 新的产品想法
      </button>

      <div className="index-label">会话索引 · {sessions.length}</div>
      <nav className="session-list">
        {sessions.map((s, i) => (
          <button
            key={s.id}
            className={"session-item" + (s.id === currentId ? " active" : "")}
            style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}
            onClick={() => onSelect(s.id)}
            disabled={busy}
          >
            <span className="session-num">{String(i + 1).padStart(2, "0")}</span>
            <span className="session-title">{s.title}</span>
          </button>
        ))}
        {sessions.length === 0 && <div className="empty-hint">还没有会话，写下第一个产品想法吧。</div>}
      </nav>

      <div className="sidebar-foot">多轮对话 · 竞品调研 · 版本化 PRD</div>
    </aside>
  );
}
