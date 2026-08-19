"""
utils.py — Projeto Cronos (Locaweb Challenge 2026)
Utilitários compartilhados entre as camadas Bronze / Silver / Gold e os
notebooks de modelagem dos DESAFIOS OFICIAIS do challenge (Desafio 1 —
SARIMAX, Desafio 3 — CatBoost, Desafio 4 — SHAP).

>>> ESTRUTURA DO ARQUIVO: PROJETO PRIMEIRO, SPRINT NO FINAL <<<
Este arquivo tem uma divisória visível (procure por "FIM DO ESCOPO DO
PROJETO") separando duas partes:
  1. Tudo ANTES da divisória: o projeto real entregue à Locaweb.
  2. Tudo A PARTIR da divisória: funções exclusivas das entregas
     acadêmicas de Sprint da FIAP (Sprint 3 de Machine Learning/Deep
     Learning — um modelo "simples e interpretável" e uma ANN, exigidos
     pela disciplina, não pelo challenge). Nenhum notebook do projeto
     principal depende dessa parte.
Um só arquivo para não ter que sincronizar dois `.py` no Drive, mas a
fronteira fica marcada de propósito — se precisar saber rapidamente
"isso aqui é do projeto ou da disciplina", é só olhar de qual lado da
divisória a função está.

Filosofia deste módulo:
- Nenhuma regra de negócio mora aqui. Isso aqui é "encanamento":
  logging, paths, leitura/gravação padronizada, validação de schema,
  e profiling genérico de DataFrame. Regra de negócio (o que é
  outlier, o que é vazamento, como tratar nulo) fica nos notebooks
  de cada camada, onde a decisão pode ser lida e revisada em contexto.
- Cada gravação registra metadados de proveniência (quando, de onde,
  hash do arquivo de origem) porque, em produção, "de onde veio esse
  dado" é a primeira pergunta que alguém faz quando um número não bate.
- Funções pequenas e testáveis. Se uma função aqui começar a acumular
  parâmetros condicionais para casos especiais, é sinal de que virou
  regra de negócio e deveria voltar para o notebook da camada.

Uso típico em um notebook Colab (projeto ou sprint — é o mesmo import,
mudando só quais nomes você importa):

    import sys
    sys.path.append('/content/drive/MyDrive/cronos_project')
    from utils import (
        setup_logging, PROJECT_PATHS, load_excel_source,
        save_parquet_with_metadata, validate_schema, profile_dataframe,
    )
"""

from __future__ import annotations

import hashlib
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import numpy as np


# =====================================================================
# 1. LOGGING
# =====================================================================
# Um cientista de dados "ligado à empresa" não debuga com print() — usa
# logging porque isso é o que vira log de execução em produção/Airflow/
# GitHub Actions amanhã, sem precisar reescrever nada.

def setup_logging(name: str = "cronos", level: int = logging.INFO) -> logging.Logger:
    """Configura um logger padronizado para todos os notebooks do projeto.

    Chamar no início de cada notebook: logger = setup_logging("bronze").
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evita handlers duplicados se a célula for reexecutada no Colab
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# =====================================================================
# 2. CONFIGURAÇÃO DE PATHS
# =====================================================================
# Centralizado aqui para que trocar a estrutura de pastas no Drive não
# exija caçar strings de path espalhadas em 7 notebooks diferentes.

@dataclass(frozen=True)
class ProjectPaths:
    """Caminhos padronizados do projeto, todos derivados de uma raiz única."""

    root: Path = Path("/content/drive/MyDrive/cronos_project")

    @property
    def raw_source(self) -> Path:
        return self.root / "data_raw" / "LW-DATASET.xlsx"

    @property
    def bronze(self) -> Path:
        return self.root / "data" / "bronze"

    @property
    def silver(self) -> Path:
        return self.root / "data" / "silver"

    @property
    def gold(self) -> Path:
        return self.root / "data" / "gold"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ensure_dirs(self) -> None:
        """Cria toda a árvore de diretórios do projeto, se ainda não existir."""
        for p in [self.bronze, self.silver, self.gold, self.logs]:
            p.mkdir(parents=True, exist_ok=True)


PROJECT_PATHS = ProjectPaths()


# =====================================================================
# 3. SCHEMA CONTRATADO (dicionário de dados como código)
# =====================================================================
# Isso transforma o dicionário de dados do documento de ideação em algo
# que o pipeline consegue checar sozinho. Se a Locaweb mandar uma nova
# extração do dataset amanhã com uma coluna a menos ou renomeada, é
# aqui que isso é detectado — na Bronze, antes de qualquer camada
# consumir um dado incompleto silenciosamente.

EXPECTED_COLUMNS: tuple[str, ...] = (
    "Número",
    "Prioridade",
    "Produto",
    "Categoria",
    "Subcategoria",
    "Grupo designado",
    "Item de configuração",
    "Aberto",
    "Resolvido",
    "Encerrado",
    "Duração",
    "Código de fechamento",
    "Descrição resumida",
    "Solução",
    "Aberto por",
    "Incidente Pai",
    "Status",
    "Entrou para KPI?",
    "KPI Violado?",
)

# Colunas que, na origem, já são timestamp — usadas para tipagem mínima
# na Bronze (a ÚNICA transformação que a Bronze aplica).
DATETIME_COLUMNS: tuple[str, ...] = ("Aberto", "Resolvido", "Encerrado")


def validate_schema(
    df: pd.DataFrame,
    expected_columns: Iterable[str] = EXPECTED_COLUMNS,
    logger: logging.Logger | None = None,
) -> None:
    """Valida que o DataFrame tem exatamente as colunas esperadas.

    Não corrige nada — só denuncia. Colunas faltando levantam erro
    (parar o pipeline é o comportamento certo: é melhor falhar alto
    e cedo do que a Gold silenciosamente ficar sem uma feature).
    Colunas extras geram warning (pode ser um campo novo da Locaweb
    que ainda não foi incorporado ao dicionário de dados — não é
    necessariamente um erro, mas precisa de atenção humana).
    """
    log = logger or logging.getLogger("cronos")
    atual = set(df.columns)
    esperado = set(expected_columns)

    faltando = esperado - atual
    extras = atual - esperado

    if faltando:
        raise ValueError(
            f"Schema quebrado: {len(faltando)} coluna(s) esperada(s) não encontrada(s) "
            f"na fonte: {sorted(faltando)}. Pipeline interrompido — não seguir para Silver/Gold "
            f"até confirmar se é uma mudança de schema da fonte ou um erro de carga."
        )

    if extras:
        log.warning(
            "Colunas presentes na fonte mas fora do dicionário de dados esperado: %s "
            "— confirmar se é um campo novo antes de decidir se entra na Silver.",
            sorted(extras),
        )

    log.info("Schema validado: %d colunas esperadas, todas presentes.", len(esperado))


# Domínios categóricos conhecidos, na origem — usados por validate_categorical_domains()
# para detectar valores novos/inesperados que a validação de schema (que só olha nome de
# coluna) não pega. Uma coluna aqui não precisa cobrir 100% dos valores "corretos" para
# sempre — o objetivo não é travar o pipeline a cada valor novo genuíno, é AVISAR quando
# a fonte manda algo fora do que já foi observado e documentado.
KNOWN_CATEGORICAL_DOMAINS: dict[str, frozenset[str]] = {
    "Prioridade": frozenset({"1 - Crítica", "2 - Alta", "3 - Média", "4 - Baixa", "5 - Muito Baixa"}),
    "Status": frozenset({"Sem Intervenção", "Encerrado", "Encerrado Automaticamente", "Aguardando Problema"}),
    "Aberto por": frozenset({"Monitoramento", "Manual"}),
    "Entrou para KPI?": frozenset({"SIM", "NAO"}),
    "KPI Violado?": frozenset({"SIM", "NAO"}),
}


def validate_categorical_domains(
    df: pd.DataFrame,
    domains: dict[str, frozenset[str]] = KNOWN_CATEGORICAL_DOMAINS,
    logger: logging.Logger | None = None,
) -> dict[str, set]:
    """Para cada coluna em `domains`, verifica se os valores observados no
    DataFrame são um subconjunto dos valores conhecidos/esperados.

    Diferente de `validate_schema` (que checa nome de coluna), isto checa
    o CONTEÚDO da coluna — pega o caso, por exemplo, de a fonte passar a
    mandar uma nova Prioridade ('0 - Emergencial') que nenhuma regra
    downstream (Silver, Gold, modelagem) foi desenhada para tratar.

    Não levanta exceção — apenas loga um warning por coluna com valores
    novos, e retorna um dicionário {coluna: {valores novos}} para quem
    chamar decidir o que fazer (parar, ignorar, ou atualizar o domínio
    conhecido). Nulos são ignorados aqui de propósito — nulo é tratado
    como decisão à parte em cada camada, não como "valor fora do domínio".
    """
    log = logger or logging.getLogger("cronos")
    achados: dict[str, set] = {}

    for coluna, valores_esperados in domains.items():
        if coluna not in df.columns:
            continue
        valores_observados = set(df[coluna].dropna().unique())
        novos = valores_observados - valores_esperados
        if novos:
            achados[coluna] = novos
            log.warning(
                "Domínio categórico de '%s' tem %d valor(es) não observado(s) antes: %s "
                "— confirmar se é uma mudança legítima da fonte antes de seguir.",
                coluna, len(novos), sorted(novos),
            )
        else:
            log.info("Domínio categórico de '%s': OK, nenhum valor novo.", coluna)

    return achados


# =====================================================================
# 4. LEITURA DA FONTE, COM HASH DE PROVENIÊNCIA
# =====================================================================

def compute_file_hash(path: Path, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """Calcula o hash de um arquivo, para registrar de forma inequívoca
    qual versão exata do arquivo de origem gerou uma Bronze específica.

    Isso importa porque "o mesmo nome de arquivo" não garante "o mesmo
    conteúdo" — se a Locaweb reenviar o LW-DATASET.xlsx atualizado com
    o mesmo nome, o hash muda e isso fica registrado nos metadados.
    """
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_parquet_layer(
    path: Path,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Lê um parquet de qualquer camada (Bronze/Silver/Gold), logando shape
    e as colunas de metadados de proveniência encontradas (se houver).

    Usar isso em vez de `pd.read_parquet` direto nos notebooks de camada
    garante que toda leitura entre-camadas fica logada da mesma forma,
    o que ajuda muito a debugar "cadê essas 40 linhas que sumiram" sem
    precisar adicionar prints manuais toda vez.
    """
    log = logger or logging.getLogger("cronos")

    if not path.exists():
        raise FileNotFoundError(
            f"Camada não encontrada em {path}. Confirme se o notebook da "
            f"camada anterior já rodou e gravou o parquet esperado."
        )

    df = pd.read_parquet(path)
    meta_cols = [c for c in df.columns if c.startswith("_")]
    log.info(
        "Lido de %s: %d linhas x %d colunas (%d colunas de metadado: %s).",
        path, df.shape[0], df.shape[1] - len(meta_cols), len(meta_cols), meta_cols,
    )
    return df


def load_excel_source(
    path: Path | None = None,
    logger: logging.Logger | None = None,
) -> pd.DataFrame:
    """Carrega o arquivo Excel de origem, sem nenhuma transformação de
    conteúdo — só leitura. Loga shape e hash do arquivo para o registro
    de proveniência.
    """
    log = logger or logging.getLogger("cronos")
    source_path = path or PROJECT_PATHS.raw_source

    if not source_path.exists():
        raise FileNotFoundError(
            f"Arquivo de origem não encontrado em {source_path}. "
            f"Confirme se o Drive foi montado e o arquivo está no lugar esperado."
        )

    file_hash = compute_file_hash(source_path)
    log.info("Lendo fonte: %s (sha256=%s)", source_path, file_hash[:12])

    df = pd.read_excel(source_path)
    log.info("Fonte carregada: %d linhas x %d colunas.", df.shape[0], df.shape[1])

    return df


# =====================================================================
# 5. GRAVAÇÃO PADRONIZADA COM METADADOS DE PROVENIÊNCIA
# =====================================================================

def save_parquet_with_metadata(
    df: pd.DataFrame,
    path: Path,
    source_hash: str | None = None,
    layer: str = "bronze",
    logger: logging.Logger | None = None,
) -> None:
    """Grava um DataFrame em parquet, acrescentando colunas de auditoria
    (`_ingested_at`, `_source_layer`, `_source_hash`) — sem alterar as
    colunas de negócio originais.

    O objetivo dessas colunas de metadado é rastreabilidade: em qualquer
    camada, é possível responder "quando esse dado entrou no pipeline" e
    "a partir de qual versão exata da fonte" sem depender de memória ou
    de nome de arquivo.
    """
    log = logger or logging.getLogger("cronos")
    path.parent.mkdir(parents=True, exist_ok=True)

    df_out = df.copy()
    df_out["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df_out["_source_layer"] = layer
    if source_hash:
        df_out["_source_hash"] = source_hash[:16]

    df_out.to_parquet(path, index=False, engine="pyarrow")
    log.info("Gravado: %s (%d linhas, %.1f MB).", path, len(df_out), path.stat().st_size / 1e6)


# =====================================================================
# 6. PROFILING GENÉRICO (reaproveitável em qualquer camada)
# =====================================================================

def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Gera um resumo estrutural padrão: dtype, contagem de não-nulos,
    percentual de nulos e cardinalidade, por coluna.

    Esta é a mesma tabela usada na Seção 2 da EDA — centralizada aqui
    para não reescrever a lógica em cada notebook de camada e garantir
    que Bronze/Silver/Gold reportem esse resumo de forma idêntica,
    facilitando comparar o "antes e depois" de cada transformação.
    """
    resumo = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "n_nao_nulos": df.notna().sum(),
        "n_nulos": df.isna().sum(),
        "pct_nulos": (df.isna().mean() * 100).round(2),
        "n_unicos": df.nunique(),
    })
    return resumo.sort_values("pct_nulos", ascending=False)


def diff_row_count(df_antes: pd.DataFrame, df_depois: pd.DataFrame, etapa: str,
                    logger: logging.Logger | None = None) -> None:
    """Loga quantas linhas uma transformação removeu/adicionou.

    Chamar depois de qualquer operação que possa mudar o número de
    linhas (dedup, filtro, join) — em produção, uma queda inesperada
    de linhas é o sintoma mais comum de um bug silencioso de pipeline.
    """
    log = logger or logging.getLogger("cronos")
    delta = len(df_depois) - len(df_antes)
    sinal = "+" if delta >= 0 else ""
    log.info(
        "[%s] %d -> %d linhas (%s%d, %.2f%%).",
        etapa, len(df_antes), len(df_depois), sinal, delta,
        (delta / len(df_antes) * 100) if len(df_antes) else 0.0,
    )


# =====================================================================
# 7. TEXTO — normalização determinística (sem aprendizado de vocabulário)
# =====================================================================
# Deliberadamente "burra": só remove acentuação, pontuação e stopwords.
# Nenhum TF-IDF, embedding ou tokenizador é ajustado aqui — isso é
# aprendizado de representação e, se colocado na Silver, vazaria
# informação do conjunto inteiro (incluindo o que depois vira "teste")
# para dentro de uma etapa que deveria ser puramente determinística.

STOPWORDS_PT_BR: frozenset[str] = frozenset("""
a ao aos aquela aquelas aquele aqueles aquilo as até com como da das de dela
delas dele deles depois do dos e ela elas ele eles em entre era eram essa
essas esse esses esta estas este estes eu foi foram há isso isto já lhe lhes
mais mas me mesmo meu meus minha minhas muito na nas nem no nos nossa nossas
nosso nossos num numa nós o os ou para pela pelas pelo pelos por qual quando
que quem se seu seus só sua suas também te tem tera teu teus tu tua tuas um
uma você vocês
""".split())


def clean_text_ptbr(series: pd.Series) -> pd.Series:
    """Normalização determinística de texto em português: minúsculas,
    remoção de acentuação, remoção de caracteres não-alfanuméricos, e
    remoção de stopwords comuns. Não faz stemming/lematização (decisão
    deliberada — mudaria o vocabulário de forma menos auditável, e o
    CatBoost text_features já lida bem com variações morfológicas).

    Preserva valores nulos como nulos (não os transforma em string vazia,
    para não confundir "sem descrição" com "descrição vazia após limpeza").
    """

    def _clean_one(texto: object) -> object:
        if pd.isna(texto):
            return texto
        texto = str(texto).lower()
        texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        texto = re.sub(r"[^a-z0-9\s]", " ", texto)
        tokens = [t for t in texto.split() if t not in STOPWORDS_PT_BR]
        return " ".join(tokens)

    return series.apply(_clean_one)


# =====================================================================
# 8. TRATAMENTO DE OUTLIERS — winsorização explícita, nunca silenciosa
# =====================================================================

def cap_outliers(
    series: pd.Series,
    upper_quantile: float = 0.99,
    logger: logging.Logger | None = None,
    label: str = "",
) -> pd.Series:
    """Winsoriza (capa) os valores acima do quantil informado, retornando
    uma nova série. Loga quantos valores foram afetados e o teto aplicado
    — a winsorização NUNCA deve ser silenciosa, porque ela descaracteriza
    a cauda da distribuição, e quem for auditar a Silver precisa ver esse
    número no log, não descobrir por acaso numa análise futura.
    """
    log = logger or logging.getLogger("cronos")
    teto = series.quantile(upper_quantile)
    n_afetados = int((series > teto).sum())

    log.info(
        "cap_outliers%s: teto no p%.0f = %.2f | %d valores afetados (%.2f%%).",
        f" [{label}]" if label else "", upper_quantile * 100, teto,
        n_afetados, (n_afetados / len(series) * 100) if len(series) else 0.0,
    )

    return series.clip(upper=teto)


# =====================================================================
# 9. FEATURES DE TEMPO CÍCLICO (genérico — usado pela Gold)
# =====================================================================

def add_cyclical_time_features(
    df: pd.DataFrame,
    values: pd.Series,
    period: float,
    prefix: str,
) -> pd.DataFrame:
    """Adiciona colunas seno/cosseno para uma grandeza cíclica (hora do
    dia, dia da semana, dia do ano etc.), retornando uma CÓPIA do df com
    as duas colunas novas: `{prefix}_sin` e `{prefix}_cos`.

    Por que seno/cosseno em vez do número cru: hora 23 e hora 0 são
    adjacentes no relógio, mas "distantes" numericamente (23 vs 0) se
    tratadas como um número comum — a codificação cíclica preserva essa
    adjacência para o modelo. Isso é transformação matemática genérica,
    não decisão de negócio, por isso mora no utils e não no notebook.
    """
    df_out = df.copy()
    df_out[f"{prefix}_sin"] = np.sin(2 * np.pi * values / period)
    df_out[f"{prefix}_cos"] = np.cos(2 * np.pi * values / period)
    return df_out


# =====================================================================
# 10. CONTAGEM HISTÓRICA CAUSAL POR CHAVE (genérico — usado pela Gold)
# =====================================================================

def expanding_count_by_key(
    df: pd.DataFrame,
    key_col: str,
    time_col: str,
    new_col: str,
) -> pd.Series:
    """Para cada linha, conta quantas ocorrências da mesma chave (`key_col`)
    já existiam ANTES do timestamp daquela linha (`time_col`) — nunca
    incluindo a própria linha nem eventos futuros.

    Uso típico: 'quantos incidentes esse mesmo Item de configuração já
    teve antes deste' — um "histórico de recorrência" que é legítimo de
    usar como feature porque, no instante de abertura de um chamado
    novo, o histórico passado daquele ativo já é conhecido; o que NUNCA
    pode entrar é a contagem TOTAL (passado + futuro), que vazaria
    informação que só existe depois do fato.

    Quando `key_col` é nulo naquela linha (ex.: chamado sem Incidente
    Pai), o resultado é NaN, não 0 — "não aplicável" é semanticamente
    diferente de "zero ocorrências anteriores", e essa distinção é
    preservada de propósito.

    Retorna uma Series alinhada ao índice de `df`, pronta para virar
    uma nova coluna: df[new_col] = expanding_count_by_key(df, ...).
    """
    ordenado = df.sort_values(time_col)
    contagem_causal = ordenado.groupby(key_col, dropna=True).cumcount()
    return contagem_causal.reindex(df.index).rename(new_col)


def hours_since_last_event_by_key(
    df: pd.DataFrame,
    key_col: str,
    time_col: str,
    new_col: str,
) -> pd.Series:
    """Para cada linha, calcula quantas horas se passaram desde a última
    ocorrência anterior da mesma chave — NaN se for a primeira ocorrência
    (não existe "última vez" para comparar).

    Complementa `expanding_count_by_key`: a contagem mede FREQUÊNCIA
    histórica ("esse ativo já deu problema muitas vezes"), isso aqui mede
    RECÊNCIA ("o último problema desse ativo foi há quanto tempo") — um
    ativo com recorrência muito curta entre incidentes é um sinal
    operacional diferente de um ativo com muitos incidentes espaçados
    ao longo de anos.
    """
    ordenado = df.sort_values(time_col)
    tempo_anterior = ordenado.groupby(key_col, dropna=True)[time_col].shift(1)
    delta_horas = (ordenado[time_col] - tempo_anterior).dt.total_seconds() / 3600
    return delta_horas.reindex(df.index).rename(new_col)


def rolling_window_causal_count(
    df: pd.DataFrame,
    key_col: str,
    time_col: str,
    window: str,
    new_col: str,
) -> pd.Series:
    """Para cada linha, conta quantos eventos da mesma chave ocorreram na
    janela de tempo imediatamente anterior (ex.: '60min') — exclui
    sempre o próprio evento (janela fechada à esquerda: [t-janela, t)).

    Diferença para `expanding_count_by_key`: aquela função mede o
    histórico TOTAL (desde o início dos dados); esta mede carga RECENTE
    numa janela curta. Uso típico: 'quantos chamados esse Grupo
    designado já está atendendo na última hora' — um proxy de carga de
    trabalho corrente da equipe naquele instante, diferente de um
    histórico acumulado de meses.

    `window` aceita qualquer string de offset do pandas (ex.: '60min',
    '2h', '1D').

    Implementação: concatena o resultado por grupo explicitamente com
    `pd.concat`, em vez de usar `groupby(...).apply(...)` — descobrimos,
    via teste automatizado, que `apply` muda a forma do resultado quando
    há um único grupo no DataFrame (colapsa para DataFrame largo em vez
    de concatenar as séries), o que quebrava silenciosamente em bases
    pequenas ou filtradas a um só grupo. `pd.concat` tem comportamento
    determinístico independente do número de grupos.
    """
    df_sorted = df.sort_values(time_col)
    partes: list[pd.Series] = []

    for _, grupo in df_sorted.groupby(key_col):
        serie = pd.Series(1, index=pd.DatetimeIndex(grupo[time_col]))
        contado = serie.rolling(window, closed="left").count()
        contado.index = grupo.index
        partes.append(contado)

    resultado = pd.concat(partes) if partes else pd.Series(dtype=float)
    return resultado.reindex(df.index).fillna(0).rename(new_col)


# =====================================================================
# 11. ESTATÍSTICA DE REFERÊNCIA POR GRUPO (descritiva — nunca feature de modelo direto)
# =====================================================================
# Diferença crítica em relação às funções causais acima: as funções desta
# seção usam a base INTEIRA (não são causais/temporais) e por isso NUNCA
# devem virar uma coluna por-linha usada como feature de um modelo
# supervisionado — isso seria vazamento (a estatística "vê" o futuro de
# qualquer linha específica). Servem para DOIS usos legítimos: (1) uma
# tabela de referência/diagnóstico (ex.: Desafio 2, que é descritivo, não
# preditivo), ou (2) documentar explicitamente que um recálculo causal
# equivalente, se necessário como feature, deve ser feito dentro do fold
# de treino no notebook de modelagem.

def duration_reference_stats_by_group(
    df: pd.DataFrame,
    duration_col: str,
    group_cols: list[str],
) -> pd.DataFrame:
    """Gera uma tabela de referência (mediana, média, p90, contagem) de
    uma coluna de duração, agrupada por uma ou mais colunas categóricas
    (tipicamente `Status`, isoladamente ou cruzado com `Prioridade`).

    Motivação: o teste de Kruskal-Wallis já confirmou que `Duração` é
    uma mistura de populações diferentes por `Status` — comparar
    duração sem essa segmentação mistura processos incomparáveis. Esta
    função existe para que a Gold registre essa segmentação como uma
    TABELA DE REFERÊNCIA (uso em relatório/diagnóstico), sem transformar
    isso numa coluna por-ticket que arriscaria vazamento se usada como
    feature (a duração de um chamado só é conhecida no fechamento).
    """
    agrupado = df.groupby(group_cols)[duration_col].agg(
        mediana="median", media="mean", p90=lambda s: s.quantile(0.90), contagem="count",
    )
    return agrupado.round(1).sort_values("mediana", ascending=False)


def flag_low_volume_groups(
    df: pd.DataFrame,
    group_col: str,
    min_volume: int = 100,
) -> pd.Series:
    """Retorna uma Series booleana (alinhada ao índice de `df`) marcando
    linhas cujo grupo (ex.: `Grupo designado`) tem menos de `min_volume`
    observações no total — usado para sinalizar que uma estatística
    calculada para aquele grupo (ex.: taxa de violação) é estatisticamente
    instável e não deve ser super-interpretada isoladamente.

    Este é o substituto deliberadamente mais simples de um shrinkage
    bayesiano completo: shrinkage de TAXA (ex.: taxa de violação por
    Grupo designado) usa a variável-alvo no cálculo e, por isso, só pode
    ser computado dentro do fold de treino no notebook de modelagem —
    nunca aqui na Gold. Esta flag usa apenas VOLUME (contagem, não
    alvo), então é segura de pré-calcular, e já resolve o caso de uso
    prático: avisar que uma leitura como 'Team06 tem taxa de violação de
    10%' vem de uma base de 39 casos.

    IMPORTANTE: calcule esta flag sobre o MESMO subconjunto em que a
    instabilidade importa. Para o Desafio 3, isso é o universo elegível
    para KPI (`Entrou para KPI? == 'SIM'`), não a base inteira de
    chamados — um grupo pode ter milhares de chamados no total e ainda
    assim poucas dezenas de casos elegíveis.
    """
    contagem_por_grupo = df.groupby(group_col)[group_col].transform("count")
    return (contagem_por_grupo < min_volume).rename(f"{group_col}_baixo_volume")


# =====================================================================
# 12. VALIDAÇÃO TEMPORAL — folds walk-forward (compartilhado entre desafios)
# =====================================================================

def generate_expanding_folds(
    start_date: str = "2025-01-01",
    min_train_weeks: int = 30,
    test_weeks: int = 7,
    n_folds: int = 3,
) -> list[dict]:
    """Gera os limites de data dos folds walk-forward (janela expansiva),
    no mesmo desenho usado tanto para o Desafio 1 (SARIMAX) quanto para o
    Desafio 3 (CatBoost) — mesmos limites de semana para os dois, o que
    torna qualquer comparação entre os dois desafios (ex.: 'pressão de
    fila prevista' como feature) temporalmente consistente.

    Retorna uma lista de dicionários com `fold`, `train_start`,
    `train_end`, `test_start`, `test_end` (todos `pd.Timestamp`). O
    treino de cada fold sempre começa em `start_date` (janela expansiva,
    não deslizante) — fold 2 inclui todo o período do fold 1, mais o
    período de teste do fold 1.
    """
    inicio = pd.Timestamp(start_date)
    folds = []
    for i in range(n_folds):
        train_end = inicio + pd.Timedelta(weeks=min_train_weeks + i * test_weeks) - pd.Timedelta(days=1)
        test_start = inicio + pd.Timedelta(weeks=min_train_weeks + i * test_weeks)
        test_end = test_start + pd.Timedelta(weeks=test_weeks) - pd.Timedelta(days=1)
        folds.append({
            "fold": i + 1,
            "train_start": inicio,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
        })
    return folds


# =====================================================================
# 13. MÉTRICAS PARA CLASSE RARA — bootstrap e Precision@K (compartilhado)
# =====================================================================

def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k) -> float:
    """Precision@K: dos K casos com maior score previsto, qual fração
    realmente é positiva. `k` pode ser um inteiro (top-K casos) ou um
    float entre 0 e 1 (top-K% dos casos).

    Esta é a métrica que reflete o uso real do modelo de risco: uma fila
    priorizada, consumida do topo para baixo por um coordenador — não
    um threshold fixo de probabilidade.
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    n = len(y_true)
    k_int = int(k * n) if isinstance(k, float) and k <= 1 else int(k)
    k_int = max(1, min(k_int, n))

    ordem = np.argsort(-y_score)
    top_k = y_true[ordem[:k_int]]
    return float(top_k.mean())


def bootstrap_metric_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric_fn,
    n_boot: int = 1000,
    ci: float = 0.90,
    random_state: int = 42,
) -> dict:
    """Calcula uma métrica (ex.: average_precision_score, roc_auc_score,
    ou `precision_at_k` acima) sobre reamostragens bootstrap REAIS
    (com reposição, dos próprios dados de teste — nunca sintéticas) do
    conjunto de teste, retornando o valor pontual e o intervalo de
    confiança.

    Motivação: com poucos positivos (ex.: ~250 casos), qualquer métrica
    de um único cálculo no conjunto de teste tem alta variância — o
    intervalo de confiança é o que separa uma leitura honesta de uma
    aparência de precisão que os dados não sustentam.

    `metric_fn` deve ter assinatura `metric_fn(y_true, y_score) -> float`.
    Reamostragens sem nenhum positivo são descartadas (a métrica não
    seria definida) e não contam para `n_boot`.
    """
    rng = np.random.default_rng(random_state)
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    n = len(y_true)

    valor_pontual = metric_fn(y_true, y_score)

    amostras = []
    tentativas = 0
    max_tentativas = n_boot * 20  # limite de segurança contra loop infinito
    while len(amostras) < n_boot and tentativas < max_tentativas:
        tentativas += 1
        idx = rng.integers(0, n, size=n)
        y_true_boot, y_score_boot = y_true[idx], y_score[idx]
        if y_true_boot.sum() == 0:
            continue
        amostras.append(metric_fn(y_true_boot, y_score_boot))

    amostras = np.array(amostras)
    alpha = (1 - ci) / 2
    return {
        "valor_pontual": float(valor_pontual),
        "media_bootstrap": float(amostras.mean()) if len(amostras) else float("nan"),
        "desvio_padrao": float(amostras.std()) if len(amostras) else float("nan"),
        "ic_inferior": float(np.quantile(amostras, alpha)) if len(amostras) else float("nan"),
        "ic_superior": float(np.quantile(amostras, 1 - alpha)) if len(amostras) else float("nan"),
        "n_amostras_validas": len(amostras),
    }


# =====================================================================
# 14. SÉRIES TEMPORAIS — baselines, métricas e variantes SARIMAX (compartilhado)
# =====================================================================
# Consolidado aqui depois que o notebook do Desafio 1 cresceu bastante repetindo
# a mesma lógica em várias seções — mesmo princípio do resto do utils.py:
# a mecânica genérica mora aqui, a decisão de QUAL variante/hiperparâmetro usar
# fica no notebook, em contexto.

def calcular_metricas_serie(y_real, y_previsto) -> dict:
    """MAE, RMSE, MAPE — e as versões robustas (mediana) MedAE e MdAPE, menos
    sensíveis a um único dia de erro extremo do que a média. Motivação
    direta: no Desafio 1, um único salto de volume anômalo num dia (ver
    `detectar_saltos_anomalos`) pode dominar a média de erro de um fold
    inteiro sem representar o comportamento típico do modelo — reportar
    a mediana ao lado da média torna isso visível em vez de escondido.
    """
    y_real = np.asarray(y_real, dtype=float)
    y_previsto = np.asarray(y_previsto, dtype=float)
    erro_absoluto = np.abs(y_real - y_previsto)
    denom = np.where(y_real == 0, np.nan, y_real)
    erro_percentual = np.abs((y_real - y_previsto) / denom) * 100

    return {
        "MAE": round(float(np.mean(erro_absoluto)), 2),
        "RMSE": round(float(np.sqrt(np.mean((y_real - y_previsto) ** 2))), 2),
        "MAPE_%": round(float(np.nanmean(erro_percentual)), 2),
        "MedAE": round(float(np.median(erro_absoluto)), 2),
        "MdAPE_%": round(float(np.nanmedian(erro_percentual)), 2),
    }


def baseline_naive(serie_treino: pd.Series, horizonte: int) -> np.ndarray:
    """Repete o último valor observado do treino para todo o horizonte."""
    return np.full(horizonte, serie_treino.iloc[-1])


def baseline_seasonal_naive(serie_treino: pd.Series, horizonte: int, periodo: int = 7) -> np.ndarray:
    """Repete o padrão da última semana completa do treino, ciclicamente."""
    ultima_semana = serie_treino.iloc[-periodo:].values
    return np.tile(ultima_semana, int(np.ceil(horizonte / periodo)))[:horizonte]


def baseline_rolling_mean(serie_treino: pd.Series, horizonte: int, janela: int = 7) -> np.ndarray:
    """Repete a média móvel dos últimos `janela` dias do treino para todo o horizonte."""
    return np.full(horizonte, serie_treino.iloc[-janela:].mean())


def baseline_arima_puro(serie_treino: pd.Series, horizonte: int, **auto_arima_kwargs) -> np.ndarray:
    """ARIMA univariado, sem exógenas nem sazonalidade — baseline estatístico
    simples (não ingênuo) para comparação. Requer `pmdarima` instalado
    (`!pip install pmdarima -q` no notebook).
    """
    import pmdarima as pm

    params = {"d": 1, "seasonal": False, "max_p": 3, "max_q": 3,
              "information_criterion": "bic", "stepwise": True,
              "suppress_warnings": True, "error_action": "ignore"}
    params.update(auto_arima_kwargs)
    modelo = pm.auto_arima(serie_treino, **params)
    previsao, _ = modelo.predict(n_periods=horizonte, return_conf_int=True)
    return np.asarray(previsao)


def compute_all_baselines(serie_treino: pd.Series, horizonte: int) -> dict:
    """Roda os 4 baselines padrão do projeto de uma vez, retornando um
    dicionário {nome: previsão}. Usar isso em vez de chamar cada baseline
    separadamente reduz a repetição no notebook a uma linha por fold.
    """
    return {
        "naive": baseline_naive(serie_treino, horizonte),
        "seasonal_naive": baseline_seasonal_naive(serie_treino, horizonte),
        "rolling_mean_7d": baseline_rolling_mean(serie_treino, horizonte),
        "arima_puro": baseline_arima_puro(serie_treino, horizonte),
    }


# Especificações padrão das 3 variantes SARIMAX competidas no Desafio 1 — ver
# análise na Seção 6/9 do notebook para o racional de cada uma. Mantidas aqui
# como configuração central: mudar uma especificação em um lugar só.
SPECS_SARIMAX_PADRAO = {
    "sarima_classico": {"seasonal": True, "X_cols": None},
    "arimax_fourier": {"seasonal": False, "X_cols": ["dow_sin", "dow_cos", "fim_de_semana", "feriado", "vespera_feriado", "dia_seguinte_feriado"]},
    "sarimax_hibrido": {"seasonal": True, "X_cols": ["feriado", "vespera_feriado", "dia_seguinte_feriado"]},
    "arimax_fourier_parcimonioso": {"seasonal": False, "X_cols": ["fim_de_semana", "feriado", "vespera_feriado", "dia_seguinte_feriado"]},
}


def rodar_variante_sarimax(
    nome: str,
    spec: dict,
    serie_treino: pd.Series,
    serie_teste: pd.Series,
    exog_treino: pd.DataFrame | None = None,
    exog_teste: pd.DataFrame | None = None,
    **auto_arima_kwargs,
) -> dict:
    """Ajusta uma variante SARIMAX (definida por `spec`, ver
    `SPECS_SARIMAX_PADRAO`) e prevê o horizonte de `serie_teste`.

    `spec` precisa ter as chaves `seasonal` (bool) e `X_cols` (lista de
    colunas de `exog_treino`/`exog_teste` a usar, ou `None` para não usar
    exógenas). `d=1`, `max_p=3`, `max_q=3` e `information_criterion='bic'`
    são os padrões do projeto (ver EDA complementar, Seção 3, para o
    racional de `d=1`) — sobrescrevíveis via `auto_arima_kwargs`.

    Requer `pmdarima` instalado.
    """
    import pmdarima as pm

    X_treino = exog_treino[spec["X_cols"]] if spec["X_cols"] else None
    X_teste = exog_teste[spec["X_cols"]] if spec["X_cols"] else None

    params = {"d": 1, "seasonal": spec["seasonal"], "m": 7 if spec["seasonal"] else 1,
              "max_p": 3, "max_q": 3, "information_criterion": "bic",
              "stepwise": True, "suppress_warnings": True, "error_action": "ignore"}
    params.update(auto_arima_kwargs)

    modelo = pm.auto_arima(serie_treino, X=X_treino, **params)
    horizonte = len(serie_teste)
    previsao, ic = modelo.predict(n_periods=horizonte, X=X_teste, return_conf_int=True)
    previsao = np.asarray(previsao)  # nunca deixar como pd.Series — evita o bug de indexação [0] com DatetimeIndex

    return {
        "nome": nome, "modelo": modelo, "previsao": previsao, "ic": ic,
        "ordem": modelo.order, "ordem_sazonal": modelo.seasonal_order,
        "bic": round(modelo.bic(), 1), "aicc": round(modelo.aicc(), 1),
    }


def construir_exogenas_futuras(
    data_inicio: str,
    periodos: int,
    colunas: list[str] | None = None,
) -> pd.DataFrame:
    """Constrói o bloco de variáveis exógenas de calendário para datas
    futuras (fora da base histórica) — todas conhecidas *a priori*, sem
    depender de nenhum dado observado, então seguras de projetar à frente.

    Requer o pacote `holidays` instalado; sem ele, a coluna `feriado` e
    derivadas ficam zeradas (com aviso via `logger`, se fornecido no
    notebook — aqui a função só constrói o DataFrame).

    `colunas`, se fornecido, seleciona um subconjunto (ex.: para uma
    variante que só usa algumas exógenas) — na mesma ordem de
    `SPECS_SARIMAX_PADRAO[...]['X_cols']`.
    """
    datas_futuras = pd.date_range(data_inicio, periods=periodos, freq="D")

    try:
        import holidays
        anos = sorted({datas_futuras.min().year, datas_futuras.max().year})
        feriados_br = holidays.Brazil(years=anos)
        feriados_dates = set(pd.to_datetime(list(feriados_br.keys())).date)
    except ImportError:
        feriados_dates = set()

    exog = pd.DataFrame(index=datas_futuras)
    exog["fim_de_semana"] = (datas_futuras.dayofweek >= 5).astype(int)
    exog["feriado"] = pd.Series(datas_futuras.date, index=datas_futuras).isin(feriados_dates).astype(int)
    exog["vespera_feriado"] = pd.Series((datas_futuras + pd.Timedelta(days=1)).date, index=datas_futuras).isin(feriados_dates).astype(int)
    exog["dia_seguinte_feriado"] = pd.Series((datas_futuras - pd.Timedelta(days=1)).date, index=datas_futuras).isin(feriados_dates).astype(int)
    exog["dow_sin"] = np.sin(2 * np.pi * datas_futuras.dayofweek / 7)
    exog["dow_cos"] = np.cos(2 * np.pi * datas_futuras.dayofweek / 7)

    return exog[colunas] if colunas else exog


def monitorar_teto_contratual(previsao_periodo: float, teto_periodo: float | None, ic_superior: float | None = None) -> dict | None:
    """Compara uma previsão (ex.: W+1) contra um teto contratual real.

    `teto_periodo` DEVE vir de um dado contratual/OLA real, fornecido por
    quem tem acesso a essa informação de negócio — nunca de um valor
    assumido ou estimado pela equipe de dados. Retorna None se
    `teto_periodo` não for fornecido, em vez de inventar um limite.
    """
    if teto_periodo is None:
        return None
    pct_atingimento = (previsao_periodo / teto_periodo) * 100
    pct_atingimento_pessimista = (ic_superior / teto_periodo) * 100 if ic_superior is not None else None
    if pct_atingimento >= 100:
        status = "CRÍTICO — projeção pontual já ultrapassa o teto"
    elif pct_atingimento_pessimista is not None and pct_atingimento_pessimista >= 100:
        status = "ATENÇÃO — dentro do teto na previsão pontual, mas o cenário pessimista (IC superior) ultrapassa"
    elif pct_atingimento >= 80:
        status = "ATENÇÃO — projeção próxima do teto"
    else:
        status = "OK"
    return {"previsao_periodo": previsao_periodo, "teto_periodo": teto_periodo,
            "pct_atingimento": round(pct_atingimento, 1), "status": status}


def detectar_saltos_anomalos(serie: pd.Series, limiar_desvios: float = 3.0) -> pd.DataFrame:
    """Identifica dias em que a variação dia a dia (`diff()`) foge muito do
    padrão típico — `limiar_desvios` desvios-padrão da própria série de
    diferenças. Usado para achar saltos abruptos (ex.: incidente em massa
    causando um pico de chamados) que nenhum modelo de série temporal
    baseado só no próprio histórico consegue prever, e que podem estar
    inflando artificialmente métricas de erro em um fold específico.

    Retorna um DataFrame com a data, o valor, a variação do dia anterior,
    e quantos desvios-padrão essa variação representa — vazio se nenhum
    salto passar do limiar.
    """
    diffs = serie.diff().dropna()
    z = (diffs - diffs.mean()) / diffs.std()
    anomalos = z[z.abs() > limiar_desvios]
    return pd.DataFrame({
        "data": anomalos.index,
        "valor": serie.loc[anomalos.index].values,
        "variacao_dia_anterior": diffs.loc[anomalos.index].values,
        "desvios_padrao": z.loc[anomalos.index].round(2).values,
    }).reset_index(drop=True)


def bootstrap_prediction_interval(
    residuos: np.ndarray,
    previsao_pontual: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    random_state: int = 42,
) -> dict:
    """Constrói um intervalo de previsão por reamostragem bootstrap dos
    RESÍDUOS observados do modelo, em vez de assumir resíduos
    gaussianos (o padrão do `predict(return_conf_int=True)` do pmdarima).

    Motivação direta: quando os resíduos do modelo têm curtose muito
    acima de 3 (cauda pesada — comum quando há dias de pico atípico na
    série), o intervalo de confiança gaussiano tende a ser estreito
    demais. Reamostrar os resíduos reais preserva a forma real da
    distribuição de erro, sem assumir normalidade.

    Retorna, para cada ponto de `previsao_pontual`, os limites inferior
    e superior do intervalo (arrays do mesmo tamanho).
    """
    rng = np.random.default_rng(random_state)
    residuos = np.asarray(residuos)
    previsao_pontual = np.asarray(previsao_pontual)
    alpha = (1 - ci) / 2

    amostras_residuo = rng.choice(residuos, size=(n_boot, len(previsao_pontual)), replace=True)
    trajetorias = previsao_pontual[np.newaxis, :] + amostras_residuo

    return {
        "ic_inferior": np.quantile(trajetorias, alpha, axis=0),
        "ic_superior": np.quantile(trajetorias, 1 - alpha, axis=0),
    }



def log1p_bias_corrected_forecast(previsao_log1p: np.ndarray, residuos_log1p_treino: np.ndarray) -> np.ndarray:
    """Reverte uma previsão feita em escala `log1p` de volta para a escala
    original, com correção de viés (estimador de suavização de Duan).

    Motivação: `np.expm1(previsao_log1p)` sozinho é um erro sutil e comum —
    a esperança de uma transformação convexa (exponencial) NÃO é igual à
    transformação da esperança (desigualdade de Jensen). Reverter sem
    correção SUBESTIMA sistematicamente o valor esperado na escala
    original, especialmente quando a variância dos resíduos é grande (que é
    exatamente o caso aqui — ver o teste de heterocedasticidade do Desafio
    1). O fator de suavização usa os resíduos IN-SAMPLE do próprio ajuste em
    log1p — nunca dados de teste.
    """
    fator_suavizacao = float(np.mean(np.exp(residuos_log1p_treino)))
    return np.exp(previsao_log1p) * fator_suavizacao - 1


def diagnostico_residuos(modelo_ajustado) -> dict:
    """Roda os testes estatísticos padrão de diagnóstico de resíduos sobre
    um modelo SARIMAX/ARIMA já ajustado (objeto pmdarima ou o
    `.arima_res_` do statsmodels por trás dele): Ljung-Box (autocorrelação
    residual), Jarque-Bera (normalidade) e Breusch-Pagan (heterocedasticidade
    condicional aos valores ajustados).

    Retorna um dicionário simples de {teste: (estatística, p-valor)} — a
    INTERPRETAÇÃO de cada teste (o que fazer se falhar) fica no notebook,
    em contexto, porque a ação correta depende do que já se sabe sobre os
    dados (ex.: heterocedasticidade aqui já era esperada pelo crescimento
    forte da série, não é uma surpresa isolada).
    """
    from statsmodels.stats.diagnostic import acorr_ljungbox, het_breuschpagan
    from statsmodels.stats.stattools import jarque_bera

    resultado_sm = modelo_ajustado.arima_res_ if hasattr(modelo_ajustado, "arima_res_") else modelo_ajustado
    residuos = np.asarray(resultado_sm.resid)
    valores_ajustados = np.asarray(resultado_sm.fittedvalues)

    lb = acorr_ljungbox(residuos, lags=[1], return_df=True)
    jb_stat, jb_p, skew, kurtosis = jarque_bera(residuos)

    # Breusch-Pagan precisa de uma matriz de regressores; usamos os valores ajustados como proxy do nível
    import statsmodels.api as sm
    X_bp = sm.add_constant(valores_ajustados)
    bp_stat, bp_p, _, _ = het_breuschpagan(residuos, X_bp)

    return {
        "ljung_box_p": round(float(lb["lb_pvalue"].iloc[0]), 4),
        "jarque_bera_stat": round(float(jb_stat), 2),
        "jarque_bera_p": round(float(jb_p), 4),
        "skew": round(float(skew), 2),
        "kurtosis": round(float(kurtosis), 2),
        "breusch_pagan_stat": round(float(bp_stat), 2),
        "breusch_pagan_p": round(float(bp_p), 4),
    }


# =====================================================================
# 15. CLASSIFICAÇÃO DE EVENTO RARO — CatBoost, Optuna, avaliação (Desafio 3)
# =====================================================================
# Mesma filosofia da Seção 14: a mecânica repetida entre folds mora aqui;
# QUAIS features usar, QUAL fold é o de produção, e QUAL custo de negócio
# calibra o threshold continuam decisão do notebook, em contexto.
#
# Disciplina que percorre toda esta seção (não relaxar em nenhuma função):
# nunca calcular estatística baseada no alvo (target encoding, shrinkage de
# taxa, o próprio ajuste do CatBoost) fora do bloco de treino de um fold —
# é exatamente o erro que motivou trocar a GRU original pelo CatBoost.

def aplicar_fold_por_timestamp(
    df: pd.DataFrame,
    time_col: str,
    fold: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recorta um DataFrame de granularidade fina (ex.: 1 linha por chamado)
    nos limites de um fold gerado por `generate_expanding_folds` — a mesma
    fronteira de semanas usada no Desafio 1, agora aplicada por timestamp
    de linha em vez de por índice de série temporal.

    Retorna (df_treino, df_teste), ambos cópias independentes (`.copy()`)
    para que qualquer transformação feita em um não vaze para o outro.
    """
    treino_mask = (df[time_col] >= fold["train_start"]) & (df[time_col] <= fold["train_end"])
    teste_mask = (df[time_col] >= fold["test_start"]) & (df[time_col] <= fold["test_end"])
    return df.loc[treino_mask].copy(), df.loc[teste_mask].copy()



def preparar_categoricas_catboost(df: pd.DataFrame, cat_features: list[str], rotulo_ausente: str = "Ausente") -> pd.DataFrame:
    """Converte as colunas categóricas para string, com um rótulo explícito
    no lugar de nulo — necessário porque o CatBoost (nesta versão) não
    aceita `NaN` bruto do pandas em coluna categórica de tipo `object`
    (erro: "cat_features must be integer or string... NaN values should
    be converted to string").

    Isso NÃO é imputação — o objetivo continua sendo o mesmo de sempre no
    projeto (nulo é sua própria categoria informativa, nunca preenchido
    com um valor plausível). A diferença é só a representação: em vez de
    `NaN` do pandas, o nulo vira o rótulo `rotulo_ausente` como string —
    o CatBoost enxerga isso como uma categoria própria, exatamente como
    seria com o NaN nativo, só que sem o erro de tipo.

    Retorna uma CÓPIA do DataFrame — as colunas fora de `cat_features`
    não são tocadas.
    """
    df_out = df.copy()
    for col in cat_features:
        df_out[col] = df_out[col].astype("object").where(df_out[col].notna(), rotulo_ausente).astype(str)
    return df_out


def treinar_catboost_fold(
    df_treino: pd.DataFrame,
    df_teste: pd.DataFrame,
    target_col: str,
    cat_features: list[str],
    text_features: list[str] | None = None,
    params: dict | None = None,
    time_col: str | None = None,
    random_state: int = 42,
) -> dict:
    """Treina um CatBoostClassifier num fold e retorna o modelo e as
    probabilidades previstas no teste.

    Decisões fixas do projeto, não parametrizáveis por engano:
    - `auto_class_weights='Balanced'` — ajusta a função de perda pela
      classe rara sem gerar nenhum dado sintético (decisão documentada:
      sem SMOTE/SMOTEENN).
    - Categóricas (`cat_features`) entram BRUTAS — nenhum one-hot, nenhum
      target encoding manual. O Ordered Target Statistics do próprio
      CatBoost calcula isso dentro do ajuste, usando só o treino deste
      fold, sem vazamento.
    - `text_features`, se fornecido, é processado nativamente pelo
      CatBoost (BoW/embeddings internos) — sem TF-IDF manual.

    Se `time_col` for passado, a coluna é removida da matriz de features
    antes de montar o Pool (proteção contra o erro comum de deixar um
    timestamp bruto entrar como se fosse feature numérica — o CatBoost
    quebra com um erro de tipo confuso quando isso acontece).
    """
    from catboost import CatBoostClassifier, Pool

    params_padrao = {
        "iterations": 500, "learning_rate": 0.05, "depth": 6, "l2_leaf_reg": 3.0,
        "auto_class_weights": "Balanced", "eval_metric": "PRAUC",
        "random_state": random_state, "verbose": False,
    }
    if params:
        params_padrao.update(params)

    colunas_a_dropar = [target_col] + ([time_col] if time_col else [])
    X_treino, y_treino = df_treino.drop(columns=colunas_a_dropar), df_treino[target_col]
    X_teste, y_teste = df_teste.drop(columns=colunas_a_dropar), df_teste[target_col]

    pool_treino = Pool(X_treino, y_treino, cat_features=cat_features, text_features=text_features or [])
    pool_teste = Pool(X_teste, y_teste, cat_features=cat_features, text_features=text_features or [])

    modelo = CatBoostClassifier(**params_padrao)
    modelo.fit(pool_treino, eval_set=pool_teste, use_best_model=False)

    y_score_teste = modelo.predict_proba(pool_teste)[:, 1]
    return {"modelo": modelo, "y_true": y_teste.values, "y_score": y_score_teste, "params": params_padrao}


def otimizar_hiperparametros_catboost(
    df_treino_fold: pd.DataFrame,
    target_col: str,
    cat_features: list[str],
    text_features: list[str] | None,
    time_col: str,
    n_trials: int = 30,
    frac_validacao: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Busca de hiperparâmetros do CatBoost via Optuna, feita ESTRITAMENTE
    dentro do treino de um fold — nunca na base completa.

    Para não vazar nem informação temporal dentro da própria busca, o
    treino do fold é subdividido de forma causal: os últimos
    `frac_validacao` (por tempo, não aleatório) viram validação interna do
    Optuna; o restante, mais antigo, é o sub-treino. Depois de escolher os
    melhores hiperparâmetros, quem decide o modelo final do fold (treinado
    com 100% do treino do fold) é o notebook, não esta função — ela só
    devolve os parâmetros vencedores.
    """
    import optuna
    from catboost import CatBoostClassifier, Pool
    from sklearn.metrics import average_precision_score

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    df_ordenado = df_treino_fold.sort_values(time_col)
    corte = int(len(df_ordenado) * (1 - frac_validacao))
    sub_treino, sub_valid = df_ordenado.iloc[:corte], df_ordenado.iloc[corte:]

    if sub_valid[target_col].sum() == 0:
        raise ValueError(
            "A fatia de validação interna do Optuna não tem nenhum positivo — "
            "aumente frac_validacao ou revise o tamanho do fold antes de continuar."
        )

    # time_col só serve para ordenar — precisa sair da matriz de features antes do Pool,
    # senão o CatBoost tenta tratar um timestamp como número (ou categoria de altíssima
    # cardinalidade) e quebra.
    colunas_a_dropar = [target_col, time_col]
    X_sub_treino, y_sub_treino = sub_treino.drop(columns=colunas_a_dropar), sub_treino[target_col]
    X_sub_valid, y_sub_valid = sub_valid.drop(columns=colunas_a_dropar), sub_valid[target_col]
    pool_sub_treino = Pool(X_sub_treino, y_sub_treino, cat_features=cat_features, text_features=text_features or [])
    pool_sub_valid = Pool(X_sub_valid, y_sub_valid, cat_features=cat_features, text_features=text_features or [])

    def objetivo(trial: "optuna.Trial") -> float:
        params = {
            "iterations": trial.suggest_int("iterations", 200, 800),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "depth": trial.suggest_int("depth", 3, 8),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0, log=True),
            "auto_class_weights": "Balanced",
            "eval_metric": "PRAUC",
            "random_state": random_state,
            "verbose": False,
        }
        modelo = CatBoostClassifier(**params)
        modelo.fit(pool_sub_treino, eval_set=pool_sub_valid, early_stopping_rounds=30, use_best_model=True)
        y_score = modelo.predict_proba(pool_sub_valid)[:, 1]
        return average_precision_score(y_sub_valid, y_score)

    estudo = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=random_state))
    estudo.optimize(objetivo, n_trials=n_trials, show_progress_bar=False)

    return {"melhores_params": estudo.best_params, "melhor_pr_auc_validacao": estudo.best_value, "estudo": estudo}


def avaliar_classificador_raro(
    y_true: np.ndarray,
    y_score: np.ndarray,
    k_list: list = (10, 20, 50),
    n_boot: int = 1000,
    random_state: int = 42,
) -> dict:
    """Pacote de avaliação padrão do projeto para classificação de evento
    raro: PR-AUC como métrica primária (com IC por bootstrap), ROC-AUC como
    referência secundária (sabidamente otimista sob desbalanceamento
    extremo — não usar como decisão principal), e Precision@K para cada K
    em `k_list` (reflete o uso real como fila priorizada).
    """
    from sklearn.metrics import average_precision_score, roc_auc_score

    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)

    pr_auc_ic = bootstrap_metric_ci(y_true, y_score, average_precision_score, n_boot=n_boot, random_state=random_state)
    roc_auc = float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else float("nan")

    precisao_em_k = {f"precision_at_{k}": round(precision_at_k(y_true, y_score, k), 4) for k in k_list}

    return {
        "pr_auc": round(pr_auc_ic["valor_pontual"], 4),
        "pr_auc_ic_inferior": round(pr_auc_ic["ic_inferior"], 4),
        "pr_auc_ic_superior": round(pr_auc_ic["ic_superior"], 4),
        "roc_auc_referencia": round(roc_auc, 4),
        "n_positivos": int(y_true.sum()),
        "n_total": int(len(y_true)),
        **precisao_em_k,
    }


def treinar_catboost_producao(
    df: pd.DataFrame,
    target_col: str,
    cat_features: list[str],
    text_features: list[str] | None,
    params: dict,
    time_col: str | None = None,
    random_state: int = 42,
) -> "CatBoostClassifier":
    """Treina o modelo final de produção com 100% dos dados disponíveis —
    sem `eval_set`, porque não há dado de teste (por definição: é o
    modelo que vai para produção, não uma rodada de validação).

    Existe como função separada de `treinar_catboost_fold` (em vez de
    reaproveitá-la passando um conjunto de teste vazio) porque o CatBoost
    levanta erro (`Labels variable is empty`) ao tentar montar um Pool de
    avaliação vazio — um detalhe fácil de esquecer que vale documentar
    aqui em vez de deixar quem for rodar o notebook redescobrir sozinho.
    """
    from catboost import CatBoostClassifier, Pool

    params_finais = dict(params)
    params_finais.setdefault("auto_class_weights", "Balanced")
    params_finais.setdefault("eval_metric", "PRAUC")
    params_finais.setdefault("random_state", random_state)
    params_finais.setdefault("verbose", False)

    colunas_a_dropar = [target_col] + ([time_col] if time_col else [])
    X, y = df.drop(columns=colunas_a_dropar), df[target_col]
    pool = Pool(X, y, cat_features=cat_features, text_features=text_features or [])

    modelo = CatBoostClassifier(**params_finais)
    modelo.fit(pool)
    return modelo


def calibrar_threshold_por_custo(
    y_true: np.ndarray,
    y_score: np.ndarray,
    custo_falso_positivo: float,
    custo_falso_negativo: float,
) -> dict:
    """Encontra, na curva Precision-Recall, o threshold que minimiza o
    custo esperado — em vez do padrão arbitrário de 0,5.

    `custo_falso_positivo` e `custo_falso_negativo` são SEMPRE parâmetros
    de entrada, nunca valores fixos assumidos por esta função — mobilizar
    um analista à toa (falso positivo) e deixar um SLA estourar sem alerta
    (falso negativo) têm custos de negócio reais, mas diferentes, que só
    quem opera a área consegue estimar. Sem esses dois números fornecidos
    de forma explícita, não existe threshold "ótimo" — só um custo
    relativo assumido, e isso precisa ficar visível a quem usa a função.
    """
    from sklearn.metrics import precision_recall_curve

    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    precisao, recall, thresholds = precision_recall_curve(y_true, y_score)

    n_positivos = y_true.sum()
    n_negativos = len(y_true) - n_positivos

    # Para cada threshold candidato: FN esperado = (1-recall)*positivos ; FP esperado = positivos_previstos - VP
    custos = []
    for i, thr in enumerate(thresholds):
        vp = recall[i] * n_positivos
        fn = n_positivos - vp
        vp_mais_fp = vp / precisao[i] if precisao[i] > 0 else 0
        fp = vp_mais_fp - vp
        custo_total = fp * custo_falso_positivo + fn * custo_falso_negativo
        custos.append(custo_total)

    idx_otimo = int(np.argmin(custos)) if custos else 0
    return {
        "threshold_otimo": float(thresholds[idx_otimo]) if len(thresholds) else 0.5,
        "precisao_no_threshold": float(precisao[idx_otimo]),
        "recall_no_threshold": float(recall[idx_otimo]),
        "custo_esperado": float(custos[idx_otimo]) if custos else float("nan"),
    }


# =====================================================================
# =====================================================================
# ############   FIM DO ESCOPO DO PROJETO — A PARTIR DAQUI É SPRINT   ############
# =====================================================================
# =====================================================================
#
# Tudo ANTES desta linha pertence ao projeto real entregue à Locaweb:
# Bronze/Silver/Gold, Desafio 1 (SARIMAX), Desafio 3 (CatBoost), e onde
# o Desafio 4 (SHAP) vai entrar. Nenhum notebook do challenge em si
# depende do que vem a seguir.
#
# Tudo A PARTIR DAQUI é exigência acadêmica de disciplina da FIAP
# (Sprint 3 de Machine Learning e de Deep Learning) — um "modelo simples
# e interpretável" e uma ANN comparando com clusterização, exigidos pelo
# enunciado da disciplina, não pelo desafio da Locaweb. Fica separado
# aqui, no mesmo arquivo, só para não obrigar a manter dois .py
# sincronizados no Drive — mas a fronteira é esta, e é para ficar óbvia.
#
# Se algo desta seção um dia precisar ser reaproveitado pelo projeto
# principal, mova a função para ANTES desta divisória nesse momento —
# não antes disso.


# =====================================================================
# SPRINT 3 — MACHINE LEARNING (regressão logística interpretável)
# =====================================================================

def preparar_features_sklearn(
    df_treino: pd.DataFrame,
    df_teste: pd.DataFrame,
    cat_features: list[str],
    num_features: list[str],
    target_col: str,
):
    """Prepara matrizes de feature prontas para scikit-learn (regressão
    logística, redes neurais) a partir de um par treino/teste de um fold:
    one-hot das categóricas e padronização (`StandardScaler`) das
    numéricas, ambos ajustados SÓ no treino e aplicados (`transform`) no
    teste — a mesma disciplina anti-vazamento do projeto principal, aqui
    aplicada para modelos que (diferente do CatBoost) exigem entrada só
    numérica.

    Categorias vistas no teste mas não no treino são ignoradas no one-hot
    (`handle_unknown='ignore'`) em vez de gerar erro — no mundo real, uma
    categoria nova apareceria eventualmente, e o modelo precisa lidar com
    isso sem quebrar.

    Retorna `(X_treino, X_teste, y_treino, y_teste, nomes_features)`.

    Usado por: EC_Sprint_3_..._ML.ipynb (regressão logística). Fora do
    escopo do projeto principal — ver divisória acima.
    """
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    y_treino, y_teste = df_treino[target_col].values, df_teste[target_col].values

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cat_treino = encoder.fit_transform(df_treino[cat_features])
    cat_teste = encoder.transform(df_teste[cat_features])
    nomes_cat = list(encoder.get_feature_names_out(cat_features))

    scaler = StandardScaler()
    num_treino = scaler.fit_transform(df_treino[num_features])
    num_teste = scaler.transform(df_teste[num_features])

    X_treino = np.hstack([cat_treino, num_treino])
    X_teste = np.hstack([cat_teste, num_teste])
    nomes_features = nomes_cat + list(num_features)

    return X_treino, X_teste, y_treino, y_teste, nomes_features


class _ResultadoLogitBootstrap:
    """Objeto leve que imita a interface do resultado do `statsmodels`
    (`.params`, `.pvalues`, `.conf_int()`) para que o código do notebook
    não precise mudar dependendo de qual dos três caminhos de
    `ajustar_logit_interpretavel` foi usado."""

    def __init__(self, params: np.ndarray, pvalues: np.ndarray, ic_inferior: np.ndarray, ic_superior: np.ndarray):
        self.params = params
        self.pvalues = pvalues
        self._ic_inferior = ic_inferior
        self._ic_superior = ic_superior

    def conf_int(self) -> np.ndarray:
        return np.column_stack([self._ic_inferior, self._ic_superior])


def _ajustar_logit_bootstrap(X_com_constante: np.ndarray, y: np.ndarray, n_boot: int = 300, random_state: int = 42) -> "_ResultadoLogitBootstrap":
    """Última camada de segurança: reamostra (com reposição) as linhas
    reais e reajusta uma regressão logística regularizada (`sklearn`,
    mais robusta numericamente que o `statsmodels` para esse cenário)
    a cada reamostragem. Coeficiente, IC e p-valor saem da distribuição
    empírica dos coeficientes entre as reamostragens — não depende de
    inverter nenhuma matriz Hessiana, então não quebra mesmo quando o
    ajuste regularizado direto (`fit_regularized`) ainda falha ao
    calcular o erro-padrão analítico (caso de múltiplas categorias
    sem nenhum positivo ao mesmo tempo).

    p-valor aqui é uma versão bootstrap (dobro da menor fração de
    reamostragens em que o coeficiente ficou do lado oposto de zero) —
    uma aproximação de propósito, não um p-valor de teste de hipótese
    clássico.
    """
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(random_state)
    n = len(y)
    coeficientes_bootstrap = []
    tentativas, max_tentativas = 0, n_boot * 10

    while len(coeficientes_bootstrap) < n_boot and tentativas < max_tentativas:
        tentativas += 1
        idx = rng.integers(0, n, size=n)
        y_boot = y[idx]
        if y_boot.sum() == 0 or y_boot.sum() == len(y_boot):
            continue  # reamostragem sem os dois valores de alvo não ajusta nada
        X_boot = X_com_constante[idx]
        modelo_boot = LogisticRegression(C=1.0, max_iter=2000, solver="lbfgs", fit_intercept=False)
        modelo_boot.fit(X_boot, y_boot)
        coeficientes_bootstrap.append(modelo_boot.coef_[0])

    coeficientes_bootstrap = np.array(coeficientes_bootstrap)
    params = coeficientes_bootstrap.mean(axis=0)
    ic_inferior = np.percentile(coeficientes_bootstrap, 2.5, axis=0)
    ic_superior = np.percentile(coeficientes_bootstrap, 97.5, axis=0)

    frac_positivo = (coeficientes_bootstrap > 0).mean(axis=0)
    frac_negativo = (coeficientes_bootstrap < 0).mean(axis=0)
    pvalues = 2 * np.minimum(frac_positivo, frac_negativo)
    pvalues = np.clip(pvalues, 0, 1)

    return _ResultadoLogitBootstrap(params, pvalues, ic_inferior, ic_superior)


def ajustar_logit_interpretavel(
    df_treino: pd.DataFrame,
    cat_features: list[str],
    num_features: list[str],
    target_col: str,
    random_state: int = 42,
):
    """Ajusta uma regressão logística interpretável, com três camadas de
    robustez que caem em cascata conforme necessário (a maioria das
    execuções usa só a primeira):

    1. `statsmodels.Logit.fit()` — ajuste clássico, p-valores exatos.
    2. Se (1) falhar (`LinAlgError`/não converge): `fit_regularized`
       (L2/Ridge) — sempre converge no ajuste em si, mas o cálculo do
       erro-padrão analítico ainda pode falhar se várias categorias
       tiverem zero positivos ao mesmo tempo.
    3. Se (2) também falhar: bootstrap de uma regressão logística
       regularizada via `sklearn` (`_ajustar_logit_bootstrap`) — não
       depende de inverter nenhuma matriz, funciona mesmo no cenário
       mais degenerado.

    Motivação de fundo (por que isso é necessário neste projeto e não
    seria em um dataset qualquer): com ~17 equipes dividindo menos de
    1% de positivos, é comum alguma equipe não ter NENHUM positivo no
    treino de um fold — separação quase-completa, que quebra a
    matriz Hessiana usada tanto no ajuste clássico quanto (às vezes)
    no cálculo de erro-padrão do ajuste regularizado. Isso não é
    resolvido removendo outras features — a causa é a escassez de
    positivos em certas categorias, não multicolinearidade entre as
    features escolhidas.

    Ajustada numa base única (ex.: todo o treino do fold de produção),
    não por fold — é uma ferramenta de INTERPRETAÇÃO complementar, não
    substitui a validação walk-forward já feita com `sklearn`.

    Retorna `(resultado, nomes_features, metodo)` — `resultado` tem
    `.params`/`.pvalues`/`.conf_int()` disponíveis nos três caminhos;
    `metodo` (`"classico"`, `"regularizado"` ou `"bootstrap"`) indica
    qual foi usado, e deve ser checado antes de interpretar os
    p-valores no notebook (só o `"classico"` é inferência exata).
    """
    import statsmodels.api as sm
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop="first")
    cat_transformado = encoder.fit_transform(df_treino[cat_features])
    nomes_cat = list(encoder.get_feature_names_out(cat_features))

    scaler = StandardScaler()
    num_transformado = scaler.fit_transform(df_treino[num_features])

    X = np.hstack([cat_transformado, num_transformado])
    nomes_features = nomes_cat + list(num_features)
    X_com_constante = sm.add_constant(X)
    y = df_treino[target_col].values

    logger = logging.getLogger("cronos")
    modelo = sm.Logit(y, X_com_constante)
    metodo = "classico"

    try:
        resultado = modelo.fit(disp=0, maxiter=200)
        if not resultado.mle_retvals.get("converged", True):
            raise np.linalg.LinAlgError("MLE não convergiu (mle_retvals['converged'] = False)")
    except (np.linalg.LinAlgError, ValueError) as erro_classico:
        logger.warning(
            "Ajuste clássico do Logit falhou (%s) — provável separação quase-completa "
            "(alguma categoria sem nenhum positivo no treino). Tentando regularização L2/Ridge.",
            type(erro_classico).__name__,
        )
        metodo = "regularizado"
        try:
            resultado = modelo.fit_regularized(alpha=1.0, L1_wt=0.0, disp=0, maxiter=200)
        except (np.linalg.LinAlgError, ValueError) as erro_regularizado:
            logger.warning(
                "Regularização direta também falhou ao calcular erro-padrão (%s) — "
                "provável múltiplas categorias com zero positivos simultaneamente. "
                "Caindo para bootstrap de regressão logística regularizada (sklearn).",
                type(erro_regularizado).__name__,
            )
            metodo = "bootstrap"
            resultado = _ajustar_logit_bootstrap(X_com_constante, y, random_state=random_state)

    return resultado, ["const"] + nomes_features, metodo


# =====================================================================
# SPRINT 3 — DEEP LEARNING (ANN + investigação de clusterização)
# =====================================================================

def investigar_clusters_texto(
    df_treino: pd.DataFrame,
    df_teste: pd.DataFrame,
    text_col: str,
    n_clusters: int = 5,
    random_state: int = 42,
) -> dict:
    """Agrupa `text_col` em clusters temáticos via TF-IDF + K-Means,
    ajustado ESTRITAMENTE no treino (mesma disciplina anti-vazamento do
    resto do projeto) e aplicado (`transform`) no teste.

    Existe para responder à exigência do enunciado da disciplina de DL:
    "investigar o uso de clusterização para evidenciar vantagens
    (existentes ou não) no feature engineering" — o cluster resultante
    é pensado como um substituto de baixa cardinalidade para o sinal de
    Produto/Categoria (63,6% nulos), não como um fim em si.

    Retorna um dicionário com `cluster_treino`/`cluster_teste` (arrays de
    inteiro, prontos para virar uma coluna categórica ou dummy), o
    `silhouette_treino` (métrica de quão bem separados os clusters
    ficaram, calculada só no treino) e os objetos `vectorizer`/`kmeans`
    ajustados, para inspeção posterior (ex.: termos mais representativos
    de cada cluster).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    texto_treino = df_treino[text_col].fillna("").astype(str)
    texto_teste = df_teste[text_col].fillna("").astype(str)

    vectorizer = TfidfVectorizer(max_features=200, min_df=2)
    X_tfidf_treino = vectorizer.fit_transform(texto_treino)
    X_tfidf_teste = vectorizer.transform(texto_teste)

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    cluster_treino = kmeans.fit_predict(X_tfidf_treino)
    cluster_teste = kmeans.predict(X_tfidf_teste)

    # Silhouette em amostra (não na base inteira) por custo computacional — só como
    # diagnóstico de quão bem separados os clusters ficaram, não uma métrica de modelo.
    n_amostra = min(2000, X_tfidf_treino.shape[0])
    idx_amostra = np.random.default_rng(random_state).choice(X_tfidf_treino.shape[0], n_amostra, replace=False)
    silhouette = silhouette_score(X_tfidf_treino[idx_amostra], cluster_treino[idx_amostra]) if n_amostra > n_clusters else float("nan")

    return {
        "cluster_treino": cluster_treino, "cluster_teste": cluster_teste,
        "silhouette_treino": round(float(silhouette), 4),
        "vectorizer": vectorizer, "kmeans": kmeans,
    }


def construir_ann(
    input_dim: int,
    camadas: list[int] = (64, 32),
    dropout: list[float] = (0.3, 0.2),
    learning_rate: float = 0.001,
):
    """Monta e compila uma MLP simples (arquitetura padrão do projeto:
    Dense -> Dropout, repetido, terminando em sigmoid) para classificação
    binária. `camadas` e `dropout` precisam ter o mesmo tamanho — cada
    par define uma camada oculta.

    Arquitetura deliberadamente enxuta: com poucos milhares de exemplos
    elegíveis e ~240 positivos, uma rede grande overfita rápido demais
    para ser útil — a rede aqui é um MLP raso de propósito, não um
    exagero de profundidade que a quantidade de dado não sustenta.
    """
    from tensorflow import keras

    assert len(camadas) == len(dropout), "camadas e dropout precisam ter o mesmo tamanho"

    modelo = keras.Sequential()
    modelo.add(keras.layers.Input(shape=(input_dim,)))
    for n_neuronios, taxa_dropout in zip(camadas, dropout):
        modelo.add(keras.layers.Dense(n_neuronios, activation="relu"))
        modelo.add(keras.layers.Dropout(taxa_dropout))
    modelo.add(keras.layers.Dense(1, activation="sigmoid"))

    modelo.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[keras.metrics.AUC(name="auc"), keras.metrics.AUC(name="pr_auc", curve="PR")],
    )
    return modelo


def treinar_ann_fold(
    df_treino: pd.DataFrame,
    df_teste: pd.DataFrame,
    cat_features: list[str],
    num_features: list[str],
    target_col: str,
    camadas: list[int] = (64, 32),
    dropout: list[float] = (0.3, 0.2),
    learning_rate: float = 0.001,
    epochs: int = 100,
    batch_size: int = 64,
    patience: int = 10,
    time_col: str | None = None,
    verbose: int = 0,
) -> dict:
    """Treina uma ANN num fold, reaproveitando `preparar_features_sklearn`
    para a matriz de entrada (one-hot + padronização, ajustados só no
    treino) e aplicando `class_weight` (não SMOTE) para lidar com o
    desbalanceamento — mesma decisão de projeto usada no CatBoost e na
    regressão logística, agora para a rede neural.

    `EarlyStopping` monitora a PR-AUC de validação (não a loss — com
    desbalanceamento extremo, a loss pode melhorar só por acertar a
    classe majoritária, sem o modelo aprender sinal real da classe rara).
    Uma fatia do próprio treino (últimos 15%, por tempo) vira validação
    interna do Keras.

    **`time_col`**: se fornecido, `df_treino` é ordenado por essa coluna
    ANTES do split interno de validação — sem isso, `validation_split`
    do Keras pega "as últimas 15% linhas do array na ordem em que
    chegaram", que só corresponde aos dias mais recentes se o DataFrame
    já estiver garantidamente ordenado por tempo antes de entrar na
    função. Passar `time_col` remove essa suposição implícita.

    Retorna `(modelo, y_true, y_score, history, nomes_features)`.
    """
    from tensorflow import keras
    from sklearn.utils.class_weight import compute_class_weight

    if time_col is not None:
        df_treino = df_treino.sort_values(time_col)

    X_treino, X_teste, y_treino, y_teste, nomes_features = preparar_features_sklearn(
        df_treino, df_teste, cat_features, num_features, target_col
    )

    pesos = compute_class_weight(class_weight="balanced", classes=np.array([0, 1]), y=y_treino)
    class_weight = {0: pesos[0], 1: pesos[1]}

    modelo = construir_ann(X_treino.shape[1], camadas=camadas, dropout=dropout, learning_rate=learning_rate)

    early_stopping = keras.callbacks.EarlyStopping(
        monitor="val_pr_auc", mode="max", patience=patience, restore_best_weights=True,
    )

    history = modelo.fit(
        X_treino, y_treino,
        validation_split=0.15,  # últimos 15% do array (não embaralhado por padrão -> aproximadamente temporal)
        shuffle=False,
        epochs=epochs, batch_size=batch_size,
        class_weight=class_weight, callbacks=[early_stopping],
        verbose=verbose,
    )

    y_score = modelo.predict(X_teste, verbose=0).ravel()
    return {"modelo": modelo, "y_true": y_teste, "y_score": y_score, "history": history, "nomes_features": nomes_features}


def ajustar_encoder_scaler_producao(
    df: pd.DataFrame,
    cat_features: list[str],
    num_features: list[str],
):
    """Ajusta (`fit`) um `OneHotEncoder` e um `StandardScaler` no
    DataFrame completo — usado só para o modelo de PRODUÇÃO (sem
    conjunto de teste, por definição), diferente de
    `preparar_features_sklearn`, que ajusta por fold com treino/teste
    separados.

    Retorna `(X, y, encoder, scaler)` — `encoder`/`scaler` ajustados
    ficam disponíveis para transformar um chamado novo depois (ver
    `prever_risco_chamado`), sem reajustá-los com o dado de produção.
    """
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cat_transformado = encoder.fit_transform(df[cat_features])

    scaler = StandardScaler()
    num_transformado = scaler.fit_transform(df[num_features])

    X = np.hstack([cat_transformado, num_transformado])
    return X, encoder, scaler


def prever_risco_chamado(modelo, encoder, scaler, cat_features: list[str], num_features: list[str], dados_chamado: dict) -> float:
    """MVP funcional exigido pelo enunciado da disciplina: recebe os
    dados de UM chamado novo (dicionário com as mesmas chaves de
    `cat_features` + `num_features`) e devolve a probabilidade de
    violação de SLA prevista pela ANN — 100% local, sem depender de
    nuvem, provando que a lógica fim-a-fim (dado -> features -> predição)
    funciona de verdade.

    `encoder` e `scaler` são os objetos já ajustados no treino (não
    reajustados aqui — usar um novo chamado para "aprender" o encoding
    seria vazamento na direção oposta: informação de produção vazando
    para dentro do pipeline de treino).
    """
    df_chamado = pd.DataFrame([dados_chamado])
    cat_transformado = encoder.transform(df_chamado[cat_features])
    num_transformado = scaler.transform(df_chamado[num_features])
    X = np.hstack([cat_transformado, num_transformado])
    return float(modelo.predict(X, verbose=0).ravel()[0])
