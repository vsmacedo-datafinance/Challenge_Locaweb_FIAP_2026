export type Tone = "default" | "cyan" | "red" | "amber";
export type RiskTone = "red" | "amber" | "cyan";
export type Estado = "ok" | "atento" | "alerta";

export interface KpiCard {
  label: string;
  value: string;
  sub: string;
  tone: Tone;
  highlight: boolean;
}

export interface RiskItemData {
  rank: number;
  incident_id: string;
  probability: number;
  tone: RiskTone;
  team?: string | null;
  asset?: string | null;
  description?: string | null;
}

export interface ChroninhoMessageData {
  estado: Estado;
  estado_label: string;
  message: string;
}

export interface ExplainabilityFactor {
  factor: string;
  pct: string;
}

export interface ExplainabilityData {
  incident_id: string;
  increasing: ExplainabilityFactor[];
  decreasing: ExplainabilityFactor[];
  summary_note: string;
}

export interface SchedulePlanRow {
  day: string;
  forecast: number;
  suggestion: string;
  tone: "default" | "amber";
}

export interface InsightData {
  tone: "amber" | "cyan" | "red";
  text: string;
}

export interface ModelComparisonRow {
  model: string;
  pr_auc: string;
  bar_pct: number;
  tone: "red" | "gray";
  note: string;
}

export interface PrAucGrowthPoint {
  period: string;
  value: string;
}

export interface VolumeMae {
  p2: string;
  p3: string;
}

export interface OverviewTabData {
  chroninho: ChroninhoMessageData;
  kpis: KpiCard[];
  d1_callout: string;
  top_risks: RiskItemData[];
}

export interface ForecastTabData {
  chroninho: ChroninhoMessageData;
  kpis: KpiCard[];
  schedule_plan: SchedulePlanRow[];
}

export interface RiskTabData {
  chroninho: ChroninhoMessageData;
  queue: RiskItemData[];
  explainability: ExplainabilityData;
  kpis: KpiCard[];
}

export interface TrendsTabData {
  chroninho: ChroninhoMessageData;
  kpis: KpiCard[];
  insights: InsightData[];
}

export interface ResultsTabData {
  chroninho: ChroninhoMessageData;
  model_comparison: ModelComparisonRow[];
  comparison_insight: string;
  pr_auc_growth: PrAucGrowthPoint[];
  growth_insight: string;
  volume_mae: VolumeMae;
  engineering_rigor: string[];
  scientific_honesty: string[];
  footer_note: string;
}

export interface DashboardResponse {
  updated_at_label: string;
  overview: OverviewTabData;
  forecast: ForecastTabData;
  risk: RiskTabData;
  trends: TrendsTabData;
  results: ResultsTabData;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
}
