# 🕰️ Projeto Chronos | Locaweb Challenge 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?style=for-the-badge&logo=pandas)
![Estatística](https://img.shields.io/badge/Stats-Econometrics-brightgreen?style=for-the-badge)
![Arquitetura](https://img.shields.io/badge/Architecture-Medallion-FFD700?style=for-the-badge)

**Repositório oficial do Projeto Chronos, desenvolvido para o Challenge Locaweb 2026 (FIAP).**

**Link do repositório:** https://github.com/vsmacedo-datafinance/Challenge_Locaweb_FIAP_2026

## 👥 Equipe

* **Bruno Rosa** — RM563779
* **Danilo Alves** — RM564109
* **Enzo Cremaschi** — RM562058
* **Vinícius Macedo** — RM561911

---

## 📑 Sumário

- [Resumo Executivo](#-resumo-executivo)
- [Ordem de Leitura Recomendada](#-ordem-de-leitura-recomendada)
- [Arquitetura de Dados (Pipeline)](#️-arquitetura-de-dados-pipeline)
- [Destaques de Engenharia & Rigor Econométrico](#-destaques-de-engenharia--rigor-econométrico)
- [Resultados da Modelagem](#-resultados-da-modelagem)
- [Estrutura do Repositório](#-estrutura-do-repositório)

---

## 🎯 Resumo Executivo

O Projeto Chronos aplica ciência de dados à gestão de incidentes da Locaweb, cobrindo os 4 desafios analíticos do enunciado oficial (previsão de volume, tendências, classificação de risco e explicabilidade) mais duas entregas acadêmicas (Machine Learning e Deep Learning). A arquitetura segue o padrão **Medalhão** (Bronze/Silver/Gold), com **tolerância zero a *data leakage*** e rigor econométrico documentado em cada decisão.

Uma auditoria técnica em duas rodadas (interna + revisão de um segundo modelo de IA) encontrou e corrigiu um **bug real na previsão de produção do Desafio 1** — causado por censura no campo `Entrou para KPI?` — e um **problema de design na explicabilidade do Desafio 4** (SHAP calculado sobre os mesmos dados de treino). As duas correções estão implementadas, testadas (**44 testes automatizados, todos passando**) e validadas com dado real — os 11 notebooks do repositório rodam do início ao fim sem erro, e os números deste README foram conferidos diretamente nas saídas reais mais recentes.

---

## 📖 Ordem de Leitura Recomendada

1. **`01_bronze_ingestao.ipynb`** — ingestão bruta, sem regra de negócio.
2. **`EDA_Completa.ipynb`** — primeira rodada de análise exploratória.
3. **`EDA_Complementar.ipynb`** — segunda rodada, aprofunda/revisa achados da EDA Completa.
4. **`02_silver_limpeza.ipynb`** — limpeza e regras de negócio, cada uma com evidência estatística.
5. **`03_gold_features.ipynb`** — features, série elegível/bruta separada, `tem_incidente_pai` removida (regra oficial do Dicionário v2).
6. **`Sprint_3_ML.ipynb`** e **`Sprint_3_DL.ipynb`** — entregas acadêmicas (regressão logística e ANN), mesma base da Gold.
7. **`04_Sarimax_Previsão_de_Volume.ipynb`** — Desafio 1.
8. **`07_Tendencias_Operacionais.ipynb`** — Desafio 2.
9. **`05_Catboost_Risco_de_Violação_de_OLA.ipynb`** — Desafio 3.
10. **`06_SHAP_Explicabilidade.ipynb`** — Desafio 4 — depende do `.cbm` salvo pelo notebook 05.

---

## 🏗️ Arquitetura de Dados (Pipeline)

Toda a lógica reutilizável está centralizada em `src/utils.py` — com uma divisória explícita separando as funções do projeto principal das funções exclusivas das Sprints acadêmicas de ML/DL. A suíte de **44 testes automatizados** (`src/test_utils.py`) cobre as funções causais, os modelos e as correções mais recentes (detecção de censura, avaliação por horizonte, IC conjunto, SHAP) — rodei a suíte inteira antes de fechar este README, todos os 44 passam.

### 🥉 Camada Bronze
Ingestão sem regra de negócio: validação de schema, validação de domínio, metadados de proveniência (`_ingested_at`, `_source_hash`).

### 🥈 Camada Silver
Limpeza e regras de negócio, cada uma com a evidência estatística que a sustenta: exclusão de 2023-2024 (perfil categórico anômalo), tratamento MNAR de `Produto`/`Categoria` (χ² = 36.726,99, p ≈ 0), *winsorização* de `Duração`, texto normalizado sem aprendizado de vocabulário.

### 🥇 Camada Gold
Três tabelas isoladas por desafio, com contrato de dados automático:
1. **`gold_volume_diario`** — série elegível e bruta, separada por prioridade (P2/P3), para o SARIMAX.
2. **`gold_tendencias_macro`** — agregação semanal com dimensão `elegivel_kpi`, para o Desafio 2.
3. **`gold_chamados_risco`** — matriz granular para o CatBoost e o SHAP, sem `tem_incidente_pai`/`incidente_pai_contagem_historica` (regra oficial: incidente com pai preenchido não entra em KPI). Distribuição real de `Prioridade`: 4-Baixa (64.580), 3-Média (41.260), 2-Alta (15.645), 5-Muito Baixa (325), **1-Crítica (1 chamado — existe, mas é irrelevante em volume)**.

---

## 🔬 Destaques de Engenharia & Rigor Econométrico

### 1. Estatística de séries temporais (Desafio 1)
ADF/KPSS para `d=1`; abordagem **Bottom-Up** (P2 e P3 modelados separadamente, somados na produção); diagnóstico de resíduos (Ljung-Box, Breusch-Pagan, Jarque-Bera); intervalo por *bootstrap*; correção de viés de Duan; teste de parcimônia por BIC; piso em zero.

**Achado crítico confirmado com dado real**: o campo `Entrou para KPI?` é **censurado** — sua proporção semanal, estável por meses, despenca nas últimas semanas da base (queda de mais de 80% na semana final). Consistente com o campo sendo preenchido só no fechamento do chamado. O treino do modelo de produção foi cortado em **07/12/2025** para não herdar esse artefato — sem essa correção, a previsão de P3 chegava a sair zerada em dias normais, contra uma média histórica de 54,8/dia.

**Métrica por horizonte (D+1/D+7)**, critério oficial da banca, medida com validação de origem rolante — antes só existia MAE de bloco de 49 dias. Isso mudou a especificação vencedora em ambas as séries: P2 → `sarima_classico`; P3 → `sarimax_hibrido` (escala log1p). O MAE em D+1/D+7 de P3 (9,49 e 10,1) é, na verdade, melhor do que a métrica de bloco antiga sugeria (13,11).

**Intervalo de confiança conjunto**: a soma de P2+P3 usa *bootstrap* que sorteia o mesmo dia para as duas séries, preservando a correlação real entre os erros, em vez de somar os limites de cada IC separadamente.

### 2. Probabilidade e associação categórica (Desafios 2, 3 e 4)
Kruskal-Wallis (mistura de populações em `Duração`); V de Cramér (associação categórica); `grupo_baixo_volume` (guardrail de *cold start*); separação quase-completa identificada e resolvida na Sprint de ML (cascata de 3 níveis) — resultado real: só 3 de 38 coeficientes estatisticamente significativos, **nenhum de `Grupo designado`**; Ordered Target Statistics do CatBoost.

**Calibração de threshold honesta**: o threshold de decisão do CatBoost era calibrado no mesmo conjunto de teste usado para reportar a métrica — otimista por construção. Corrigido para calibrar numa fatia de validação interna e só então aplicar ao teste real: o resultado corrigido é mais conservador (recall de 11,8%, não mais 26,5%) — um número menos bonito, porém defensável.

**SHAP validado contra memorização**: o modelo de produção do CatBoost treina com 100% do histórico — explicá-lo sobre os mesmos dados mistura sinal real com decoreba. A correção reconstrói o modelo do fold 3 (nunca viu o período de teste): 6 dos 10 chamados mais arriscados **fora da amostra** violaram de fato. Os 5 chamados que aparecem nos dois rankings (in-sample e out-of-sample) foram auditados individualmente — **todos são violações reais confirmadas**, evidência de sinal genuíno, não de viés estrutural.

---

## 🚀 Resultados da Modelagem

### ✅ Desafio 1 — Previsão de Volume (SARIMAX, Bottom-Up)

* **Especificação final**: P2 → `sarima_classico` (escala bruta); P3 → `sarimax_hibrido` (escala log1p) — vencedores pelo critério oficial D+1/D+7.
* **MAE por horizonte** (média dos 3 folds): P2 — D+1: 4,07 | D+7: 4,32. P3 — D+1: 9,49 | D+7: 10,1.
* **Produção**: treino cortado em 07/12/2025 (censura confirmada). W+1 consolidado de **477 chamados** (P2: 96 | P3: 381), IC 90% por *bootstrap* conjunto de [273, 788]. Nenhum valor negativo em nenhuma etapa.
* **Guardrail de plausibilidade**: previsão desvia -5,4% (P2) e +21,9% (P3) da média das últimas 8 semanas — dentro do limite de ±50%, sem alerta.
* **Teto Contratual (Dicionário v2)**: 2025 fechou em 125% de atingimento de volume em ambas as prioridades; projeção 2026 mantém o mesmo patamar (P2: 125%, P3: 125%).
* **Projeção de perda de OLA D+1/D+7**: estimativa de 4,9 violações esperadas em W+1 — **validada contra um período real e subestimou** (erro absoluto de 18,3 no fold 3). A multiplicação simples (volume previsto × taxa histórica) é direcionalmente correta, mas não deve ser apresentada como número exato sem essa ressalva.

### ✅ Desafio 2 — Tendências e Fatores de Crescimento

* **Achado central**: o volume total de chamados cresceu +840/semana entre as janelas comparadas — mas **113% desse crescimento vem de chamados de Monitoramento não-elegíveis para KPI**. O volume elegível de verdade, nas mesmas janelas, caiu. Responde diretamente à pergunta oficial "o que mais influencia o aumento de incidentes": é ruído de monitoramento automático, não demanda operacional real.
* **Atingimento acumulado de OLA**: P2 em 75% (ritmo recente projeta 50% se mantido); P3 em 150%. Consistente com o achado do Desafio 1 de que P2 tem volume sob controle mas taxa de violação proporcionalmente pior.
* **Cobertura de categorização caindo**: 18,7% no período recente contra 40,0% no período anterior.

### ✅ Desafio 3 — Classificação de Risco (CatBoost)

* **Resultado**: PR-AUC médio de **0,1501** (baseline: 0,0088) — 17x melhor. ROC-AUC médio de 0,8075.
* **Threshold corrigido**: calibrado numa validação interna, aplicado ao teste real — 7 alertas, precisão de 57,1%, recall de 11,8% (a calibração anterior, otimista por usar o próprio teste, mostrava recall de 26,5%).
* **Top *features*** (pós-remoção de `tem_incidente_pai`): `descricao_limpa`, `grupo_contagem_historica`, `pressao_fila_7d`.

### ✅ Desafio 4 — Explicabilidade (SHAP)

* **Quais fatores mais influenciam o risco de violação?** Por SHAP, os 5 fatores mais usados pelo modelo: `descricao_limpa` (0,78 de |SHAP| médio — dominante), `descricao_contagem_historica` (0,32, tende a não aumentar risco — problema recorrente já tem rotina), `grupo_contagem_historica` (0,28), `grupo_chamados_ultima_hora` (0,27), `hora_cos` (0,20). `Grupo designado` (maior V de Cramér na EDA) cai para posição distante no SHAP — o sinal da equipe é majoritariamente absorvido pelas features derivadas de carga.
* **Onde estão os principais riscos operacionais?** Fora da amostra (fold 3), PR-AUC de 0,2141, 6 de 10 chamados mais críticos violaram de fato. Por taxa observada com intervalo de Wilson: templates "erro instalacao" (6,7%, n=30) e "problem check postgresql" (3,0%, n=33) concentram risco, com amostra pequena o bastante para exigir cautela na leitura.
* **Cautela obrigatória**: equipes com `grupo_baixo_volume=1` e templates com IC largo não devem ser lidos como problema de desempenho confirmado — a amostra não sustenta essa conclusão.

### 📎 Sprints Acadêmicas (ML e DL)

* **ML — Regressão Logística**: PR-AUC médio ~0,043 (ROC-AUC ~0,807, quase empatado com o CatBoost — evidência direta de por que PR-AUC é a métrica primária do projeto).
* **DL — ANN**: PR-AUC 0,0727 no fold 3 (clusterização de texto testada e descartada). MVP funcional validado com chamado real do histórico.

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
│   ├── utils.py                                            # módulo central do projeto + Sprints
│   └── test_utils.py                                       # 44 testes automatizados
├── .gitattributes
└── README.md
```

> As pastas `data/bronze`, `data/silver` e `data/gold` são versionadas vazias (`.gitkeep`) — os parquets ficam no Google Drive montado em runtime, não no Git.
