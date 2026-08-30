# 🕰️ Projeto Chronos | Locaweb Challenge 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?style=for-the-badge&logo=pandas)
![Estatística](https://img.shields.io/badge/Stats-Econometrics-brightgreen?style=for-the-badge)
![Arquitetura](https://img.shields.io/badge/Architecture-Medallion-FFD700?style=for-the-badge)

**Repositório oficial do Projeto Chronos, desenvolvido para o Challenge Locaweb 2026 (FIAP).**

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
- [Próximos Passos](#-próximos-passos)

---

## 🎯 Resumo Executivo

O Projeto Chronos visa otimizar a gestão de incidentes da Locaweb através de inteligência de dados. Nossa abordagem foge do padrão de notebooks monolíticos e adota uma **Arquitetura Medalhão (Medallion Pattern)** robusta, suportada por princípios de Engenharia de Dados (rastreabilidade, logs estruturados, testes automatizados) e um forte rigor econométrico na fase de Análise Exploratória (EDA).

A pipeline de dados foi desenhada com **tolerância zero a *data leakage*** (vazamento de dados — nenhuma coluna pós-evento entra como *feature*, nenhum encoding aprendido do alvo é calculado fora do fold de treino) e tratamento explícito para problemas de *cold start* (equipes/filas com pouquíssima amostragem).

---

## 📖 Ordem de Leitura Recomendada

Os notebooks foram desenhados para serem lidos nesta sequência — cada um depende de decisões documentadas no anterior:

1. **`Projeto_Chronos_Locaweb_01_bronze_ingestao.ipynb`** — ingestão bruta, sem regra de negócio.
2. **`Projeto_Chronos_Locaweb_EDA_Completa.ipynb`** — primeira rodada de análise exploratória, base para as decisões de limpeza da Silver.
3. **`Projeto_Chronos_Locaweb_EDA_Complementar.ipynb`** — segunda rodada, aprofunda/revisa achados da EDA Completa (inclusive corrigindo hipóteses iniciais).
4. **`Projeto_Chronos_Locaweb_02_silver_limpeza.ipynb`** — limpeza e regras de negócio, cada uma com a evidência estatística das EDAs que a sustenta.
5. **`Projeto_Chronos_Locaweb_03_gold_features_ajuste_incidente_pai.ipynb`** — camada de features, com a série de volume elegível/bruta separada e `tem_incidente_pai`/`incidente_pai_contagem_historica` removidas (regra oficial do Dicionário de Dados v2: incidente com pai preenchido não entra em KPI).
6. **`Projeto_Chronos_Locaweb_Sprint_3_Cronos_ML.ipynb`** e **`Projeto_Chronos_Locaweb_Sprint_3_Cronos_DL.ipynb`** — entregas acadêmicas (regressão logística interpretável e ANN), mesma base da Gold.
7. **`Projeto_Chronos_Locaweb_04_Sarimax_.ipynb`** — Desafio 1 (previsão de volume), leia por último entre os desafios: consome a série elegível já validada na Gold.
8. **`Projeto_Chronos_Locaweb_05_Catboost_.ipynb`** — Desafio 3 (risco de violação de SLA), fecha a sequência de modelagem.

---

## 🏗️ Arquitetura de Dados (Pipeline)

Adotamos a Arquitetura Medalhão para garantir governança, reprodutibilidade e isolamento de regras de negócio. Todo o "encanamento" (hashing, logging, I/O, validação, persistência de modelo) está centralizado em `src/utils.py`, respeitando o princípio de responsabilidade única — com uma divisória explícita separando as funções do projeto principal das funções exclusivas das Sprints acadêmicas de ML/DL.

### 🥉 Camada Bronze (Ingestão & Auditoria)

A camada Bronze é a porta de entrada. Garante que os dados ingeridos respeitem o contrato estabelecido, sem nenhuma regra de negócio aplicada ainda.

* **Validação de schema:** verificação estrita das 19 colunas mapeadas no dicionário de dados.
* **Validação de domínio:** detecção de anomalias categóricas inesperadas (valores fora do domínio esperado).
* **Metadados de proveniência:** injeção automática de `_ingested_at`, `_source_layer` e `_source_hash` (SHA-256) para rastreabilidade ponta a ponta.
* **Transformação:** apenas tipagem mínima de datas (`datetime`) — nenhuma regra de negócio.

### 🥈 Camada Silver (Limpeza & Regras de Negócio)

Aplicação de regras de negócio embasadas por testes de hipóteses estatísticas da nossa EDA — cada regra carrega, em código e em texto, a evidência que a justificou.

* **Filtro de regime estrutural:** exclusão dos dados de 2023-2024 (0,6% da base), identificados estatisticamente como período de teste/implantação — perfil categórico sistematicamente diferente de 2025 (73,6% de origem Manual contra 14,5%; 89,6% Encerrado Automaticamente contra 21,5%).
* **Tratamento de *missingness* (MNAR):** identificação via teste Qui-Quadrado (χ² = 36.726,99, p ≈ 0) de que os nulos em *Produto/Categoria* dependem estruturalmente da origem automática do chamado (*Monitoramento*). Em vez de imputação preditiva (que causaria viés), criamos a *flag* de cobertura categórica.
* **Winsorização e log:** tratamento explícito da cauda da variável `Duração` (*capping* no P99 calculado globalmente + transformação `log1p`).
* **Processamento de texto determinístico:** padronização de `Descrição resumida` (minúsculas, sem acento/pontuação, sem *stopword*), sem nenhum token aprendido — evita vazamento se usado fora do fold de treino de um modelo.

### 🥇 Camada Gold (Feature Store & Model Readiness)

Desenho de *features* focado em evitar vazamento temporal (*look-ahead bias*), com três tabelas de consumo isoladas, uma por desafio — e um contrato de dados (`CONTRATO_DADOS_*.md`) gerado automaticamente para cada uma, documentando coluna, tipo, % de nulos e cardinalidade, pronto para compartilhar com o time sem precisar abrir o notebook.

1. **`gold_volume_diario`** (Desafio 1) — série diária elegível e bruta, separada por prioridade (P2/P3), com variáveis cíclicas (seno/cosseno) e *lags* operativos (t-1 a t-7), para modelagem **SARIMAX**.
2. **`gold_tendencias_macro`** (Desafio 2) — agregação semanal sumarizando volumetria, cobertura de categorias e mediana de duração, com dimensão de elegibilidade (`elegivel_kpi`), para diagnóstico e relatórios de BI. Exportada também em CSV (`exports_dashboard/`) para consumo direto em Power BI/Tableau.
3. **`gold_chamados_risco`** (Desafios 3 e 4) — matriz granular de predição (121.811 chamados) pronta para o **CatBoost**, com exclusão cirúrgica de variáveis pós-evento (`Resolvido`, `Código de fechamento`, `Status`, `Duração` etc.) e de `tem_incidente_pai`/`incidente_pai_contagem_historica` (regra oficial: incidente com pai preenchido não entra em KPI).

---

## 🔬 Destaques de Engenharia & Rigor Econométrico

### 1. Estatística de séries temporais (Desafio 1)

* **Estacionariedade:** testes de Dickey-Fuller Aumentado (ADF) e KPSS, definindo matematicamente a necessidade de diferenciação de 1ª ordem (d=1).
* **Abordagem Bottom-Up:** P2 e P3 têm dinâmicas diferentes (P3 com sazonalidade semanal muito mais forte que P2, confirmado por decomposição STL) — modelados separadamente e somados na produção, em vez de uma série combinada única.
* **Diagnóstico de resíduos:** validação sistemática com **Ljung-Box** (autocorrelação), **Breusch-Pagan** (heterocedasticidade) e **Jarque-Bera** (normalidade) — sem assumir ruído branco gaussiano de antemão.
* **Incerteza por bootstrap:** a curtose encontrada nos resíduos indicava caudas pesadas, invalidando a premissa gaussiana clássica — substituímos o intervalo de confiança padrão por um **intervalo de previsão por *bootstrap* dos resíduos**.
* **Correção de viés de Duan:** confirmamos empiricamente, nos 3 *folds* e nas duas séries (P2 e P3), que reverter transformações logarítmicas com `expm1` ingênuo subestima sistematicamente a previsão — a escala bruta venceu a log1p nas duas séries.
* **Teste de parcimônia (BIC):** os coeficientes de Fourier de P2 foram mantidos numa versão parcimoniosa após confirmação estatística (BIC favorável em 3 de 3 *folds*); P3 nem usa Fourier (sazonalidade capturada pelo próprio componente sazonal do SARIMA).
* **Piso em zero:** previsões e limites inferiores de intervalo de confiança nunca são negativos — contagem de chamados não pode ser negativa, correção aplicada na função central de ajuste do modelo (`utils.py`), não célula por célula.
* **Teto Contratual real:** comparação do volume elegível anual contra as faixas oficiais de meta do Dicionário de Dados v2 (Locaweb/FIAP) — 2025 fechou em 125% de atingimento em ambas as prioridades.
* **Investigação de anomalias:** saltos de volume identificados por variação diária extrema, separadamente por prioridade; parte deles correlaciona com incidentes em massa (via `tem_incidente_pai`, ainda disponível na análise mesmo removida como *feature* de modelo) — tratados como evento operacional real, não falha de modelo.

### 2. Probabilidade e associação categórica (Desafios 2 e 3)

* **Kruskal-Wallis para mistura de populações:** confirmamos (H = 50.053,42, p ≈ 0) que `Duração` é, na verdade, uma mistura de distribuições distintas condicionadas ao modo de fechamento (`Status`) — invalida o uso de métricas de tendência central genéricas sobre essa variável.
* **Associação categórica:** uso do V de Cramér para medir a força de associação entre variáveis de alta cardinalidade e o alvo (`Grupo designado` foi a associação individual mais forte encontrada).
* **Guardrails de variância (*cold start*):** criação da *flag* `grupo_baixo_volume`, para sinalizar equipes/filas com amostragem insuficiente (n < 100) e evitar leitura enganosa de risco baseada em pouca informação.
* **Separação quase-completa:** identificada e resolvida na Sprint de ML — com ~17 equipes dividindo menos de 1% de positivos, o ajuste clássico de regressão logística falha numericamente para equipes sem nenhum caso positivo; resolvido com uma cascata de 3 níveis (ajuste clássico → regularização L2 → *bootstrap*). Resultado real: só 3 de 38 coeficientes se confirmaram estatisticamente significativos — nenhum deles de `Grupo designado`, o que exige cautela ao interpretar os coeficientes brutos dessa variável.
* **Ordered Target Statistics:** em vez de um *target encoding* tradicional (que gera vazamento), apoiamo-nos no processamento nativo do CatBoost, que calcula a estatística da variável-alvo respeitando a ordem temporal, sempre dentro do fold de treino.

---

## 🚀 Resultados da Modelagem

Os modelos preditivos foram otimizados com **Optuna** e validados com **Walk-Forward Validation** em janela expansiva (3 *folds* temporais estritos, sem nenhum vazamento de dado futuro) — os mesmos 3 *folds* em todos os modelos, para comparabilidade direta.

### ✅ Desafio 1 — Previsão de Volume (SARIMAX, Bottom-Up)

* **Abordagem:** P2 e P3 modelados separadamente (competição formal entre naive, ARIMA puro, SARIMA clássico e ARIMAX com Fourier, nos 3 *folds*), somados apenas na etapa de produção.
* **Resultado:** `arimax_fourier_parcimonioso` venceu para P2 (MAE 4,29 em escala bruta); `sarima_classico` venceu para P3 (MAE 11,87), sem precisar de exógenas de calendário — a sazonalidade semanal forte de P3 já é capturada pelo componente sazonal do próprio modelo.
* **Produção:** W+1 consolidado (P2+P3) de 168 chamados elegíveis, com IC 90% por *bootstrap* de [23, 464] — nenhum valor negativo em nenhuma etapa.

### ✅ Desafio 3 — Classificação de Risco (CatBoost)

* **Abordagem:** *Gradient Boosting* sobre um desbalanceamento extremo de classes — 0,95% de positivos no universo elegível (238 violações em 25.156 chamados). Sem SMOTE/SMOTEENN em nenhum momento do projeto; balanceamento via `auto_class_weights`.
* **Resultado:** o CatBoost superou os baselines por uma margem grande, com **PR-AUC médio de 0,1545** (contra 0,0088 do baseline de taxa histórica) e **ROC-AUC médio de 0,7804** — superando com folga o teto (~0,65) obtido em iterações anteriores do projeto com uma arquitetura de rede neural recorrente (GRU).
* **Limitação conhecida:** Precision@10 tem desvio-padrão (0,29) maior que a própria média (0,37) entre *folds* — instabilidade real ainda sem intervalo de confiança formal (ver Próximos Passos).
* **Threshold de decisão:** calibrado com uma matriz de custo **ilustrativa** de 1:15 (custo de deixar passar uma violação real vs. custo de uma verificação redundante) — usada para demonstrar o mecanismo de calibração, não como um valor real de negócio.
* **Top *features*:** a descrição do chamado (`descricao_limpa`, ~29% de importância), a pressão operacional da fila nos últimos 7 dias (`pressao_fila_7d`) e o histórico de problemas do ativo de infraestrutura (`ic_contagem_historica`).

### 📎 Sprints Acadêmicas (ML e DL)

Duas entregas separadas, exigidas pelas disciplinas de Machine Learning e Deep Learning da FIAP — mesmo alvo do Desafio 3, mas com foco em interpretabilidade (ML) e viabilidade técnica de MVP (DL), não em superar o CatBoost:

* **ML — Regressão Logística:** PR-AUC médio ~0,043 (ROC-AUC ~0,807, quase empatado com o CatBoost — evidência direta de por que PR-AUC, não ROC-AUC, é a métrica primária do projeto).
* **DL — ANN:** PR-AUC 0,0727 no fold 3 (clusterização de texto testada e descartada nesta versão — piorou o PR-AUC após a remoção de `tem_incidente_pai` da Gold) — inclui MVP funcional local (`prever_risco_chamado`), validado com um chamado real do histórico (não um cenário sintético, que gerou valores fora de distribuição e saturou a rede).

---

## 📁 Estrutura do Repositório

```
.
├── data/
│   ├── bronze/
│   │   └── .gitkeep
│   ├── silver/
│   │   └── .gitkeep
│   └── gold/
│       └── .gitkeep
├── notebooks/
│   ├── Projeto_Chronos_Locaweb_01_bronze_ingestao.ipynb
│   ├── Projeto_Chronos_Locaweb_02_silver_limpeza.ipynb
│   ├── Projeto_Chronos_Locaweb_03_gold_features_ajuste_incidente_pai.ipynb
│   ├── Projeto_Chronos_Locaweb_04_Sarimax_.ipynb
│   ├── Projeto_Chronos_Locaweb_05_Catboost_.ipynb
│   ├── Projeto_Chronos_Locaweb_EDA_Completa.ipynb
│   ├── Projeto_Chronos_Locaweb_EDA_Complementar.ipynb
│   ├── Projeto_Chronos_Locaweb_Sprint_3_Cronos_ML.ipynb    # Sprint acadêmica — regressão logística interpretável
│   └── Projeto_Chronos_Locaweb_Sprint_3_Cronos_DL.ipynb    # Sprint acadêmica — ANN + investigação de clusterização
├── src/
│   └── utils.py                                            # Módulo central do projeto + Sprints
├── .gitattributes
└── README.md
```

> As pastas `data/bronze`, `data/silver` e `data/gold` são versionadas vazias (`.gitkeep`) — os parquets gerados pelos notebooks ficam no Google Drive montado em runtime, não no Git.

---

## 🔮 Próximos Passos

- [ ] **Desafio 4 — Explicabilidade (SHAP):** aprofundar a explicabilidade do modelo de risco através da extração dos valores SHAP, traduzindo o impacto marginal das *top features* em *insights* de negócio acionáveis para a operação da Locaweb.
- [ ] **Ensemble dos modelos de fold do CatBoost**, para reduzir a variância de desempenho observada entre os 3 *folds* de validação.
- [ ] **Intervalo de confiança por *bootstrap* no Precision@K**, hoje reportado como número pontual (instabilidade real já identificada: desvio-padrão maior que a média no Precision@10).
- [ ] **Estatística descritiva consolidada** do projeto.
