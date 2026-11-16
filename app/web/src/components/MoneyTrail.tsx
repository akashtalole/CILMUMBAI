import { useEffect, useState } from "react";
import { api, type GraphNode, type Row, type ViewResult } from "../api";
import { formatDate, formatRupees, type Lang } from "../i18n";
import { useLang } from "../lang";
import { Gaps } from "./Gaps";
import { Source } from "./Source";

function details(node: GraphNode, t: ReturnType<typeof useLang>["t"], lang: Lang): string[] {
  const out: string[] = [];
  const title = node.title || node.name;
  if (title) out.push(String(title));
  if (node.ref_no) out.push(`${t.ref}: ${node.ref_no}`);
  if (typeof node.estimated_cost === "number") out.push(`${t.estimated}: ${formatRupees(node.estimated_cost, lang)}`);
  if (typeof node.value === "number") out.push(`${t.value}: ${formatRupees(node.value, lang)}`);
  if (typeof node.amount === "number") out.push(`${t.value}: ${formatRupees(node.amount, lang)}`);
  if (node.due_on) out.push(`${t.due}: ${formatDate(String(node.due_on), lang)}`);
  if (node.from_date && node.to_date)
    out.push(`${t.period}: ${formatDate(String(node.from_date), lang)} – ${formatDate(String(node.to_date), lang)}`);
  if (node.paid_on) out.push(`${t.paidOn}: ${formatDate(String(node.paid_on), lang)}`);
  return out;
}

/** Budget to work to tender to award to contract to contractor to payments, each step with its source. */
export function MoneyTrail({ placeId }: { placeId: string | null }) {
  const { t, lang } = useLang();
  const [result, setResult] = useState<ViewResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!placeId) return;
    setResult(null);
    setError(false);
    api.money(placeId).then(setResult).catch(() => setError(true));
  }, [placeId]);

  if (!placeId) return <p className="hint">{t.pickPlace}</p>;
  if (error) return <p className="notice error">{t.error}</p>;
  if (!result) return <div className="skeleton" aria-label={t.loading} />;
  const works = result.rows.filter((r) => r.hops?.length);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <section aria-live="polite">
      {works.length === 0 && <p className="notice">{t.noMoney}</p>}
      {works.map((w) => (
        <ol key={w.work_id} className="trail">
          {(w.hops as Row[]).map((h) =>
            h.node ? (
              <li key={h.node.id + h.hop} className={`step step-${h.hop}`}>
                <span className="step-label">{t.hops[h.hop] ?? h.hop}</span>
                {details(h.node, t, lang).map((line) => (
                  <span key={line} className="step-line">
                    {line}
                  </span>
                ))}
                {h.hop === "work" && Boolean(h.node.due_on) && !h.node.completed_on && String(h.node.due_on) < today && (
                  <span className="badge warn">{t.overdue}</span>
                )}
                <Source node={h.node} />
              </li>
            ) : null,
          )}
        </ol>
      ))}
      <Gaps gaps={result.gaps} />
    </section>
  );
}
