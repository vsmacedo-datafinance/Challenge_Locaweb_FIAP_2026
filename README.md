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
* **Validação de Schema:** Verificação estrita das 19 colunas mapeadas no dicionário de dados.
* **Validação de Domínio:** Detecção de anomalias categóricas inesperadas.
* **Metadados de Proveniência:** Injeção automática de `_ingested_at`, `_source_layer` e `_source_hash` (SHA-256) para rastreabilidade ponta a ponta.
* **Transformação:** Apenas tipagem mínima de datas (`datetime`).

### 🥈 Camada Silver (Limpeza & Regras de Negócio)
Aplicação de regras de negócio embasadas por testes de hipóteses estatísticas da nossa EDA.
* **Filtro de Regime Estrutural:** Exclusão dos dados de 2023-2024, identificados estatisticamente como período de testes/ruído (comportamento anômalo nas probabilidades conjuntas de origem e fechamento).
* **Tratamento de Missingness (MNAR):** Identificação via Teste Qui-Quadrado ($\chi^2$) de que nulos em *Produto/Categoria* dependem da origem do chamado (*Monitoramento*). Em vez de imputação enviesada, criamos a flag de cobertura categórica.
* **Winsorização e Log:** Tratamento explícito da cauda da variável `Duração` (capping no P99 calculado globalmente e transformação `log1p`).
* **Processamento de Texto Determinístico:** Padronização de `Descrição resumida` usando conversão morfológica, sem tokens aprendidos (evitando vazamento global).

### 🥇 Camada Gold (Feature Store & Model Readiness)
Desenho de *Features* focado em evitar vazamento temporal (*look-ahead bias*), criando três tabelas de consumo isoladas:
1. **`gold_volume_diario` (Desafio 1):** Agregação temporal (365 dias de 2025) com variáveis cíclicas (seno/cosseno) e *lags* operativos ($t-1$ a $t-7$) para modelagem **SARIMAX**.
2. **`gold_tendencias_macro` (Desafio 2):** Agregação semanal sumarizando volumetria, cobertura de categorias e mediana de duração para diagnóstico e relatórios de BI.
3. **`gold_chamados_risco` (Desafios 3 e 4):** Matriz granular de predição (121.811 tickets) pronta para o **CatBoost**. Exclusão cirúrgica de variáveis pós-evento (`Resolvido`, `Código de Fechamento`, etc.).

---

## 🔬 Destaques de Engenharia & Data Science

### 1. Engenharia Causal Estrita
Features temporais foram desenhadas olhando estritamente para o passado ($t-1$):
* `expanding_count_by_key`: Histórico de falhas de um *Item de Configuração* acumulado até o segundo anterior ao chamado.
* `hours_since_last_event_by_key`: Proxy de recência de falhas.
* `rolling_window_causal_count`: Janela deslizante (*60min, closed='left'*) medindo a "pressão na fila" de um Grupo Designado no momento exato do incidente.

### 2. Rigor Econométrico e Estatístico
Nenhuma decisão foi tomada por empirismo cego:
* **Mistura de Populações (Kruskal-Wallis):** Comprovamos que a `Duração` é gerada por múltiplos processos concorrentes (automático, manual, sem intervenção), impedindo análises generalistas sem segmentação por `Status`.
* **Guardrails de Variância:** Criação da flag `grupo_baixo_volume` para evitar que o modelo sofra overfitting devido a alta variância em filas/equipes com pouca amostragem ($n < 100$).

### 3. Código Testável e Governança
Uso intenso da biblioteca de `logging` padronizando saídas, funções agnósticas a negócio no módulo `.py` de utilidades, e asserções (`assert`) pós-gravação de Parquets para garantir unicidade de chaves primárias e integridade de *Data Leakage*.

---

## 🚀 Próximos Passos (Modelagem)
Com a fundação de dados finalizada, os próximos módulos avançam para o Machine Learning:
- [ ] **Desafio 1:** Previsão de volume através de modelos auto-regressivos sazonais (SARIMAX).
- [ ] **Desafio 3:** Classificação de Risco (Quebra de KPI) utilizando aprendizado baseado em árvores com suporte nativo a texto e categóricas (CatBoost).
- [ ] **Desafio 4:** Explicabilidade de Modelos através de SHAP Values para direcionar os insights de negócios e as recomendações de eficiência à Locaweb.

---
*Projeto elaborado como desafio acadêmico e técnico (FIAP).*
