# 🕰️ Projeto Cronos | Locaweb Challenge 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?style=for-the-badge&logo=pandas)
![Estatística](https://img.shields.io/badge/Stats-Econometrics-brightgreen?style=for-the-badge)
![Arquitetura](https://img.shields.io/badge/Architecture-Medallion-FFD700?style=for-the-badge)

**Repositório oficial do Projeto Cronos, desenvolvido para o Challenge Locaweb 2026 (FIAP).**

## 👥 Equipe

* **Bruno Rosa** — RM563779
* **Danilo Alves** — RM564109
* **Enzo Cremaschi** — RM562058
* **Vinícius Macedo** — RM561911

---

## 📑 Sumário

- [Resumo Executivo](#-resumo-executivo)
- [Arquitetura de Dados (Pipeline)](#️-arquitetura-de-dados-pipeline)
- [Destaques de Engenharia & Rigor Econométrico](#-destaques-de-engenharia--rigor-econométrico)
- [Resultados da Modelagem](#-resultados-da-modelagem)
- [Estrutura do Repositório](#-estrutura-do-repositório)
- [Próximos Passos](#-próximos-passos)

---

## 🎯 Resumo Executivo

O Projeto Cronos visa otimizar a gestão de incidentes da Locaweb através de inteligência de dados. Nossa abordagem foge do padrão de notebooks monolíticos e adota uma **Arquitetura Medalhão (Medallion Pattern)** robusta, suportada por princípios de Engenharia de Dados (rastreabilidade, logs estruturados, testes automatizados) e um forte rigor econométrico na fase de Análise Exploratória (EDA).

A pipeline de dados foi desenhada com **tolerância zero a *data leakage*** (vazamento de dados — nenhuma coluna pós-evento entra como *feature*, nenhum encoding aprendido do alvo é calculado fora do fold de treino) e tratamento explícito para problemas de *cold start* (equipes/filas com pouquíssima amostragem).

---

## 🏗️ Arquitetura de Dados (Pipeline)

Adotamos a Arquitetura Medalhão para garantir governança, reprodutibilidade e isolamento de regras de negócio. Todo o "encanamento" (hashing, logging, I/O, validação) está centralizado em um único módulo `utils.py`, respeitando o princípio de responsabilidade única.

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

Desenho de *features* focado em evitar vazamento temporal (*look-ahead bias*), com três tabelas de consumo isoladas, uma por desafio:

1. **`gold_volume_diario`** (Desafio 1) — agregação temporal (365 dias de 2025), variáveis cíclicas (seno/cosseno) e *lags* operativos (t-1 a t-7), para modelagem **SARIMAX**.
2. **`gold_tendencias_macro`** (Desafio 2) — agregação semanal sumarizando volumetria, cobertura de categorias e mediana de duração, para diagnóstico e relatórios de BI.
3. **`gold_chamados_risco`** (Desafios 3 e 4) — matriz granular de predição (121.811 chamados) pronta para o **CatBoost**, com exclusão cirúrgica de variáveis pós-evento (`Resolvido`, `Código de fechamento`, `Status`, `Duração` etc.).

---

## 🔬 Destaques de Engenharia & Rigor Econométrico

### 1. Estatística de séries temporais (Desafio 1)

* **Estacionariedade:** testes de Dickey-Fuller Aumentado (ADF) e KPSS, definindo matematicamente a necessidade de diferenciação de 1ª ordem (d=1).
* **Diagnóstico de resíduos:** validação sistemática com **Ljung-Box** (autocorrelação), **Breusch-Pagan** (heterocedasticidade) e **Jarque-Bera** (normalidade) — sem assumir ruído branco gaussiano de antemão.
* **Incerteza por bootstrap:** a curtose encontrada nos resíduos (muito acima de 3) indicava caudas pesadas, invalidando a premissa gaussiana clássica — substituímos o intervalo de confiança padrão por um **intervalo de previsão por *bootstrap* dos resíduos**.
* **Correção de viés de Duan:** confirmamos empiricamente, nos 3 *folds*, que reverter transformações logarítmicas com `expm1` ingênuo subestima sistematicamente a previsão quando a variância é alta — a correção de Duan foi usada em todas as comparações de escala.
* **Teste de parcimônia (BIC):** o Critério de Informação Bayesiano penalizou complexidade desnecessária — os coeficientes de Fourier foram removidos após confirmar estatisticamente que não eram significativos (p = 0,81 e p = 0,98).

### 2. Probabilidade e associação categórica (Desafios 2 e 3)

* **Kruskal-Wallis para mistura de populações:** confirmamos (H = 50.053,42, p ≈ 0) que `Duração` é, na verdade, uma mistura de distribuições distintas condicionadas ao modo de fechamento (`Status`) — invalida o uso de métricas de tendência central genéricas sobre essa variável.
* **Associação categórica:** uso do V de Cramér para medir a força de associação entre variáveis de alta cardinalidade e o alvo (`Grupo designado` foi a associação individual mais forte encontrada).
* **Guardrails de variância (*cold start*):** criação da *flag* `grupo_baixo_volume`, para sinalizar equipes/filas com amostragem insuficiente (n < 100) e evitar leitura enganosa de risco baseada em pouca informação.
* **Ordered Target Statistics:** em vez de um *target encoding* tradicional (que gera vazamento), apoiamo-nos no processamento nativo do CatBoost, que calcula a estatística da variável-alvo respeitando a ordem temporal, sempre dentro do fold de treino.

---

## 🚀 Resultados da Modelagem

Os modelos preditivos foram otimizados com **Optuna** e validados com **Walk-Forward Validation** em janela expansiva (3 *folds* temporais estritos, sem nenhum vazamento de dado futuro).

### ✅ Desafio 1 — Previsão de Volume (SARIMAX)

* **Abordagem:** competição formal entre modelo *naive*, ARIMA puro, SARIMA clássico e ARIMAX com coeficientes de Fourier, com decisão sustentada por métricas robustas a *outliers* (MedAE, MdAPE) além das tradicionais.
* **Resultado:** o modelo vencedor foi o `arimax_fourier_parcimonioso`, treinado em escala bruta (superando a escala logarítmica mesmo com a correção de Duan aplicada) — mais estável diante dos saltos anômalos de volumetria diária identificados na série.

### ✅ Desafio 3 — Classificação de Risco (CatBoost)

* **Abordagem:** *Gradient Boosting* sobre um desbalanceamento extremo de classes — 0,95% de positivos no universo elegível (238 violações em 25.156 chamados). Sem SMOTE/SMOTEENN em nenhum momento do projeto; balanceamento via `auto_class_weights`.
* **Resultado:** o CatBoost superou os baselines por uma margem grande, com **PR-AUC médio de 0,1530** (contra 0,0088 do baseline de taxa histórica) e **ROC-AUC médio de 0,7838** — superando com folga o teto (~0,65) obtido em iterações anteriores do projeto com uma arquitetura de rede neural recorrente (GRU).
* **Threshold de decisão:** calibrado com uma matriz de custo **ilustrativa** de 1:15 (custo de deixar passar uma violação real vs. custo de uma verificação redundante) — usada para demonstrar o mecanismo de calibração, não como um valor real de negócio. O time ainda não forneceu os custos reais de falso positivo/falso negativo; quando isso acontecer, a mesma função já está pronta para recalibrar.
* **Top *features*:** as variáveis de maior peso identificadas foram a descrição do chamado (`descricao_limpa`, ~29% de importância), a pressão operacional da fila nos últimos 7 dias (`pressao_fila_7d`) e o histórico de problemas do ativo de infraestrutura (`ic_contagem_historica`).

---

## 📁 Estrutura do Repositório

```
.
├── utils.py                              # Módulo central (projeto + seção de Sprints acadêmicas, separadas por divisória)
├── notebooks/
│   ├── 01_bronze_ingestao.ipynb
│   ├── 02_silver_limpeza_texto.ipynb
│   ├── 03_gold_features.ipynb
│   ├── 04_desafio1_sarimax.ipynb
│   ├── 05_desafio3_catboost.ipynb
│   ├── EC_Sprint_3_Cronos_ML.ipynb        # Sprint acadêmica — regressão logística interpretável
│   └── EC_Sprint_3_Cronos_DeepL.ipynb     # Sprint acadêmica — ANN + investigação de clusterização
├── tests/
│   └── test_utils.py                      # Suíte de testes das funções de utils.py
└── docs/
    ├── EDA_Completa_Locaweb_Cronos.ipynb
    ├── EDA_Complementar_Locaweb_Cronos.ipynb
    └── projeto_cronos_documento_completo.docx  # Documento de referência completo do projeto
```

---

## 🔮 Próximos Passos

- [ ] **Desafio 4 — Explicabilidade (SHAP):** aprofundar a explicabilidade do modelo de risco através da extração dos valores SHAP, traduzindo o impacto marginal das *top features* em *insights* de negócio acionáveis para a operação da Locaweb.
- [ ] **Ensemble dos modelos de fold do CatBoost**, para reduzir a variância de desempenho observada entre os 3 *folds* de validação.
- [ ] **Intervalo de confiança por *bootstrap* no Precision@K**, hoje reportado como número pontual.
- [ ] **Estatística descritiva consolidada** do projeto.
