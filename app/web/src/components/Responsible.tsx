import { useEffect, useState } from "react";
import { api, type GraphNode, type ViewResult } from "../api";
import { formatDate, type Lang } from "../i18n";
import { useLang } from "../lang";
import { Source } from "./Source";
import { Gaps } from "./Gaps";

const ISSUES = ["pothole", "open_manhole", "waterlogging", "incomplete_work"] as const;

function name(node: GraphNode | null | undefined, lang: Lang): string {
  if (!node) return "";
  return (lang === "mr" && node.name_mr) || node.title || node.name || node.code || node.id;
}

/** Who owns this road, which post to complain to, who comes next, and whether a contractor must still repair it. */
export function Responsible({ placeId }: { placeId: string | null }) {
  const { t, lang } = useLang();
  const [issue, setIssue] = useState<(typeof ISSUES)[number]>("pothole");
  const [result, setResult] = useState<ViewResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!placeId) return;
    setResult(null);
    setError(false);
    api.responsible(placeId, issue).then(setResult).catch(() => setError(true));
  }, [placeId, issue]);

  if (!placeId) return <p className="hint">{t.pickPlace}</p>;
  const hop = (h: string) => result?.rows.filter((r) => r.hop === h) ?? [];
  const post = hop("post")[0]?.node;
  const escalation = hop("escalation").map((r) => r.node);
  const liability = hop("under_liability");

  return (
    <section aria-live="polite">
      <fieldset className="chips">
        <legend className="field-label">{t.issue}</legend>
        {ISSUES.map((i) => (
          <label key={i} className={`chip ${issue === i ? "on" : ""}`}>
            <input type="radio" name="issue" value={i} checked={issue === i} onChange={() => setIssue(i)} />
            {t.issues[i]}
          </label>
        ))}
      </fieldset>

      {error && <p className="notice error">{t.error}</p>}
      {!result && !error && <div className="skeleton" aria-label={t.loading} />}

      {result && result.rows.length === 0 && <p className="notice">{t.nothingYet}</p>}
      {result && result.rows.length > 0 && (
        <>
          {liability.length > 0 ? (
            liability.map((row) => (
              <article key={row.work?.id} className="card highlight">
                <h3>{t.liabilityTitle}</h3>
                <p className="lead">
                  {t.liabilityBody(name(row.contractor, lang) || "—", formatDate(String(row.period?.to_date ?? ""), lang))}{" "}
                  <Source node={row.period} />
                </p>
                <p className="meta">
                  {t.liabilityWork}: {name(row.work, lang)} <Source node={row.work} />
                </p>
                {row.contractor && (
                  <p className="meta">
                    {t.hops.contractor}: {name(row.contractor, lang)} <Source node={row.contractor} />
                  </p>
                )}
              </article>
            ))
          ) : (
            <p className="notice">{t.noLiability}</p>
          )}

          {post && (
            <article className="card">
              <p className="eyebrow">{t.complainTo}</p>
              <h3>
                {name(post, lang)} <Source node={post} />
              </h3>
              {escalation.length > 0 && (
                <ol className="chain">
                  {escalation.map((e) => (
                    <li key={e?.id}>
                      <span className="eyebrow">{t.thenTo}</span> {name(e, lang)} <Source node={e} />
                    </li>
                  ))}
                </ol>
              )}
            </article>
          )}

          <dl className="facts">
            {hop("owner").map((r) => (
              <div key={r.node?.id}>
                <dt>{t.owner}</dt>
                <dd>
                  {name(r.node, lang)} <Source node={r.node} />
                </dd>
              </div>
            ))}
            {hop("department").map((r) => (
              <div key={r.node?.id}>
                <dt>{t.department}</dt>
                <dd>
                  {name(r.node, lang)} <Source node={r.node} />
                </dd>
              </div>
            ))}
            {hop("ward").map((r) => (
              <div key={r.node?.id}>
                <dt>{t.ward}</dt>
                <dd>
                  {name(r.node, lang)} <Source node={r.node} />
                </dd>
              </div>
            ))}
          </dl>
          <Gaps gaps={result.gaps} />
        </>
      )}
    </section>
  );
}
