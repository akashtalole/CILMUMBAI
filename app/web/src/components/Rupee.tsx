import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useLang } from "../lang";
import {
  RULE_LABEL,
  citeUrl,
  inr,
  pct,
  rupee,
  type ContractorFull,
  type Flag,
  type Note,
  type PlanItem,
  type Scores,
  type Summary,
  type Trail,
  type WardFull,
} from "../rupee";

// Follow the Rupee (SPEC-040). Where each ward's monsoon road money went, whether the fix held, who answers for it,
// and where the next rupee should go. Every figure links to the dataset row it came from.

type View = "wards" | "contractors" | "audit" | "plan" | "complaint";
const GRADE_COLOR: Record<string, string> = { A: "#2f9e44", B: "#74b816", C: "#f59f00", D: "#f76707", E: "#e03131" };

function Cites({ cites }: { cites: string[] }) {
  return (
    <span className="cites">
      {cites.map((c) => (
        <a key={c} href={citeUrl(c)} target="_blank" rel="noreferrer" className="cite">
          {c}
        </a>
      ))}
    </span>
  );
}

function Grade({ g, score }: { g: string; score?: number }) {
  return (
    <span className="grade" style={{ background: GRADE_COLOR[g] ?? "#868e96" }} title={score !== undefined ? `${score} of 100` : undefined}>
      {g}
    </span>
  );
}

function Bars({ scores }: { scores: Scores }) {
  return (
    <div className="bars">
      {Object.entries(scores).map(([k, v]) => (
        <div key={k} className="bar-row">
          <span className="bar-label">{k}</span>
          <span className="bar">
            <span className="bar-fill" style={{ width: `${v}%`, background: v >= 60 ? "#2f9e44" : v >= 45 ? "#f59f00" : "#e03131" }} />
            <span className="bar-mid" title="50 = as expected for these jobs" />
          </span>
          <span className="bar-num">{v}</span>
        </div>
      ))}
      <p className="meta">50 is what we would expect for the same jobs, methods, rain and ward. Higher is better.</p>
    </div>
  );
}

function NoteText({ note }: { note: Note }) {
  return (
    <div className="note">
      <p>{note.text}</p>
      <p className="meta">{note.by === "template" ? "Written from the figures by a template" : `Written by Claude (${note.by}) and checked: every number matches the figures, no accusations`}</p>
    </div>
  );
}

function Money({ s }: { s: Summary }) {
  return (
    <div className="kpis">
      <div className="kpi">
        <span className="kpi-num">{inr(s.spend_inr)}</span>
        <span className="kpi-label">
          spent of {inr(s.budget_inr)} budgeted · {s.work_orders.toLocaleString("en-IN")} jobs
        </span>
      </div>
      <div className="kpi">
        <span className="kpi-num">{inr(s.failed_spend_inr)}</span>
        <span className="kpi-label">on fixes that failed within 30 days</span>
      </div>
      <div className="kpi warn">
        <span className="kpi-num">{inr(s.money_in_question_inr)}</span>
        <span className="kpi-label">in question: over-billed, duplicate, or paid during the guarantee</span>
      </div>
      <div className="kpi">
        <span className="kpi-num">{s.complaints.open_issues}</span>
        <span className="kpi-label">
          open problems, from {s.complaints.complaints.toLocaleString("en-IN")} complaints in 4 languages
        </span>
      </div>
    </div>
  );
}

function WardMap({ selected, onPick }: { selected: string; onPick: (code: string) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map>();
  const pick = useRef(onPick);
  pick.current = onPick;
  useEffect(() => {
    if (!box.current) return;
    const m = new maplibregl.Map({
      container: box.current,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#e9eef0" } }] },
      center: [72.87, 19.07],
      zoom: 9.6,
      attributionControl: false,
    });
    map.current = m;
    m.on("load", async () => {
      const shapes = await rupee.wardShapes().catch(() => null);
      if (!shapes) return;
      m.addSource("wards", { type: "geojson", data: shapes });
      const bounds = new maplibregl.LngLatBounds();
      for (const f of shapes.features) for (const c of (f.geometry as GeoJSON.Polygon).coordinates?.[0] ?? []) bounds.extend(c as [number, number]);
      if (!bounds.isEmpty()) m.fitBounds(bounds, { padding: 12, duration: 0 });
      const color = ["match", ["get", "grade"], ...Object.entries(GRADE_COLOR).flat(), "#adb5bd"] as unknown as maplibregl.ExpressionSpecification;
      m.addLayer({ id: "fill", type: "fill", source: "wards", paint: { "fill-color": color, "fill-opacity": 0.55 } });
      m.addLayer({ id: "line", type: "line", source: "wards", paint: { "line-color": "#fff", "line-width": 1.2 } });
      m.addLayer({ id: "sel", type: "line", source: "wards", filter: ["==", ["get", "ward_code"], ""], paint: { "line-color": "#18201d", "line-width": 3 } });
      // Labels as HTML, so the map needs no font server.
      for (const f of shapes.features) {
        const ring = (f.geometry as GeoJSON.Polygon).coordinates?.[0];
        if (!ring?.length) continue;
        const [x, y] = ring.reduce(([a, b], [c, d]) => [a + c / ring.length, b + d / ring.length], [0, 0]);
        const el = document.createElement("span");
        el.className = "ward-label";
        el.textContent = String(f.properties?.ward_code ?? "");
        new maplibregl.Marker({ element: el }).setLngLat([x, y]).addTo(m);
        el.addEventListener("click", () => pick.current(el.textContent ?? ""));
      }
      m.on("click", "fill", (e) => {
        const code = e.features?.[0]?.properties?.ward_code as string | undefined;
        if (code) pick.current(code);
      });
      m.on("mouseenter", "fill", () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", "fill", () => (m.getCanvas().style.cursor = ""));
    });
    return () => m.remove();
  }, []);
  useEffect(() => {
    const m = map.current;
    if (m?.getLayer("sel")) m.setFilter("sel", ["==", ["get", "ward_code"], selected]);
  }, [selected]);
  return <div ref={box} className="ward-map" aria-label="Map of wards coloured by grade" />;
}

function FlagRows({ flags, limit = 50 }: { flags: Flag[]; limit?: number }) {
  const [more, setMore] = useState(false);
  const shown = more ? flags : flags.slice(0, limit);
  if (!flags.length) return <p className="meta">Nothing flagged.</p>;
  return (
    <>
      <ul className="flag-list">
        {shown.map((f) => (
          <li key={f.work_order_id + f.rule} className={`flag flag-${f.rule}`}>
            <div className="flag-head">
              <strong>{f.work_order_id}</strong>
              <span className="chip-s">{RULE_LABEL[f.rule] ?? f.rule}</span>
              <span className="flag-amt">{inr(f.amount_inr)}</span>
            </div>
            <p>{f.reason}</p>
            <p className="meta">
              Ward {f.ward_code} · {f.contractor_name} · <Cites cites={f.evidence} />
            </p>
          </li>
        ))}
      </ul>
      {flags.length > limit && (
        <button type="button" className="linkish" onClick={() => setMore(!more)}>
          {more ? "Show fewer" : `Show all ${flags.length}`}
        </button>
      )}
    </>
  );
}

function PlanRows({ items, showWard = false }: { items: PlanItem[]; showWard?: boolean }) {
  if (!items.length) return <p className="meta">No open problems.</p>;
  return (
    <ol className="plan-list">
      {items.map((i) => (
        <li key={i.issue_id} className={i.funded ? "funded" : ""}>
          <div className="flag-head">
            <span className="risk" title="Risk score out of 100">
              {i.risk}
            </span>
            <strong>
              {i.category} · {i.road_name || i.road_id}
              {showWard && ` · ${i.ward_code}`}
            </strong>
            <span className="flag-amt">{i.under_dlp ? "₹0 to BMC" : inr(i.cost_inr)}</span>
          </div>
          <ul className="why">
            {i.why.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          <p className="meta">
            Method: <strong>{i.method}</strong> (fails {pct(i.method_reopen_rate)} of the time)
            {i.cheapest_method !== i.method.replace(/^Call the original contractor under DLP; /, "") && ` rather than ${i.cheapest_method} (cheaper, fails ${pct(i.cheapest_reopen_rate)})`}
            {" · "}
            {i.funded ? "Funded from the remaining budget" : "Not funded yet"} · {i.complaints.length} complaint{i.complaints.length === 1 ? "" : "s"} · <Cites cites={i.evidence.slice(0, 4)} />
          </p>
        </li>
      ))}
    </ol>
  );
}

function SpendTable({ rows, total }: { rows: { name: string; jobs: number; spend_inr: number }[]; total: number }) {
  return (
    <table className="spend">
      <tbody>
        {rows.map((r) => (
          <tr key={r.name}>
            <td>{r.name}</td>
            <td className="num">{r.jobs}</td>
            <td className="num">{inr(r.spend_inr)}</td>
            <td className="spark">
              <span style={{ width: `${(100 * r.spend_inr) / (total || 1)}%` }} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function WardPanel({ code }: { code: string }) {
  const [w, setW] = useState<WardFull | null>(null);
  useEffect(() => {
    setW(null);
    rupee.ward(code).then(setW).catch(() => setW(null));
  }, [code]);
  if (!w) return <p className="meta">Loading ward {code}…</p>;
  const over = w.budget_used > 1;
  return (
    <article className="card">
      <div className="run-head">
        <h3 className="ct">
          Ward {w.ward_code} · {w.ward_name}
        </h3>
        <Grade g={w.grade} score={w.overall} />
      </div>
      <p className="meta">
        {w.office} · {w.zone} · flood-proneness {w.low_lying_index}
      </p>
      <NoteText note={w.note} />
      <div className="budget">
        <div className="budget-bar">
          <span className={over ? "over" : ""} style={{ width: `${Math.min(100, w.budget_used * 100)}%` }} />
        </div>
        <p className="meta">
          {inr(w.spend_inr)} of {inr(w.budget_inr)} ({pct(w.budget_used)}){over ? " — over budget" : ""} · {inr(w.plan.remaining_inr)} left
        </p>
      </div>
      <Bars scores={w.scores} />
      <h4 className="sub-title">Where the money went</h4>
      <SpendTable rows={w.by_contractor} total={w.spend_inr} />
      <SpendTable rows={w.by_work_type} total={w.spend_inr} />
      <p className="meta">
        {pct(w.reopen_rate)} of fixes failed within 30 days ({pct(w.expected_reopen_rate)} expected) · {pct(w.sla_met_rate)} met the SLA ({pct(w.expected_sla_met_rate)} expected) · {inr(w.failed_spend_inr)} spent on failed fixes
      </p>
      <h4 className="sub-title">Next rupee: {w.plan.open_issues} open problems, ranked by risk</h4>
      <p className="meta">
        The remaining budget pays for {w.plan.funded} ({inr(w.plan.funded_cost_inr)}); {w.plan.free_under_dlp} go to the original contractor under DLP at no cost.
      </p>
      <PlanRows items={w.plan.items.slice(0, 10)} />
      <h4 className="sub-title">Flags ({w.flag_list.length})</h4>
      <FlagRows flags={w.flag_list} limit={10} />
    </article>
  );
}

function Wards({ s }: { s: Summary }) {
  const [code, setCode] = useState(() => [...s.wards].sort((a, b) => a.overall - b.overall)[0]?.ward_code ?? "A");
  const sorted = useMemo(() => [...s.wards].sort((a, b) => a.overall - b.overall), [s]);
  return (
    <div className="rupee-grid">
      <div>
        <WardMap selected={code} onPick={setCode} />
        <table className="spend wards">
          <thead>
            <tr>
              <th>Ward</th>
              <th>Grade</th>
              <th className="num">Budget used</th>
              <th className="num">In question</th>
              <th className="num">Overdue</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((w) => (
              <tr key={w.ward_code} className={w.ward_code === code ? "on" : ""} onClick={() => setCode(w.ward_code)}>
                <td>
                  <button type="button" className="linkish" title={w.ward_name}>
                    {w.ward_code}
                  </button>
                </td>
                <td>
                  <Grade g={w.grade} score={w.overall} />
                </td>
                <td className={`num ${w.budget_used > 1 ? "bad" : ""}`}>{pct(w.budget_used)}</td>
                <td className="num">{inr(w.money_in_question_inr)}</td>
                <td className="num">{w.open_overdue_issues}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <WardPanel code={code} />
    </div>
  );
}

function Contractors({ s }: { s: Summary }) {
  const [open, setOpen] = useState<ContractorFull | null>(null);
  return (
    <div className="rupee-grid">
      <div className="cards">
        {s.contractors.map((c) => (
          <button key={c.contractor_id} type="button" className={`card contractor ${open?.contractor_id === c.contractor_id ? "on" : ""}`} onClick={() => rupee.contractor(c.contractor_id).then(setOpen)}>
            <div className="run-head">
              <strong>{c.name}</strong>
              <Grade g={c.grade} score={c.overall} />
            </div>
            <p className="meta">
              {c.jobs} jobs · {inr(c.spend_inr)} · fails {pct(c.reopen_rate)} (exp. {pct(c.expected_reopen_rate)}) · SLA {pct(c.sla_met_rate)} · {c.flags.overbilled.count} over-billed · {c.flags.duplicate.count} duplicates
            </p>
          </button>
        ))}
      </div>
      {open ? (
        <article className="card">
          <div className="run-head">
            <h3 className="ct">{open.name}</h3>
            <Grade g={open.grade} score={open.overall} />
          </div>
          <p className="meta">
            Empanelled since {open.empanelled_since} · works in {open.wards.length} wards · median bill {open.median_bill_vs_rate_card}× the rate card
          </p>
          <NoteText note={open.note} />
          <Bars scores={open.scores} />
          <p className="meta">Billing counts the contractor's own bills: over-billing and duplicates. Paying for a road under its guarantee is counted against the ward that approved it.</p>
          <h4 className="sub-title">Methods</h4>
          <SpendTable rows={open.by_method} total={open.spend_inr} />
          <h4 className="sub-title">Flags ({open.flag_list.length})</h4>
          <FlagRows flags={open.flag_list.filter((f) => f.rule !== "dlp_paid")} limit={15} />
        </article>
      ) : (
        <p className="hint">Pick a contractor to see its scorecard. Scores are fair: each job is compared with what anyone would expect for the same method, weather and ward, and doing more work is not punished.</p>
      )}
    </div>
  );
}

function Audit({ s }: { s: Summary }) {
  const [rule, setRule] = useState("overbilled");
  const [ward, setWard] = useState("");
  const [flags, setFlags] = useState<Flag[] | null>(null);
  useEffect(() => {
    setFlags(null);
    rupee.flags(rule, ward).then((r) => setFlags(r.items));
  }, [rule, ward]);
  return (
    <section>
      <div className="chips">
        {Object.entries(s.flags).map(([r, v]) => (
          <button key={r} type="button" className={`chip ${r === rule ? "on" : ""}`} onClick={() => setRule(r)}>
            {RULE_LABEL[r] ?? r} · {v.count} · {inr(v.amount_inr)}
          </button>
        ))}
        <select value={ward} onChange={(e) => setWard(e.target.value)} aria-label="Ward">
          <option value="">All wards</option>
          {s.wards.map((w) => (
            <option key={w.ward_code} value={w.ward_code}>
              {w.ward_code}
            </option>
          ))}
        </select>
      </div>
      <p className="hint">
        {s.flags[rule]?.label}. Rules are in code with fixed thresholds (over-billed means above {s.thresholds.overbilled_ratio}× the rate card; duplicate means the same road and work within {s.thresholds.duplicate_days} days with no complaint), so anyone can check a flag with the data and a calculator.
        {rule === "repeat_paid" && " This one is a lead to look into, not a finding: it is not counted in the money in question."}
      </p>
      {flags ? <FlagRows flags={flags} /> : <p className="meta">Loading…</p>}
    </section>
  );
}

function Plan({ s }: { s: Summary }) {
  return (
    <section>
      <p className="hint">
        The highest-risk open problems in the city. Risk adds up severity, flooding at that spot (with last season's rain and big tides), traffic and bus routes, road accidents, hospitals and schools that depend on the road, and how many people reported it. Weights:{" "}
        {Object.entries(s.thresholds.plan_weights)
          .map(([k, v]) => `${k} ${Math.round(v * 100)}%`)
          .join(", ")}
        . The method chosen is the one that lasts longest for that kind of problem, not the cheapest.
      </p>
      <PlanRows items={s.top_plan} showWard />
    </section>
  );
}

function Complaint() {
  const { lang } = useLang();
  const [id, setId] = useState("");
  const [got, setGot] = useState<Trail | null>(null);
  const [error, setError] = useState("");
  const look = (cid: string) => {
    setError("");
    rupee
      .complaint(cid, lang)
      .then(setGot)
      .catch(() => {
        setGot(null);
        setError("No complaint with that number.");
      });
  };
  useEffect(() => {
    if (got) look(String(got.complaint.complaint_id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);
  return (
    <section>
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          look(id);
        }}
      >
        <label htmlFor="cid" className="field-label">
          Complaint number (for example BMC25-000013)
        </label>
        <div className="search-row">
          <input id="cid" type="search" value={id} onChange={(e) => setId(e.target.value)} placeholder="BMC25-000013" />
          <button type="submit" className="primary" disabled={id.trim().length < 6}>
            Look up
          </button>
        </div>
        <p className="meta">
          Try:{" "}
          {[
            ["BMC25-000013", "fixed and held"],
            ["BMC25-000047", "fix failed, bill flagged"],
            ["BMC25-000076", "still open"],
          ].map(([x, what]) => (
            <span key={x} className="example">
              <button type="button" className="linkish" onClick={() => (setId(x), look(x))}>
                {x}
              </button>{" "}
              ({what}){" "}
            </span>
          ))}
        </p>
      </form>
      {error && <p className="notice error">{error}</p>}
      {got && (
        <article className="card">
          <p className="lead">{got.answer}</p>
          <p className="meta">
            {String(got.complaint.state)} · ward {String(got.complaint.ward_code || "?")} ({String(got.complaint.ward_from)}) · {String(got.complaint.category)} · road {String(got.complaint.road_id || "?")} ({String(got.complaint.road_from)}) · <Cites cites={[String(got.complaint.cite), ...(got.work_order ? [got.work_order.cite] : [])]} />
          </p>
        </article>
      )}
    </section>
  );
}

export function Rupee() {
  const [s, setS] = useState<Summary | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<View>("wards");
  useEffect(() => {
    rupee
      .summary()
      .then(setS)
      .catch((e: { status?: number }) => setError(e.status === 503 ? "Follow the Rupee has not been built on this server yet (hishob rupee build)." : "Could not load Follow the Rupee."));
  }, []);
  if (error) return <p className="notice error">{error}</p>;
  if (!s) return <p className="meta">Loading…</p>;
  const views: [View, string][] = [
    ["wards", "Wards"],
    ["contractors", "Contractors"],
    ["audit", "Audit flags"],
    ["plan", "Next rupee"],
    ["complaint", "My complaint"],
  ];
  return (
    <section className="rupee">
      <h2 className="section-title">Mumbai monsoon road repairs, June to October 2025</h2>
      <p className="demo-banner">Synthetic data from the Claude Impact Lab Mumbai challenge. No real contractors or citizens.</p>
      <Money s={s} />
      <nav className="tabs sub" role="tablist">
        {views.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={view === id} className={view === id ? "on" : ""} onClick={() => setView(id)}>
            {label}
          </button>
        ))}
      </nav>
      {view === "wards" && <Wards s={s} />}
      {view === "contractors" && <Contractors s={s} />}
      {view === "audit" && <Audit s={s} />}
      {view === "plan" && <Plan s={s} />}
      {view === "complaint" && <Complaint />}
    </section>
  );
}
