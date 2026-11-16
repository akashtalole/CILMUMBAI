import type { Gap } from "../api";
import { useLang } from "../lang";

/** Records the platform does not hold, and who does: each one is something a resident can ask for under RTI. */
export function Gaps({ gaps }: { gaps: Gap[] }) {
  const { t } = useLang();
  if (!gaps.length) return null;
  return (
    <aside className="gaps">
      <h4>{t.notInRecords}</h4>
      <ul>
        {gaps.map((g) => (
          <li key={g.hop + g.record_needed}>
            <strong>{g.record_needed}</strong>
            <span className="meta">
              {t.holder}: {g.holder} · {t.askByRti}
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
