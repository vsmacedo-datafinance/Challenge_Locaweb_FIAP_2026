# 🕰️ Projeto Chronos | Locaweb Challenge 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?style=for-the-badge&logo=pandas)
![Estatística](https://img.shields.io/badge/Stats-Econometrics-brightgreen?style=for-the-badge)
![Arquitetura](https://img.shields.io/badge/Architecture-Medallion-FFD700?style=for-the-badge)

**Solução de AIOps para previsão de incidentes e tendências operacionais, desenvolvida para o Challenge Locaweb 2026 (FIAP).**

**Repositório:** https://github.com/vsmacedo-datafinance/Challenge_Locaweb_FIAP_2026

## 👥 Equipe

* **Bruno Rosa** — RM563779
* **Danilo Alves** — RM564109
* **Enzo Cremaschi** — RM562058
* **Vinícius Macedo** — RM561911

---

## 📑 Sumário

- [O que esta solução entrega](#-o-que-esta-solução-entrega)
- [Ordem de Leitura](#-ordem-de-leitura)
- [Arquitetura de Dados](#️-arquitetura-de-dados)
- [Resultados por Desafio](#-resultados-por-desafio)
- [Rigor Metodológico](#-rigor-metodológico)
- [Saídas para o Dashboard](#-saídas-para-o-dashboard)
- [Estrutura do Repositório](#-estrutura-do-repositório)

---

## 🎯 O que esta solução entrega

Os quatro desafios analíticos do enunciado oficial, mais duas entregas acadêmicas (Machine Learning e Deep Learning), construídos sobre uma arquitetura Medalhão (Bronze/Silver/Gold) com disciplina anti-vazamento de ponta a ponta:

| Desafio | Entrega | Resultado principal |
|---|---|---|
| **1 — Antecipar incidentes** | Previsão de volume D+1/D+7 por prioridade (SARIMAX Bottom-Up) | MAE D+1: **4,07** (P2) e **9,49** (P3) |
| **2 — Identificar tendências** | Decomposição do crescimento por origem e elegibilidade | **113%** do crescimento vem de Monitoramento não-elegível |
| **3 — Projetar impacto nos KPIs** | Classificação de risco de violação de OLA (CatBoost) | PR-AUC **0,1501** — 17x o baseline |
| **4 — Apoiar decisão operacional** | Explicabilidade por chamado (SHAP) | **6 de 10** chamados de maior risco violaram de fato |

Base: 121.811 chamados, dos quais 25.156 elegíveis para KPI (238 violações — 0,95%). Cobertura de código: **44 testes automatizados**.

---

## 📖 Ordem de Leitura

1. **`01_bronze_ingestao.ipynb`** — ingestão bruta, validação de schema e domínio.
2. **`EDA_Completa.ipynb`** — análise exploratória principal.
3. **`EDA_Complementar.ipynb`** — aprofundamento e revisão de hipóteses.
4. **`02_silver_limpeza.ipynb`** — regras de negócio, cada uma com evidência estatística.
5. **`03_gold_features.ipynb`** — engenharia de features e as três tabelas de consumo.
6. **`Sprint_3_ML.ipynb`** / **`Sprint_3_DL.ipynb`** — entregas acadêmicas.
7. **`04_Sarimax_Previsão_de_Volume.ipynb`** — Desafio 1.
8. **`07_Tendencias_Operacionais.ipynb`** — Desafio 2.
9. **`05_Catboost_Risco_de_Violação_de_OLA.ipynb`** — Desafio 3.
10. **`06_SHAP_Explicabilidade.ipynb`** — Desafio 4 (consome o modelo salvo pelo notebook 05).

---

## 🏗️ Arquitetura de Dados

Toda lógica reutilizável centralizada em `src/utils.py`, com divisória explícita separando funções do projeto das funções exclusivas das Sprints acadêmicas.

### 🥉 Bronze — Ingestão e Auditoria
Validação estrita de schema (19 colunas do dicionário), validação de domínio categórico, e metadados de proveniência (`_ingested_at`, `_source_layer`, `_source_hash` SHA-256). Nenhuma regra de negócio.

### 🥈 Silver — Limpeza com Evidência
Cada regra carrega o teste estatístico que a justifica:
* **Filtro de regime:** exclusão de 2023-2024 (0,6% da base) — perfil categórico sistematicamente distinto de 2025.
* **Missingness MNAR:** χ² = 36.726,99 (p ≈ 0) confirma que os nulos de `Produto`/`Categoria` dependem estruturalmente da origem automática. Nenhuma imputação — criada a flag de cobertura.
* **Winsorização:** cauda de `Duração` tratada com capping no P99 + `log1p`.
* **Texto determinístico:** normalização sem vocabulário aprendido, evitando vazamento.

### 🥇 Gold — Feature Store
Três tabelas isoladas, com contrato de dados gerado automaticamente:
1. **`gold_volume_diario`** — série diária elegível e bruta, por prioridade, com variáveis cíclicas e lags causais (t-1 a t-7).
2. **`gold_tendencias_macro`** — agregação semanal com dimensão `elegivel_kpi`.
3. **`gold_chamados_risco`** — matriz granular de predição, com exclusão cirúrgica de variáveis pós-evento (`Resolvido`, `Duração`, `Status`, `Código de fechamento`).

Distribuição real de `Prioridade`: 4-Baixa (64.580), 3-Média (41.260), 2-Alta (15.645), 5-Muito Baixa (325), 1-Crítica (1).

---

## 🚀 Resultados por Desafio

### ✅ Desafio 1 — Previsão de Volume (SARIMAX Bottom-Up)

P2 e P3 são modelados **separadamente** — a decomposição STL confirma dinâmicas distintas (P3 com sazonalidade semanal significativamente mais forte) — e somados apenas na etapa de produção. A seleção de modelo usa erro medido especificamente em **D+1 e D+7**, com validação de origem rolante, que é o critério de avaliação oficial.

| | P2 | P3 |
|---|---|---|
| Especificação vencedora | `sarima_classico` (escala bruta) | `sarimax_hibrido` (escala log1p) |
| MAE D+1 | 4,07 | 9,49 |
| MAE D+7 | 4,32 | 10,10 |
| Previsão W+1 | 96 chamados | 381 chamados |

**W+1 consolidado: 477 chamados elegíveis**, com IC 90% de [273, 788] por bootstrap conjunto (reamostragem pareada, preservando a correlação entre as séries). Validação automática de plausibilidade confirma desvio de -5,4% (P2) e +21,9% (P3) frente à média das últimas 8 semanas.

**Teto Contratual:** 2025 fechou em **125% de atingimento** de volume em ambas as prioridades, medido contra as faixas oficiais do Dicionário de Dados v2. Projeção 2026 mantém o mesmo patamar.

### ✅ Desafio 2 — Tendências Operacionais

Decomposição do crescimento de volume por origem (`Aberto por`) e elegibilidade (`elegivel_kpi`):

* Crescimento total: **+840 chamados/semana** entre as janelas comparadas.
* **113% desse crescimento vem de chamados de Monitoramento não-elegíveis para KPI** — o volume elegível, que representa a demanda operacional real, apresentou queda no mesmo período.
* **Atingimento acumulado de OLA:** P2 em 75% (ritmo recente projeta 50%); P3 em 150%.
* **Cobertura de categorização:** 18,7% no período recente contra 40,0% no anterior.

A leitura de negócio: o aumento aparente de incidentes é dominado por ruído de alertas automáticos, não por crescimento de demanda sobre as equipes.

### ✅ Desafio 3 — Risco de Violação de OLA (CatBoost)

Classificação sob desbalanceamento extremo (0,95% de positivos), sem SMOTE/SMOTEENN em nenhum momento — balanceamento via `auto_class_weights`.

| Métrica | Valor |
|---|---|
| PR-AUC médio (3 folds) | **0,1501** |
| PR-AUC baseline (taxa histórica) | 0,0088 — **17x inferior** |
| ROC-AUC médio | 0,8075 |
| Threshold calibrado (custo 1:15) | 0,6144 |
| Precisão / Recall no threshold | 57,1% / 11,8% |

**Top features:** `descricao_limpa`, `grupo_contagem_historica`, `pressao_fila_7d`.

O threshold é calibrado numa fatia de validação interna e só então aplicado ao conjunto de teste — a precisão reportada é o desempenho real esperado, não o do ponto de corte otimizado sobre o próprio teste.

### ✅ Desafio 4 — Explicabilidade (SHAP)

Explicação em três camadas — global (quais fatores pesam no modelo), local (por que este chamado específico) e descritiva (quais tipos de chamado concentram violação).

* **Fatores de maior peso:** `descricao_limpa` (dominante, 1,8x o segundo colocado), `descricao_contagem_historica` (tende a **reduzir** risco — problema recorrente já tem rotina de resolução), `grupo_contagem_historica`, `grupo_chamados_ultima_hora`.
* **Validação fora da amostra:** PR-AUC de **0,2141** no fold 3, com **6 de 10** chamados apontados como mais críticos violando de fato (taxa base: 1,30%).
* **Concentração de risco:** templates "erro instalacao" (6,7%, n=30) e "problem check postgresql" (3,0%, n=33), reportados com intervalo de Wilson para não confundir amostra pequena com sinal.
* `Grupo designado` — a variável de maior V de Cramér na EDA — aparece em posição distante no ranking SHAP: o efeito de equipe é majoritariamente absorvido pelas features derivadas de carga operacional.

### 📎 Sprints Acadêmicas

| Modelo | PR-AUC (fold 3) | ROC-AUC |
|---|---|---|
| Regressão Logística (ML) | 0,0518 | 0,7756 |
| ANN (DL) | 0,0727 | 0,8033 |
| CatBoost (Desafio 3) | 0,2401 | 0,7808 |

A proximidade dos ROC-AUC contra a distância dos PR-AUC é a evidência direta de por que **PR-AUC é a métrica primária** do projeto. A Sprint de DL inclui MVP funcional local (`prever_risco_chamado`).

---

## 🔬 Rigor Metodológico

**Séries temporais:** ADF/KPSS para determinação de `d=1`; walk-forward em 3 folds temporais estritos; diagnóstico formal de resíduos (Ljung-Box, Breusch-Pagan, Jarque-Bera); intervalo de previsão por bootstrap dos resíduos (a curtose observada invalida a premissa gaussiana); correção de viés de Duan na reversão logarítmica; teste de parcimônia por BIC; piso em zero nas previsões e limites inferiores.

**Classificação:** Optuna dentro de cada fold de treino; Ordered Target Statistics nativo do CatBoost em vez de target encoding manual; guardrail `grupo_baixo_volume` (n < 100) para evitar leitura enganosa de risco em amostra insuficiente; SHAP com verificação da propriedade aditiva (soma das contribuições reproduz exatamente o log-odds previsto).

**Interpretação estatística:** intervalo de Wilson nas taxas por categoria; teste de estabilidade de ranking por tamanho mínimo de amostra; na Sprint de ML, tratamento explícito de separação quase-completa via cascata de três níveis (ajuste clássico → regularização L2 → bootstrap), com o resultado real reportado: apenas 3 de 38 coeficientes estatisticamente significativos, nenhum deles de `Grupo designado`.

---

## 📊 Saídas para o Dashboard

Os notebooks exportam para `data/gold/exports_dashboard/` os artefatos de consumo do MVP de visualização:

* Série diária de volume, elegível e bruta, por prioridade
* Tendências semanais com dimensão de elegibilidade
* Previsão D+1/D+7 com intervalos de confiança
* Painel de risco por chamado, com as três principais razões (SHAP) de cada um
* Atingimento de KPI contra as faixas oficiais

---

## 📁 Estrutura do Repositório

```
.
├── data/
│   ├── bronze/.gitkeep
│   ├── silver/.gitkeep
│   └── gold/.gitkeep
├── notebooks/
│   ├── 01_bronze_ingestao.ipynb
│   ├── 02_silver_limpeza.ipynb
│   ├── 03_gold_features.ipynb
│   ├── 04_Sarimax_Previsão_de_Volume.ipynb
│   ├── 05_Catboost_Risco_de_Violação_de_OLA.ipynb
│   ├── 06_SHAP_Explicabilidade.ipynb
│   ├── 07_Tendencias_Operacionais.ipynb
│   ├── EDA_Completa.ipynb
│   ├── EDA_Complementar.ipynb
│   ├── Sprint_3_ML.ipynb
│   └── Sprint_3_DL.ipynb
├── src/
│   ├── utils.py            # módulo central — projeto + Sprints
│   └── test_utils.py       # 44 testes automatizados
├── .gitattributes
├── requirements.txt
└── README.md
```

> As pastas de `data/` são versionadas vazias (`.gitkeep`) — os parquets ficam no Google Drive montado em runtime.

---
