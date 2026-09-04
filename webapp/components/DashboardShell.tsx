"use client";

import * as Tabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";
import ChroninhoCard from "./ChroninhoCard";
import KpiGrid from "./KpiGrid";
import RiskRadar from "./RiskRadar";
import ExplainabilityPanel from "./ExplainabilityPanel";
import SchedulePlanTable from "./SchedulePlanTable";
import InsightList from "./InsightList";
import ModelComparisonTable from "./ModelComparisonTable";
import NoteBox from "./NoteBox";
import TabNav from "./TabNav";
import VolumeForecastChart from "./charts/VolumeForecastChart";
import WeeklyForecastBars from "./charts/WeeklyForecastBars";
import CeilingTrendChart from "./charts/CeilingTrendChart";
import PrAucGrowthChart from "./charts/PrAucGrowthChart";
import { renderBold } from "@/lib/boldText";
import type { DashboardResponse } from "@/lib/types";

function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-chronos border border-line bg-panel p-4 ${className}`}>{children}</div>;
}

function CardHeading({ title, sub }: { title: string; sub: string }) {
  return (
    <>
      <h3 className="text-[0.9rem] font-semibold">{title}</h3>
      <p className="mb-3 text-[0.73rem] text-mut">{sub}</p>
    </>
  );
}

export default function DashboardShell({ data }: { data: DashboardResponse }) {
  const topRiskIncident = data.risk.queue[0];
  const probabilityLabel = topRiskIncident ? `${Math.round(topRiskIncident.probability * 100)}%` : "";

  return (
    <Tabs.Root defaultValue="s1">
      <TabNav />

      {/* ================= 1. VISÃO GERAL ================= */}
      <Tabs.Content value="s1" className="mx-auto max-w-[1220px] px-6 py-6">
        <ChroninhoCard message={data.overview.chroninho} />
        <KpiGrid kpis={data.overview.kpis} />

        <div className="mt-3 grid gap-3 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeading title="Volume: realizado e previsto" sub="Últimos 14 dias + horizonte de 7 dias com faixa de confiança" />
            <VolumeForecastChart d1Callout={data.overview.d1_callout} />
            <div className="mt-2 flex flex-wrap gap-4 text-[0.7rem] text-mut">
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-txt align-[-1px]" />
                Realizado
              </span>
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-cyan align-[-1px]" />
                Previsão Chronos
              </span>
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-cyan/30 align-[-1px]" />
                Confiança 90%
              </span>
            </div>
          </Card>

          <Card>
            <CardHeading title="Radar de risco do dia" sub="Os 5 chamados com maior probabilidade de violação" />
            <RiskRadar items={data.overview.top_risks} compact />
            <p className="mt-3 text-left text-[0.68rem] text-mut2">
              Cada score sai com o motivo. Veja a aba Risco e explicabilidade.
            </p>
          </Card>
        </div>
      </Tabs.Content>

      {/* ================= 2. PREVISÃO ================= */}
      <Tabs.Content value="s2" className="mx-auto max-w-[1220px] px-6 py-6">
        <ChroninhoCard message={data.forecast.chroninho} />
        <KpiGrid kpis={data.forecast.kpis} />

        <div className="mt-3 grid gap-3 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeading title="Horizonte D+1 a D+7 por prioridade" sub="Previsão bottom-up: cada série com seu próprio modelo" />
            <WeeklyForecastBars />
            <div className="mt-2 flex gap-4 text-[0.7rem] text-mut">
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-red align-[-1px]" />
                P2 · alta
              </span>
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-cyan align-[-1px]" />
                P3 · média
              </span>
            </div>
          </Card>

          <Card>
            <CardHeading title="Plano de escala sugerido" sub="A previsão traduzida em decisão de plantão" />
            <SchedulePlanTable rows={data.forecast.schedule_plan} />
            <p className="mt-3 text-left text-[0.68rem] text-mut2">
              Modelos revalidados a cada re-treino mensal, com previsões sempre não negativas.
            </p>
          </Card>
        </div>
      </Tabs.Content>

      {/* ================= 3. RISCO + SHAP ================= */}
      <Tabs.Content value="s3" className="mx-auto max-w-[1220px] px-6 py-6">
        <ChroninhoCard message={data.risk.chroninho} />

        <div className="grid gap-3 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeading title="Fila de atenção do dia" sub="Chamados abertos ordenados pela probabilidade de violação" />
            <RiskRadar items={data.risk.queue} />
          </Card>

          <ExplainabilityPanel data={data.risk.explainability} probabilityLabel={probabilityLabel} />
        </div>

        <div className="mt-3">
          <KpiGrid kpis={data.risk.kpis} />
        </div>
      </Tabs.Content>

      {/* ================= 4. TENDÊNCIAS ================= */}
      <Tabs.Content value="s4" className="mx-auto max-w-[1220px] px-6 py-6">
        <ChroninhoCard message={data.trends.chroninho} />
        <KpiGrid kpis={data.trends.kpis} />

        <div className="mt-3 grid gap-3 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeading title="Volume semanal elegível vs. teto contratual" sub="Linha tracejada = ritmo compatível com a meta anual" />
            <CeilingTrendChart />
            <div className="mt-2 flex gap-4 text-[0.7rem] text-mut">
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-txt align-[-1px]" />
                Volume semanal
              </span>
              <span>
                <i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-amber align-[-1px]" />
                Ritmo da meta
              </span>
            </div>
          </Card>

          <Card>
            <CardHeading title="Insights que os dados entregaram" sub="Achados de gestão, além dos modelos" />
            <InsightList insights={data.trends.insights} />
          </Card>
        </div>
      </Tabs.Content>

      {/* ================= 5. RESULTADOS ================= */}
      <Tabs.Content value="s5" className="mx-auto max-w-[1220px] px-6 py-6">
        <ChroninhoCard message={data.results.chroninho} />

        <div className="grid gap-3 lg:grid-cols-[1.55fr_1fr]">
          <Card>
            <CardHeading
              title="Detecção de risco: comparação entre modelos"
              sub="PR-AUC médio nos 3 períodos de teste, a métrica certa para um alvo de 0,95%"
            />
            <ModelComparisonTable rows={data.results.model_comparison} />
            <div className="mt-3">
              <NoteBox icon="i" tone="cyan">
                {renderBold(data.results.comparison_insight)}
              </NoteBox>
            </div>
          </Card>

          <Card>
            <CardHeading title="O modelo melhora com o tempo" sub="PR-AUC do CatBoost por período de teste, conforme o histórico cresce" />
            <PrAucGrowthChart data={data.results.pr_auc_growth} />
            <div className="mt-1.5">
              <NoteBox icon="↗" tone="red">
                {renderBold(data.results.growth_insight)}
              </NoteBox>
            </div>
          </Card>
        </div>

        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <Card>
            <CardHeading title="Previsão de volume" sub="Erro médio absoluto por dia (validação)" />
            <div className="py-1.5">
              <div className="font-sora text-[1.85rem] font-extrabold text-cyan">{data.results.volume_mae.p2}</div>
              <div className="text-[0.7rem] text-mut2">chamados/dia em P2 · modelo com sazonalidade e calendário</div>
            </div>
            <div className="py-1.5">
              <div className="font-sora text-[1.85rem] font-extrabold text-cyan">{data.results.volume_mae.p3}</div>
              <div className="text-[0.7rem] text-mut2">
                chamados/dia em P3 · sazonalidade semanal forte capturada pelo próprio modelo
              </div>
            </div>
          </Card>

          <Card>
            <CardHeading title="Rigor de engenharia" sub="O que sustenta os números" />
            <div className="flex flex-col gap-1.5">
              {data.results.engineering_rigor.map((item) => (
                <NoteBox key={item} icon="✓" tone="cyan">
                  {renderBold(item)}
                </NoteBox>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeading title="Honestidade científica" sub="O que testamos e descartamos com evidência" />
            <div className="flex flex-col gap-1.5">
              {data.results.scientific_honesty.map((item) => (
                <NoteBox key={item} icon="×" tone="amber">
                  {renderBold(item)}
                </NoteBox>
              ))}
            </div>
          </Card>
        </div>

        <div className="mt-6 text-center text-[0.68rem] text-mut2">{data.results.footer_note}</div>
      </Tabs.Content>
    </Tabs.Root>
  );
}
