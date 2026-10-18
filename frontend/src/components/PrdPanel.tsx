import type { PrdEnvelope, VersionMeta } from "../types";

interface Props {
  envelope: PrdEnvelope | null;
  versions: VersionMeta[];
  inline?: boolean;
}

const PRIORITY_ORDER = ["P0", "P1", "P2"] as const;

export default function PrdPanel({ envelope, versions, inline }: Props) {
  const prd = envelope?.data;

  if (!prd) {
    return (
      <div className="prd-empty">
        <div className="prd-empty-mark">✎</div>
        <h3>PRD 尚未生成</h3>
        <p>在左侧描述一个产品想法，Agent 生成的结构化 PRD 会出现在这张草稿纸上。</p>
      </div>
    );
  }

  const changed = new Set(envelope?.changed_sections || []);
  const isChanged = (k: string) => changed.has(k) || changed.has("*");

  return (
    <div className={"prd" + (inline ? " inline" : "")}>
      <div className="prd-head">
        <div className="prd-head-top">
          <h1 className="prd-name">{prd.product_name}</h1>
          <span className="prd-version-chip">v{envelope?.version}</span>
        </div>
        {prd.one_liner && <p className="prd-oneliner">{prd.one_liner}</p>}
        {envelope?.change_summary && (
          <p className="prd-change">
            <span className="prd-change-label">本次变更</span>
            {envelope.change_summary}
          </p>
        )}
      </div>

      {prd.background && (
        <section className={"prd-sec" + (isChanged("background") ? " changed" : "")}>
          <h4>背景与问题</h4>
          <p className="prd-text">{prd.background}</p>
        </section>
      )}

      {prd.goals?.length > 0 && (
        <section className={"prd-sec" + (isChanged("goals") ? " changed" : "")}>
          <h4>目标</h4>
          <ul className="prd-list">
            {prd.goals.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </section>
      )}

      {prd.target_users?.length > 0 && (
        <section className={"prd-sec" + (isChanged("target_users") ? " changed" : "")}>
          <h4>目标用户与画像</h4>
          <div className="personas">
            {prd.target_users.map((p, i) => (
              <div className="persona" key={i}>
                <div className="persona-name">{p.name}</div>
                <div className="persona-desc">{p.description}</div>
                {p.needs?.length > 0 && (
                  <div className="persona-needs">
                    {p.needs.map((n, k) => (
                      <span className="need" key={k}>
                        {n}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {prd.features?.length > 0 && (
        <section className={"prd-sec" + (isChanged("features") ? " changed" : "")}>
          <h4>核心功能 · 按优先级</h4>
          {PRIORITY_ORDER.map((pri) => {
            const items = prd.features.filter((f) => f.priority === pri);
            if (items.length === 0) return null;
            return (
              <div className="feat-group" key={pri}>
                <div className={"feat-pri " + pri.toLowerCase()}>{pri}</div>
                <div className="feat-items">
                  {items.map((f, i) => (
                    <div className="feat" key={i}>
                      <div className="feat-name">{f.name}</div>
                      <div className="feat-desc">{f.description}</div>
                      {f.rationale && <div className="feat-why">依据：{f.rationale}</div>}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {prd.competitors?.length > 0 && (
        <section className={"prd-sec" + (isChanged("competitors") ? " changed" : "")}>
          <h4>竞品分析</h4>
          <div className="comps">
            {prd.competitors.map((c, i) => (
              <div className="comp" key={i}>
                <div className="comp-name">
                  {c.name}
                  {c.source_url && (
                    <a href={c.source_url} target="_blank" rel="noreferrer" className="comp-src">
                      ↗
                    </a>
                  )}
                </div>
                {c.summary && <div className="comp-sum">{c.summary}</div>}
                <div className="comp-cols">
                  {c.strengths?.length > 0 && (
                    <div>
                      <span className="tag good">优势</span>
                      <ul>
                        {c.strengths.map((s, k) => (
                          <li key={k}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {c.weaknesses?.length > 0 && (
                    <div>
                      <span className="tag bad">劣势</span>
                      <ul>
                        {c.weaknesses.map((s, k) => (
                          <li key={k}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {prd.metrics?.length > 0 && (
        <section className={"prd-sec" + (isChanged("metrics") ? " changed" : "")}>
          <h4>成功指标</h4>
          <table className="prd-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>目标</th>
                <th>度量方式</th>
              </tr>
            </thead>
            <tbody>
              {prd.metrics.map((m, i) => (
                <tr key={i}>
                  <td>{m.name}</td>
                  <td className="mono">{m.target}</td>
                  <td>{m.how_to_measure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {prd.milestones?.length > 0 && (
        <section className={"prd-sec" + (isChanged("milestones") ? " changed" : "")}>
          <h4>里程碑</h4>
          <div className="miles">
            {prd.milestones.map((m, i) => (
              <div className="mile" key={i}>
                <div className="mile-phase">{m.phase}</div>
                {m.timeline && <div className="mile-time mono">{m.timeline}</div>}
                {m.deliverables?.length > 0 && (
                  <ul>
                    {m.deliverables.map((d, k) => (
                      <li key={k}>{d}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {prd.risks?.length > 0 && (
        <section className={"prd-sec" + (isChanged("risks") ? " changed" : "")}>
          <h4>风险</h4>
          <ul className="prd-list risk">
            {prd.risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      {prd.open_questions?.length > 0 && (
        <section className={"prd-sec" + (isChanged("open_questions") ? " changed" : "")}>
          <h4>待确认问题</h4>
          <ul className="prd-list open">
            {prd.open_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </section>
      )}

      {versions.length > 0 && (
        <section className="prd-sec versions">
          <h4>版本历史</h4>
          <ol className="ver-list">
            {versions.map((v) => (
              <li key={v.version}>
                <span className="ver-no mono">v{v.version}</span>
                <span className="ver-sum">{v.change_summary || "—"}</span>
                {v.changed_sections?.length > 0 && (
                  <span className="ver-tags">{v.changed_sections.join(" · ")}</span>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
