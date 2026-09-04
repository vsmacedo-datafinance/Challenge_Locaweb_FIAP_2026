import json
import os
import time
from typing import Literal

import anthropic
from anthropic import beta_tool
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Chronos API")

MODEL = "claude-sonnet-5"


class KpiCard(BaseModel):
    label: str
    value: str
    sub: str
    tone: Literal["default", "cyan", "red", "amber"] = "default"
    highlight: bool = False


class RiskItem(BaseModel):
    rank: int
    incident_id: str
    probability: float
    tone: Literal["red", "amber", "cyan"]
    team: str | None = None
    asset: str | None = None
    description: str | None = None


class ChroninhoMessage(BaseModel):
    estado: Literal["ok", "atento", "alerta"]
    estado_label: str
    message: str


class ExplainabilityFactor(BaseModel):
    factor: str
    pct: str


class Explainability(BaseModel):
    incident_id: str
    increasing: list[ExplainabilityFactor]
    decreasing: list[ExplainabilityFactor]
    summary_note: str


class SchedulePlanRow(BaseModel):
    day: str
    forecast: int
    suggestion: str
    tone: Literal["default", "amber"] = "default"


class Insight(BaseModel):
    tone: Literal["amber", "cyan", "red"]
    text: str


class ModelComparisonRow(BaseModel):
    model: str
    pr_auc: str
    bar_pct: int
    tone: Literal["red", "gray"]
    note: str


class PrAucGrowthPoint(BaseModel):
    period: str
    value: str


class VolumeMae(BaseModel):
    p2: str
    p3: str


class OverviewTab(BaseModel):
    chroninho: ChroninhoMessage
    kpis: list[KpiCard]
    d1_callout: str
    top_risks: list[RiskItem]


class ForecastTab(BaseModel):
    chroninho: ChroninhoMessage
    kpis: list[KpiCard]
    schedule_plan: list[SchedulePlanRow]


class RiskTab(BaseModel):
    chroninho: ChroninhoMessage
    queue: list[RiskItem]
    explainability: Explainability
    kpis: list[KpiCard]


class TrendsTab(BaseModel):
    chroninho: ChroninhoMessage
    kpis: list[KpiCard]
    insights: list[Insight]


class ResultsTab(BaseModel):
    chroninho: ChroninhoMessage
    model_comparison: list[ModelComparisonRow]
    comparison_insight: str
    pr_auc_growth: list[PrAucGrowthPoint]
    growth_insight: str
    volume_mae: VolumeMae
    engineering_rigor: list[str]
    scientific_honesty: list[str]
    footer_note: str


class DashboardResponse(BaseModel):
    updated_at_label: str
    overview: OverviewTab
    forecast: ForecastTab
    risk: RiskTab
    trends: TrendsTab
    results: ResultsTab


def carregar_modelo_catboost():
    """TODO (fora de escopo neste MVP): carregar o .cbm real treinado no
    notebook 05_Catboost e substituir os dados mockados abaixo por
    inferência real. Ver README do repo para o caminho do artefato.

    ATENÇÃO: `catboost` foi removido de requirements.txt porque, sozinho
    (com numpy/scipy), passa de 587MB e estoura o limite de 500MB do
    Vercel. Antes de implementar isto, resolver o tamanho do bundle
    (função Python separada, carregar o modelo de storage externo, etc.)."""
    raise NotImplementedError("Modelo CatBoost real ainda não conectado — API usa dados mockados.")


def _mock_dashboard() -> DashboardResponse:
    return DashboardResponse(
        updated_at_label="hoje, 06:00",
        overview=OverviewTab(
            chroninho=ChroninhoMessage(
                estado="atento",
                estado_label="Atento",
                message=(
                    "Bom dia, plantão! Para amanhã prevejo **33 chamados elegíveis**, cerca de "
                    "**38% acima da média** das últimas terças, puxados pela pressão acumulada na "
                    "fila do Team14. Já separei os **10 chamados abertos com maior risco de violar "
                    "o OLA**. Historicamente, verificando esses 10, chegamos antes em **7 de cada 10 "
                    "violações**."
                ),
            ),
            kpis=[
                KpiCard(label="Previsão de amanhã (D+1)", value="24", sub="chamados elegíveis, P2 + P3", tone="cyan"),
                KpiCard(label="Próximos 7 dias (W+1)", value="168", sub="intervalo de confiança 90%: 23 a 464", tone="cyan"),
                KpiCard(label="Chamados em risco agora", value="10", sub="acima do limiar de decisão (0,21)", tone="red", highlight=True),
                KpiCard(label="Teto contratual 2025", value="125%", sub="volume elegível vs. meta anual", tone="amber"),
            ],
            d1_callout="D+1: 24",
            top_risks=[
                RiskItem(rank=1, incident_id="INC8654310", probability=0.78, tone="red"),
                RiskItem(rank=2, incident_id="INC8654287", probability=0.64, tone="red"),
                RiskItem(rank=3, incident_id="INC8654201", probability=0.51, tone="amber"),
                RiskItem(rank=4, incident_id="INC8654144", probability=0.43, tone="amber"),
                RiskItem(rank=5, incident_id="INC8654098", probability=0.37, tone="amber"),
            ],
        ),
        forecast=ForecastTab(
            chroninho=ChroninhoMessage(
                estado="ok",
                estado_label="Tranquilo",
                message=(
                    "A próxima semana soma **168 chamados elegíveis**. Padrão clássico: fim de semana "
                    "calmo, pico entre terça e quinta. P2 e P3 são previstos **separadamente**, porque "
                    "têm dinâmicas diferentes, e somados no final. Sugiro **reforço nos turnos da noite "
                    "de terça e quarta**."
                ),
            ),
            kpis=[
                KpiCard(label="D+1 (amanhã)", value="24", sub="10 P2 + 14 P3", tone="cyan"),
                KpiCard(label="W+1 (soma dos 7 dias)", value="168", sub="IC 90%: 23 a 464, nunca negativo", tone="cyan"),
                KpiCard(label="Pico da semana", value="qua", sub="34 chamados previstos", tone="default"),
                KpiCard(label="Erro médio (validação)", value="4,3", sub="e 11,9 em P3, chamados por dia", tone="default"),
            ],
            schedule_plan=[
                SchedulePlanRow(day="Sáb", forecast=29, suggestion="Escala padrão"),
                SchedulePlanRow(day="Dom", forecast=9, suggestion="Escala reduzida"),
                SchedulePlanRow(day="Seg", forecast=9, suggestion="Escala reduzida"),
                SchedulePlanRow(day="Ter", forecast=33, suggestion="Reforço à noite", tone="amber"),
                SchedulePlanRow(day="Qua", forecast=34, suggestion="Reforço à noite", tone="amber"),
                SchedulePlanRow(day="Qui", forecast=30, suggestion="Escala padrão"),
            ],
        ),
        risk=RiskTab(
            chroninho=ChroninhoMessage(
                estado="alerta",
                estado_label="Alerta",
                message=(
                    "O **INC8654310** me preocupa: **78% de risco** de violar o OLA. Três motivos: a "
                    "descrição indica problema de **banco de dados**, a fila do Team06 está **40% mais "
                    "pressionada** que o normal nos últimos 7 dias e o ativo **IC00341 acumula 12 "
                    "incidentes em 30 dias**. Sugiro priorizar agora."
                ),
            ),
            queue=[
                RiskItem(rank=1, incident_id="INC8654310", probability=0.78, tone="red", team="Team06", asset="IC00341", description="database connection pool"),
                RiskItem(rank=2, incident_id="INC8654287", probability=0.64, tone="red", team="Team06", asset="IC00877", description="alarm application monitoring"),
                RiskItem(rank=3, incident_id="INC8654201", probability=0.51, tone="amber", team="Team11", asset="IC02114", description="apache busy workers"),
                RiskItem(rank=4, incident_id="INC8654144", probability=0.43, tone="amber", team="Team07", asset="IC00341", description="check application monitoring"),
                RiskItem(rank=5, incident_id="INC8654098", probability=0.37, tone="amber", team="Team14", asset="IC05230", description="disk usage threshold"),
                RiskItem(rank=6, incident_id="INC8654076", probability=0.31, tone="amber", team="Team06", asset="IC01988", description="alarm queue latency"),
                RiskItem(rank=7, incident_id="INC8654031", probability=0.26, tone="cyan", team="Team02", asset="IC00452", description="ssl certificate expiry"),
            ],
            explainability=Explainability(
                incident_id="INC8654310",
                increasing=[
                    ExplainabilityFactor(factor="Descrição do chamado", pct="+29%"),
                    ExplainabilityFactor(factor="Pressão da fila (7 dias)", pct="+21%"),
                    ExplainabilityFactor(factor="Histórico do IC00341", pct="+17%"),
                ],
                decreasing=[
                    ExplainabilityFactor(factor="Horário de abertura", pct="-6%"),
                    ExplainabilityFactor(factor="Prioridade P3", pct="-4%"),
                ],
                summary_note=(
                    "Em linguagem de plantão, todo score se explica por três perguntas: **que tipo de "
                    "problema é** (o texto), **que momento a fila vive** (a pressão de 7 dias) e **que "
                    "ativo está envolvido** (a reincidência)."
                ),
            ),
            kpis=[
                KpiCard(label="Poder do modelo", value="17x", sub="melhor que o baseline histórico (PR-AUC)", tone="red", highlight=True),
                KpiCard(label="Acerto no top 10", value="7/10", sub="dos mais críticos violaram de fato", tone="default"),
                KpiCard(label="Raridade do alvo", value="0,95%", sub="238 violações em 25.156 elegíveis", tone="default"),
                KpiCard(label="Limiar de decisão", value="0,21", sub="calibrado por custo de negócio", tone="default"),
            ],
        ),
        trends=TrendsTab(
            chroninho=ChroninhoMessage(
                estado="atento",
                estado_label="Atento",
                message=(
                    "Visão de longo prazo: a operação fechou 2025 em **125% do teto contratual** nas "
                    "duas prioridades. E um dado estrutural: **2 em cada 3 chamados** nascem do "
                    "monitoramento automático, sem categorização humana. O volume não é falta de "
                    "disciplina de registro, é a máquina falando. **Antecipar é a única forma de "
                    "escalar.**"
                ),
            ),
            kpis=[
                KpiCard(label="Atingimento do teto 2025", value="125%", sub="P2 e P3, elegível vs. meta anual", tone="amber", highlight=True),
                KpiCard(label="Origem automática", value="2 em 3", sub="chamados abertos por monitoramento", tone="default"),
                KpiCard(label="Equipes ativas", value="17", sub="filas de atendimento", tone="default"),
                KpiCard(label="Ativos monitorados", value="9,1 mil", sub="itens de configuração", tone="default"),
            ],
            insights=[
                Insight(tone="amber", text="**A operação já roda acima do contrato.** 125% do teto nas duas prioridades em 2025. Antecipar deixou de ser luxo, virou necessidade."),
                Insight(tone="cyan", text="**A falta de categorização é estrutural, não indisciplina.** Chamado automático nasce sem produto e categoria. O Chronos funciona com o dado como ele é: nenhum campo novo precisa ser preenchido."),
                Insight(tone="red", text="**O melhor preditor de violação é a pressão da fila.** O risco não mora só no chamado, mora no momento da operação. Por isso previsão de volume e risco andam juntos no mesmo produto."),
            ],
        ),
        results=ResultsTab(
            chroninho=ChroninhoMessage(
                estado="ok",
                estado_label="Transparente",
                message=(
                    "Aqui está o meu boletim, sem maquiagem. Todos os números vêm de **validação "
                    "temporal estrita**: modelos treinados só com o passado e testados no futuro que "
                    "nunca viram, três vezes, **sem nenhum vazamento de dado**. O que você vê é o que "
                    "eu saberia naquele dia."
                ),
            ),
            model_comparison=[
                ModelComparisonRow(model="CatBoost (produção)", pr_auc="0,154", bar_pct=100, tone="red", note="Vencedor, 17x o baseline"),
                ModelComparisonRow(model="Rede neural (ANN)", pr_auc="0,073", bar_pct=47, tone="gray", note="Prova de viabilidade"),
                ModelComparisonRow(model="Regressão logística", pr_auc="0,043", bar_pct=28, tone="gray", note="Referência interpretável"),
                ModelComparisonRow(model="Baseline histórico", pr_auc="0,009", bar_pct=6, tone="gray", note="Apostar na taxa passada"),
            ],
            comparison_insight=(
                "A regressão logística quase empata com o CatBoost em ROC-AUC (0,81 vs. 0,78) mas "
                "perde de 3,5x em PR-AUC. É a prova de que, com alvo raro, **ROC-AUC engana** e PR-AUC "
                "é a métrica honesta."
            ),
            pr_auc_growth=[
                PrAucGrowthPoint(period="período 1", value="0,08"),
                PrAucGrowthPoint(period="período 2", value="0,14"),
                PrAucGrowthPoint(period="período 3", value="0,24"),
            ],
            growth_insight=(
                "Desempenho **triplicou** conforme o histórico de treino cresceu. É o comportamento "
                "esperado de um sistema desenhado para ser re-treinado, não para ser estátua."
            ),
            volume_mae=VolumeMae(p2="4,3", p3="11,9"),
            engineering_rigor=[
                "**Zero vazamento:** nenhuma coluna pós-evento como preditor",
                "**Validação walk-forward:** 3 períodos temporais estritos, os mesmos para todos os modelos",
                "**Pipeline auditável:** arquitetura em camadas com rastreabilidade ponta a ponta",
            ],
            scientific_honesty=[
                "**Clusterização de texto:** testada na rede neural, piorou o resultado. Descartada com medição, não com opinião.",
                "**Dados sintéticos (SMOTE):** recusados desde o início. Em problema temporal, geram otimismo falso.",
            ],
            footer_note=(
                "Chronos · Projeto FIAP x Locaweb 2026 · Turma 2TSCPW · Bruno Rosa, Danilo Alves, Enzo "
                "Cremaschi e Vinícius Macedo — Resultados sobre dados históricos reais com validação "
                "temporal estrita. Chamados individuais exibidos são ilustrativos, no padrão da base."
            ),
        ),
    )


def _get_client() -> anthropic.Anthropic | None:
    """Sem ANTHROPIC_API_KEY, o app inteiro deve continuar funcionando com os
    mocks/fallbacks — nunca exigir a chave pra rodar localmente ou em dev."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    return anthropic.Anthropic()


# ===== Modo 1: Chroninho com IA real (interpreta os fatos, não calcula nada) =====

CHRONINHO_SYSTEM_PROMPT = (
    "Você é o Chroninho, a persona analítica de AIOps do dashboard Chronos (Locaweb x "
    "FIAP). Para cada uma das 5 abas do dashboard, escreva um insight executivo curto "
    "(2 a 4 frases) em português do Brasil, no tom de um analista de plantão direto e "
    "confiante. Destaque os números mais importantes com **negrito**. Nunca invente "
    "números — use somente os fatos fornecidos no JSON do usuário. Escolha 'estado' "
    "('ok', 'atento' ou 'alerta') e um 'estado_label' curto (1-2 palavras, ex.: "
    "'Atento', 'Tranquilo', 'Alerta', 'Transparente') coerentes com o tom da sua "
    "própria mensagem."
)

_CHRONINHO_TABS = ["overview", "forecast", "risk", "trends", "results"]

_CHRONINHO_SCHEMA = {
    "type": "object",
    "properties": {
        tab: {
            "type": "object",
            "properties": {
                "estado": {"type": "string", "enum": ["ok", "atento", "alerta"]},
                "estado_label": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["estado", "estado_label", "message"],
            "additionalProperties": False,
        }
        for tab in _CHRONINHO_TABS
    },
    "required": _CHRONINHO_TABS,
    "additionalProperties": False,
}


def _facts_for_insights(mock: DashboardResponse) -> dict:
    return {
        "overview": {
            "kpis": [k.model_dump() for k in mock.overview.kpis],
            "top_risks": [r.model_dump() for r in mock.overview.top_risks],
        },
        "forecast": {
            "kpis": [k.model_dump() for k in mock.forecast.kpis],
            "schedule_plan": [s.model_dump() for s in mock.forecast.schedule_plan],
        },
        "risk": {
            "kpis": [k.model_dump() for k in mock.risk.kpis],
            "queue_top3": [r.model_dump() for r in mock.risk.queue[:3]],
            "explainability": mock.risk.explainability.model_dump(),
        },
        "trends": {
            "kpis": [k.model_dump() for k in mock.trends.kpis],
            "insights": [i.model_dump() for i in mock.trends.insights],
        },
        "results": {
            "model_comparison": [m.model_dump() for m in mock.results.model_comparison],
            "pr_auc_growth": [p.model_dump() for p in mock.results.pr_auc_growth],
            "volume_mae": mock.results.volume_mae.model_dump(),
        },
    }


def gerar_insights_chroninho(mock: DashboardResponse) -> dict[str, ChroninhoMessage]:
    client = _get_client()
    if client is None:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada.")

    facts = _facts_for_insights(mock)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=CHRONINHO_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
        output_config={"format": {"type": "json_schema", "schema": _CHRONINHO_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    parsed = json.loads(text)
    return {tab: ChroninhoMessage(**parsed[tab]) for tab in _CHRONINHO_TABS}


def _build_dashboard() -> DashboardResponse:
    mock = _mock_dashboard()
    try:
        insights = gerar_insights_chroninho(mock)
        mock.overview.chroninho = insights["overview"]
        mock.forecast.chroninho = insights["forecast"]
        mock.risk.chroninho = insights["risk"]
        mock.trends.chroninho = insights["trends"]
        mock.results.chroninho = insights["results"]
    except Exception as exc:  # fallback: mantém os textos mockados já em `mock`
        print(f"[chroninho] usando fallback mockado ({exc})")
    return mock


_CACHE: dict[str, object] = {"data": None, "ts": 0.0}
_CACHE_TTL_SECONDS = 300


def _cached_dashboard() -> DashboardResponse:
    now = time.time()
    if _CACHE["data"] is None or (now - _CACHE["ts"]) > _CACHE_TTL_SECONDS:
        _CACHE["data"] = _build_dashboard()
        _CACHE["ts"] = now
    return _CACHE["data"]


@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard() -> DashboardResponse:
    return _cached_dashboard()


# ===== Modo 2: chat interativo com tool-use sobre os mesmos dados mockados =====
# As tools só fazem lookup em `_mock_dashboard()` — o Claude nunca calcula
# previsão/risco, só consulta e explica os mesmos fatos que já estão na tela.


@beta_tool
def prever_volume(horizonte: str) -> str:
    """Consulta a previsão de volume de chamados do Chronos.

    Args:
        horizonte: "d1" para a previsão de amanhã, ou "w1" para a soma dos próximos 7 dias.
    """
    mock = _mock_dashboard()
    label_hint = "D+1" if horizonte == "d1" else "7 dias"
    kpi = next((k for k in mock.overview.kpis if label_hint in k.label), mock.overview.kpis[0])
    return json.dumps(kpi.model_dump(), ensure_ascii=False)


@beta_tool
def consultar_risco_ola(equipe: str = "") -> str:
    """Lista os chamados abertos com risco de violar o OLA, opcionalmente filtrados por equipe.

    Args:
        equipe: nome do time pra filtrar, ex. "Team06". Deixe vazio ("") para listar todos.
    """
    mock = _mock_dashboard()
    items = mock.risk.queue
    if equipe:
        items = [i for i in items if i.team == equipe]
    return json.dumps([i.model_dump() for i in items], ensure_ascii=False)


@beta_tool
def explicar_risco(chamado_id: str) -> str:
    """Explica por que um chamado específico tem o score de risco que tem (fatores de explicabilidade).

    Args:
        chamado_id: identificador do incidente, ex.: "INC8654310".
    """
    mock = _mock_dashboard()
    exp = mock.risk.explainability
    if exp.incident_id != chamado_id:
        return json.dumps(
            {"erro": f"Não há explicabilidade detalhada para {chamado_id} neste MVP; só temos para {exp.incident_id}."},
            ensure_ascii=False,
        )
    return json.dumps(exp.model_dump(), ensure_ascii=False)


@beta_tool
def tendencias() -> str:
    """Retorna as tendências macro e os insights de longo prazo da operação."""
    mock = _mock_dashboard()
    return json.dumps(
        {
            "kpis": [k.model_dump() for k in mock.trends.kpis],
            "insights": [i.model_dump() for i in mock.trends.insights],
        },
        ensure_ascii=False,
    )


CHAT_SYSTEM_PROMPT = (
    "Você é o Chroninho, o assistente analítico de AIOps do Projeto Chronos para a "
    "Locaweb. Fale em português do Brasil, direto e prático, como um analista de "
    "plantão experiente. Use as ferramentas disponíveis para consultar dados reais "
    "do dashboard antes de responder — nunca invente números. Destaque valores "
    "importantes com **negrito**. Seja conciso: 2 a 5 frases por resposta."
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    client = _get_client()
    if client is None:
        return ChatResponse(reply="O chat com IA ainda não está configurado (falta ANTHROPIC_API_KEY).")

    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    try:
        runner = client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            tools=[prever_volume, consultar_risco_ola, explicar_risco, tendencias],
            messages=messages,
        )
        final = None
        for msg in runner:
            final = msg
        text = next((b.text for b in final.content if b.type == "text"), "") if final else ""
        return ChatResponse(reply=text or "Não consegui gerar uma resposta agora.")
    except Exception as exc:
        print(f"[chat] erro ao consultar a IA: {exc}")
        return ChatResponse(reply="Deu um erro ao consultar a IA agora. Tenta de novo em um instante.")
