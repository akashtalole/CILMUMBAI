// Follow the Rupee (SPEC-040): types and calls for the /rupee endpoints. The dataset is synthetic.

export interface Scores {
  durability: number;
  speed: number;
  billing: number;
  backlog?: number;
}
export interface RuleCount {
  count: number;
  amount_inr: number;
  label?: string;
}
export interface Note {
  text: string;
  by: string;
  problems: string[];
}
export interface Flag {
  work_order_id: string;
  rule: string;
  reason: string;
  amount_inr: number;
  ward_code: string;
  contractor_id: string;
  contractor_name: string;
  road_id: string;
  evidence: string[];
}
export interface PlanItem {
  issue_id: string;
  ward_code: string;
  road_id: string;
  road_name: string;
  category: string;
  complaints: string[];
  first_reported: string;
  risk: number;
  parts: Record<string, number>;
  why: string[];
  method: string;
  method_reopen_rate: number;
  cheapest_method: string;
  cheapest_reopen_rate: number;
  cost_inr: number;
  under_dlp: boolean;
  funded: boolean;
  evidence: string[];
}
export interface Spend {
  name: string;
  jobs: number;
  spend_inr: number;
}
export interface WardBrief {
  ward_code: string;
  ward_name: string;
  zone: string;
  grade: string;
  overall: number;
  scores: Scores;
  budget_inr: number;
  spend_inr: number;
  budget_used: number;
  failed_spend_inr: number;
  money_in_question_inr: number;
  open_overdue_issues: number;
  jobs: number;
  low_lying_index: number;
}
export interface WardPlan {
  remaining_inr: number;
  open_issues: number;
  funded: number;
  funded_cost_inr: number;
  unfunded_cost_inr: number;
  free_under_dlp: number;
  items: PlanItem[];
}
export interface WardFull extends WardBrief {
  office: string;
  note: Note;
  flags: Record<string, RuleCount>;
  reopen_rate: number;
  expected_reopen_rate: number;
  sla_met_rate: number;
  expected_sla_met_rate: number;
  by_contractor: Spend[];
  by_method: Spend[];
  by_work_type: Spend[];
  plan: WardPlan;
  flag_list: Flag[];
}
export interface ContractorBrief {
  contractor_id: string;
  name: string;
  grade: string;
  overall: number;
  scores: Scores;
  jobs: number;
  spend_inr: number;
  reopen_rate: number;
  expected_reopen_rate: number;
  sla_met_rate: number;
  expected_sla_met_rate: number;
  money_in_question_inr: number;
  flags: Record<string, RuleCount>;
}
export interface ContractorFull extends ContractorBrief {
  note: Note;
  empanelled_since: string;
  wards: string[];
  median_bill_vs_rate_card: number;
  by_method: Spend[];
  flag_list: Flag[];
}
export interface Summary {
  work_orders: number;
  spend_inr: number;
  budget_inr: number;
  failed_spend_inr: number;
  money_in_question_inr: number;
  flags: Record<string, RuleCount>;
  complaints: { complaints: number; issues: number; open_issues: number; by_state: Record<string, number>; ward_inferred: number; category_corrected: number; languages: Record<string, number> };
  thresholds: { overbilled_ratio: number; duplicate_days: number; plan_weights: Record<string, number> };
  written_by: Record<string, number>;
  wards: WardBrief[];
  contractors: ContractorBrief[];
  top_plan: PlanItem[];
}
export interface Trail {
  answer: string;
  lang: string;
  complaint: Record<string, string | number>;
  work_order: Record<string, string> | null;
  flags: Flag[];
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) {
    let detail = r.statusText;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw Object.assign(new Error(String(detail)), { status: r.status });
  }
  return r.json() as Promise<T>;
}
const q = encodeURIComponent;

export const rupee = {
  summary: () => get<Summary>("/rupee/summary"),
  ward: (code: string) => get<WardFull>(`/rupee/ward?code=${q(code)}`),
  contractor: (id: string) => get<ContractorFull>(`/rupee/contractor?id=${q(id)}`),
  flags: (rule: string, ward: string) => get<{ total: number; items: Flag[] }>(`/rupee/flags?limit=1000${rule ? `&rule=${q(rule)}` : ""}${ward ? `&ward=${q(ward)}` : ""}`),
  complaint: (id: string, lang: string) => get<Trail>(`/rupee/complaint?id=${q(id)}&lang=${lang}`),
  wardShapes: () => get<GeoJSON.FeatureCollection>("/rupee/wards.geojson"),
};

export const inr = (n: number) => {
  const sign = n < 0 ? "-" : "";
  const a = Math.abs(n);
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(1)} lakh`;
  return `${sign}₹${Math.round(a).toLocaleString("en-IN")}`;
};
export const pct = (x: number) => `${Math.round(x * 100)}%`;

// Evidence is a file and line in the dataset; it opens on GitHub at that line.
const REPO = (import.meta.env.VITE_DATASET_URL as string | undefined) ?? "https://github.com/akashtalole/CILMUMBAI/blob/main/app/datasets/follow-the-rupee/data/";
export const citeUrl = (cite: string) => {
  const [file, line] = cite.split("#");
  return `${REPO}${file}?plain=1#${line}`;
};

export const RULE_LABEL: Record<string, string> = {
  overbilled: "Over-billed",
  duplicate: "Duplicate bill",
  dlp_paid: "Paid during guarantee (DLP)",
  repeat_paid: "Failed fix paid again",
};
