# 🕰️ Projeto Cronos | Locaweb Challenge 2026

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458?style=for-the-badge&logo=pandas)
![Estatística](https://img.shields.io/badge/Stats-Econometrics-brightgreen?style=for-the-badge)
![Arquitetura](https://img.shields.io/badge/Architecture-Medallion-FFD700?style=for-the-badge)

**Repositório oficial do Projeto Cronos, desenvolvido para o Challenge Locaweb 2026.**

## 👥 Equipe
* **Bruno Rosa** - RM563779
* **Danilo Alves** - RM564109
* **Enzo Cremaschi** - RM562058
* **Vinícius Macedo** - RM561911

---

## 🎯 Resumo Executivo
O Projeto Cronos visa otimizar a gestão de incidentes da Locaweb através de inteligência de dados. Nossa abordagem foge do padrão de notebooks monolíticos e adota uma **Arquitetura Medalhão (Medallion Pattern)** robusta, suportada por princípios de Engenharia de Dados (rastreabilidade, logs estruturados) e um forte rigor econométrico na fase de Análise Exploratória (EDA).

A pipeline de dados foi desenhada com **Tolerância Zero a Data Leakage** (vazamento de dados) e tratamento explícito para problemas de *Cold Start* (partida a frio).

---

## 🏗️ Arquitetura de Dados (Pipeline)

Adotamos a Arquitetura Medalhão para garantir governança, reprodutibilidade e isolamento de regras de negócio. Todo o "encanamento" (hashing, logging, I/O) está centralizado em um módulo `utils.py`, respeitando o princípio de Responsabilidade Única (DRY).

### 🥉 Camada Bronze (Ingestão & Auditoria)
A camada Bronze é a porta de entrada. Garantimos que os dados ingeridos respeitem o contrato estabelecido.
* **Validação de Schema:** Verificação estrita das 19 colunas mapeadas no dicionário de dados[cite: 5].
* **Validação de Domínio:** Detecção de anomalias categóricas inesperadas[cite: 5].
* **Metadados de Proveniência:** Injeção automática de `_ingested_at`, `_source_layer` e `_source_hash` (SHA-256) para rastreabilidade ponta a ponta[cite: 5].
* **Transformação:** Apenas tipagem mínima de datas (`datetime`)[cite: 5].

### 🥈 Camada Silver (Limpeza & Regras de Negócio)
Aplicação de regras de negócio embasadas por testes de hipóteses estatísticas da nossa EDA.
* **Filtro de Regime Estrutural:** Exclusão dos dados de 2023-2024, identificados estatisticamente como período de testes/ruído (comportamento anômalo nas probabilidades conjuntas de origem e fechamento)[cite: 2, 4].
* **Tratamento de Missingness (MNAR):** Identificação via Teste Qui-Quadrado ($\chi^2 = 36726.99, p \approx 0$) de que nulos em *Produto/Categoria* dependem estruturalmente da origem automática do chamado (*Monitoramento*)[cite: 4]. Em vez de imputação preditiva (que causaria viés), criamos a flag de cobertura categórica[cite: 4].
* **Winsorização e Log:** Tratamento explícito da cauda da variável `Duração` (capping no P99 calculado globalmente e transformação `log1p`)[cite: 4].
* **Processamento de Texto Determinístico:** Padronização de `Descrição resumida` usando conversão morfológica, sem tokens aprendidos (evitando vazamento global)[cite: 4].

### 🥇 Camada Gold (Feature Store & Model Readiness)
Desenho de *Features* focado em evitar vazamento temporal (*look-ahead bias*), criando três tabelas de consumo isoladas[cite: 3]:
1. **`gold_volume_diario` (Desafio 1):** Agregação temporal (365 dias de 2025) com variáveis cíclicas (seno/cosseno) e *lags* operativos ($t-1$ a $t-7$) para modelagem **SARIMAX**[cite: 3, 7].
2. **`gold_tendencias_macro` (Desafio 2):** Agregação semanal sumarizando volumetria, cobertura de categorias e mediana de duração para diagnóstico e relatórios de BI[cite: 3].
3. **`gold_chamados_risco` (Desafios 3 e 4):** Matriz granular de predição (121.811 tickets) pronta para o **CatBoost**[cite: 3, 8]. Exclusão cirúrgica de variáveis pós-evento (`Resolvido`, `Código de Fechamento`, `Status`, `Duração`, etc.)[cite: 3, 8].

---

## 🔬 Destaques de Engenharia & Rigor Econométrico

### 1. Estatística de Séries Temporais (Desafio 1)
* **Estacionariedade:** Utilização dos testes de Dickey-Fuller Aumentado (ADF) e KPSS para verificação de raízes unitárias, definindo matematicamente a necessidade de diferenciação de 1ª ordem ($d=1$)[cite: 2, 7].
* **Diagnóstico de Resíduos:** Fuga da premissa ingênua de ruído branco. Os resíduos dos modelos foram sistematicamente validados usando testes de **Ljung-Box** (autocorrelação), **Breusch-Pagan** (heterocedasticidade) e **Jarque-Bera** (normalidade)[cite: 7]. 
* **Incerteza por Bootstrap:** Como a curtose encontrada indicava caudas pesadas (anulando a premissa de distribuição Gaussiana de erros), substituímos os intervalos de confiança clássicos por um **Intervalo de Previsão de Resíduos via Bootstrap**[cite: 7].
* **Correção de Viés de Duan:** Demonstramos empiricamente nos 3 folds que reverter transformações logarítmicas usando apenas $e^x - 1$ subestima sistematicamente a previsão quando a variância é alta. O uso da correção de Duan mitigou esse viés durante os testes[cite: 7].
* **Teste de Parcimônia (BIC):** Utilização do Critério de Informação Bayesiano (BIC) para penalizar a complexidade dos modelos. Removemos os coeficientes de Fourier ao provar estatisticamente (p-valores de 0.81 e 0.98) que a complexidade extra não trazia ganho preditivo[cite: 7].

### 2. Probabilidade e Associação Categórica (Desafios 2 e 3)
* **Kruskal-Wallis para Mistura de Populações:** Comprovamos ($H = 50053.42, p \approx 0$) que a variável `Duração` é, na verdade, uma mistura de distribuições distintas condicionadas ao modo de fechamento (`Status`), invalidando o uso de métricas de tendência central genéricas[cite: 2, 4].
* **Associação:** Utilização de V de Cramér para medir a força das associações entre variáveis de alta cardinalidade e o alvo[cite: 1, 4].
* **Guardrails de Variância (Cold Start):** Criação da flag `grupo_baixo_volume` para evitar instabilidade na inferência de risco baseada em equipes/filas com pouquíssima amostragem ($n < 100$)[cite: 3].
* **Ordered Target Statistics:** Ao invés de um Target Encoding tradicional que gera vazamento (*Data Leakage*), apoiamos-nos no processamento nativo do CatBoost que calcula a estatística da variável-alvo ordenando os dados no tempo[cite: 8].

---

## 🚀 Resultados da Modelagem

Os modelos preditivos foram desenvolvidos, otimizados com *Optuna* e validados utilizando a metodologia de **Walk-Forward Validation expansiva** (3 *folds* temporais estritos)[cite: 7, 8].

- [x] **Desafio 1: Previsão de Volume (SARIMAX)**
  * **Abordagem:** Competição entre modelos *Naive*, ARIMA puro, SARIMA clássico e ARIMAX com coeficientes de Fourier. As decisões priorizaram métricas robustas a outliers como MedAE e MdAPE[cite: 7].
  * **Resultado:** O modelo vencedor foi o `arimax_fourier_parcimonioso` treinado em escala bruta (superando a escala log mesmo com correção de Duan)[cite: 7]. Este modelo se provou mais eficiente e estável estatisticamente para lidar com saltos anômalos de volumetria diária[cite: 7].

- [x] **Desafio 3: Classificação de Risco (CatBoost)**
  * **Abordagem:** Utilização de *Gradient Boosting* avançado para atuar sobre o desbalanceamento extremo de classes — a base possuía apenas 0,95% de positivos no universo elegível (238 violações em 25.156 chamados)[cite: 8].
  * **Resultado:** O CatBoost "massacrou" os baselines tradicionais, atingindo um **PR-AUC médio de 0.1530** (vs. 0.0088 do baseline) e um **ROC-AUC médio de 0.7838**[cite: 8].
  * **Business Value:** O limiar de decisão (*threshold*) foi calibrado empiricamente focado em negócio (matriz de custos 1:15), onde o custo de um SLA violado ignorado (Falso Negativo) custa 15 vezes mais do que uma verificação redundante (Falso Positivo)[cite: 8].
  * **Top Features:** As variáveis de maior peso causal identificadas foram a descrição do chamado (`descricao_limpa`), a carga operacional da fila na última semana (`pressao_fila_7d`) e o histórico de problemas do ativo de infraestrutura (`ic_contagem_historica`)[cite: 8].

---

## 🔮 Próximos Passos
- [ ] **Desafio 4:** Aprofundar a Explicabilidade do Modelo de Risco (XAI) através da extração minuciosa dos **SHAP Values**. Esse passo traduzirá o impacto marginal das Top Features em *Insights de Negócios* concretos, direcionando recomendações operacionais e estratégicas de atendimento à diretoria da Locaweb.
