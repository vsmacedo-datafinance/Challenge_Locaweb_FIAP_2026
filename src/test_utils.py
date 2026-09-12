"""
Testes do utils.py — Projeto Chronos (Locaweb Challenge 2026).

Restaurado na revisão de 06/09 (Pendência 12). Cobre:
  1. funções causais da Gold (contagens históricas, janelas, flags), que
     eram o alvo dos ~23 testes originais perdidos;
  2. as funções novas das Seções 17-20 (guardrails, métrica por horizonte,
     IC conjunto, projeção de OLA, threshold em validação, SHAP/Wilson),
     cada uma com um caso normal e pelo menos um caso de borda.

Rodar na raiz do repositório:  pytest -q
Nenhum teste depende do dataset da Locaweb — tudo é sintético.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import utils  # noqa: E402


# ---------------------------------------------------------------------
# 1. Funções causais da Gold
# ---------------------------------------------------------------------

def _df_eventos():
    return pd.DataFrame({
        "chave": ["A", "A", "B", "A", None, "B"],
        "quando": pd.to_datetime([
            "2025-01-01 10:00", "2025-01-01 10:30", "2025-01-01 11:00",
            "2025-01-02 09:00", "2025-01-02 09:05", "2025-01-03 11:00",
        ]),
    })


def test_expanding_count_exclui_proprio_evento_e_futuro():
    df = _df_eventos()
    out = utils.expanding_count_by_key(df, "chave", "quando", "n")
    assert out.tolist()[:4] == [0, 1, 0, 2]
    assert out.iloc[5] == 1


def test_expanding_count_chave_nula_vira_nan_nao_zero():
    df = _df_eventos()
    out = utils.expanding_count_by_key(df, "chave", "quando", "n")
    assert np.isnan(out.iloc[4])


def test_hours_since_last_event_primeira_ocorrencia_nan():
    df = _df_eventos()
    out = utils.hours_since_last_event_by_key(df, "chave", "quando", "h")
    assert np.isnan(out.iloc[0]) and np.isnan(out.iloc[2])
    assert out.iloc[1] == pytest.approx(0.5)
    assert out.iloc[3] == pytest.approx(22.5)


def test_rolling_window_causal_count_fechada_a_esquerda():
    df = _df_eventos().dropna(subset=["chave"]).reset_index(drop=True)
    out = utils.rolling_window_causal_count(df, "chave", "quando", "60min", "c")
    # A às 10:30 vê A das 10:00; A das 10:00 não vê ninguém
    assert out.iloc[0] == 0 and out.iloc[1] == 1
    # B às 11:00 do dia 3 não vê o B do dia 1
    assert out.iloc[4] == 0


def test_rolling_window_causal_count_um_so_grupo_nao_colapsa():
    df = pd.DataFrame({
        "chave": ["Z"] * 4,
        "quando": pd.date_range("2025-01-01 10:00", periods=4, freq="20min"),
    })
    out = utils.rolling_window_causal_count(df, "chave", "quando", "60min", "c")
    assert isinstance(out, pd.Series) and out.tolist() == [0, 1, 2, 3]  # janela [t-60min, t): 11:00 vê 10:00, 10:20, 10:40


def test_rolling_window_timestamps_duplicados_nao_quebra():
    df = pd.DataFrame({
        "chave": ["Z", "Z", "Z"],
        "quando": pd.to_datetime(["2025-01-01 10:00"] * 3),
    })
    out = utils.rolling_window_causal_count(df, "chave", "quando", "60min", "c")
    assert len(out) == 3 and (out == 0).all()  # janela fechada à esquerda: mesmo instante não conta


def test_flag_low_volume_groups():
    df = pd.DataFrame({"g": ["a"] * 5 + ["b"] * 2})
    flag = utils.flag_low_volume_groups(df, "g", min_volume=3)
    assert flag.name == "g_baixo_volume"
    assert (~flag.iloc[:5]).all() and flag.iloc[5:].all()


def test_add_cyclical_time_features_adjacencia():
    df = pd.DataFrame({"h": [0, 23]})
    out = utils.add_cyclical_time_features(df, df["h"], 24, "hora")
    dist = np.hypot(out["hora_sin"].diff().iloc[1], out["hora_cos"].diff().iloc[1])
    assert dist < 0.3  # 23h e 0h ficam vizinhas no círculo


def test_cap_outliers_mantem_tamanho_e_capa():
    s = pd.Series(list(range(100)) + [10_000])
    out = utils.cap_outliers(s, 0.99)
    assert len(out) == len(s) and out.max() <= s.quantile(0.99)


def test_clean_text_ptbr_preserva_nulo_e_remove_stopword():
    s = pd.Series(["Problema: Falha na ATIVAÇÃO do plano!", None])
    out = utils.clean_text_ptbr(s)
    assert out.iloc[0] == "problema falha ativacao plano"
    assert pd.isna(out.iloc[1])


def test_generate_expanding_folds_sao_contiguos_e_expansivos():
    folds = utils.generate_expanding_folds("2025-01-01", 30, 7, 3)
    assert folds[0]["test_start"] == folds[0]["train_end"] + pd.Timedelta(days=1)
    assert folds[1]["train_end"] == folds[0]["test_end"]
    assert all(f["train_start"] == pd.Timestamp("2025-01-01") for f in folds)


def test_precision_at_k_inteiro_e_fracao():
    y = np.array([0, 1, 0, 1, 0, 0, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.1, 0.7, 0.2, 0, 0, 0, 0, 0])
    assert utils.precision_at_k(y, s, 3) == pytest.approx(2 / 3)
    assert utils.precision_at_k(y, s, 0.2) == pytest.approx(0.5)


def test_bootstrap_metric_ci_descarta_reamostra_sem_positivos():
    y = np.array([0] * 30 + [1])
    s = np.random.default_rng(0).random(31)
    res = utils.bootstrap_metric_ci(y, s, lambda a, b: float(a.sum()), n_boot=50)
    assert res["n_amostras_validas"] == 50 and res["ic_inferior"] >= 1


def test_checar_faixa_kpi_cobre_extremos():
    assert utils.checar_faixa_kpi(100, utils.FAIXAS_VOLUME_ANUAL_P2) == 150
    assert utils.checar_faixa_kpi(99_999, utils.FAIXAS_VOLUME_ANUAL_P2) == 0
    assert utils.checar_faixa_kpi(5389, utils.FAIXAS_VOLUME_ANUAL_P2) == 100


def test_calcular_metricas_serie_ignora_zero_no_mape():
    m = utils.calcular_metricas_serie([0, 10, 20], [1, 12, 18])
    assert m["MAE"] == pytest.approx(1.67, abs=0.01)
    assert not np.isnan(m["MAPE_%"])


def test_log1p_bias_corrected_maior_que_expm1_ingenuo():
    prev = np.log1p(np.array([10.0, 20.0]))
    resid = np.array([-0.5, 0.5, -0.3, 0.3])
    corrigido = utils.log1p_bias_corrected_forecast(prev, resid)
    assert (corrigido > np.expm1(prev)).all()


def test_calibrar_threshold_por_custo_penaliza_fn_mais_caro():
    y = np.array([0, 0, 0, 0, 1, 1])
    s = np.array([0.1, 0.2, 0.3, 0.6, 0.5, 0.9])
    barato_fn = utils.calibrar_threshold_por_custo(y, s, 1, 1)
    caro_fn = utils.calibrar_threshold_por_custo(y, s, 1, 100)
    assert caro_fn["recall_no_threshold"] >= barato_fn["recall_no_threshold"]


# ---------------------------------------------------------------------
# 2. Seção 17 — censura de elegibilidade e guardrail
# ---------------------------------------------------------------------

def _df_flag(prop_por_semana):
    linhas = []
    inicio = pd.Timestamp("2025-01-06")  # segunda-feira
    for i, p in enumerate(prop_por_semana):
        for d in range(7):
            for j in range(20):
                linhas.append({
                    "Aberto": inicio + pd.Timedelta(weeks=i, days=d, hours=j),
                    "Entrou para KPI?": "SIM" if j < round(p * 20) else "NAO",
                })
    return pd.DataFrame(linhas)


def test_proporcao_elegivel_por_semana_bate_com_sintetico():
    df = _df_flag([0.5, 0.5, 0.25])
    prop = utils.proporcao_elegivel_por_semana(df)
    assert len(prop) == 3 and prop.iloc[-1] == pytest.approx(0.25)


def test_detectar_censura_pega_queda_final_e_da_data_de_corte():
    prop = pd.Series([0.5] * 24 + [0.45, 0.15, 0.05],
                     index=pd.period_range("2025-01-06", periods=27, freq="W"))
    res = utils.detectar_censura_elegibilidade(prop, semanas_referencia=20, semanas_finais_max=4)
    assert res["censurado"] and res["n_semanas_censuradas"] == 2
    assert res["data_corte"] == prop.index[-2].start_time.normalize()


def test_detectar_censura_nao_dispara_com_serie_estavel():
    prop = pd.Series(np.full(30, 0.5) + np.linspace(-0.02, 0.02, 30),
                     index=pd.period_range("2025-01-06", periods=30, freq="W"))
    res = utils.detectar_censura_elegibilidade(prop)
    assert not res["censurado"] and res["data_corte"] is None


def test_detectar_censura_ignora_semana_baixa_isolada_no_meio():
    prop = pd.Series([0.5] * 25 + [0.1, 0.5, 0.5],
                     index=pd.period_range("2025-01-06", periods=28, freq="W"))
    res = utils.detectar_censura_elegibilidade(prop, semanas_finais_max=4)
    assert not res["censurado"]  # a semana baixa não é contígua ao fim


def test_detectar_censura_serie_curta_levanta_erro():
    prop = pd.Series([0.5] * 5, index=pd.period_range("2025-01-06", periods=5, freq="W"))
    with pytest.raises(ValueError):
        utils.detectar_censura_elegibilidade(prop)


def test_validar_previsao_producao_normal_nao_avisa(caplog):
    serie = pd.Series(np.full(120, 55.0), index=pd.date_range("2025-01-01", periods=120))
    with caplog.at_level(logging.WARNING, logger="cronos"):
        res = utils.validar_previsao_producao(55 * 7, serie)
    assert res["dentro_do_esperado"] and not caplog.records


def test_validar_previsao_producao_anomala_avisa(caplog):
    serie = pd.Series(np.full(120, 55.0), index=pd.date_range("2025-01-01", periods=120))
    with caplog.at_level(logging.WARNING, logger="cronos"):
        res = utils.validar_previsao_producao(168 - 12 * 7, serie)  # ~ o P3 real: 12/dia
    assert not res["dentro_do_esperado"] and res["desvio_pct"] < -50
    assert any("desvia" in r.message for r in caplog.records)


def test_validar_previsao_producao_serie_zerada_levanta_erro():
    with pytest.raises(ValueError):
        utils.validar_previsao_producao(10, pd.Series([0.0] * 60))


# ---------------------------------------------------------------------
# 3. Seção 18 — métrica por horizonte, IC conjunto, OLA
# ---------------------------------------------------------------------

class _ModeloNaive:
    """Imita a interface do pmdarima (predict/update) com um modelo naive:
    prevê sempre o último valor visto. Serve para testar a mecânica de
    origem rolante sem depender de pmdarima instalado."""

    def __init__(self, ultimo):
        self.ultimo = float(ultimo)
        self.n_updates = 0

    def predict(self, n_periods, X=None):
        return np.full(n_periods, self.ultimo)

    def update(self, y, X=None):
        self.ultimo = float(np.asarray(y)[-1])
        self.n_updates += 1


def test_avaliar_por_horizonte_naive_bate_com_calculo_manual():
    serie = pd.Series([10.0, 12.0, 11.0, 15.0, 14.0, 13.0, 16.0, 18.0, 17.0, 20.0])
    modelo = _ModeloNaive(ultimo=9.0)
    res = utils.avaliar_por_horizonte(modelo, serie, horizontes=(1, 3))
    # D+1: |y_t - y_{t-1}| com y_{-1}=9
    esperado_d1 = np.mean(np.abs(serie.values - np.r_[9.0, serie.values[:-1]]))
    esperado_d3 = np.mean(np.abs(serie.values[2:] - np.r_[9.0, serie.values[:-3]]))
    assert res["MAE_D+1"] == pytest.approx(esperado_d1, abs=0.01)
    assert res["MAE_D+3"] == pytest.approx(esperado_d3, abs=0.01)


def test_avaliar_por_horizonte_nao_altera_modelo_original():
    modelo = _ModeloNaive(ultimo=5.0)
    utils.avaliar_por_horizonte(modelo, pd.Series([1.0, 2.0, 3.0]), horizontes=(1,))
    assert modelo.ultimo == 5.0 and modelo.n_updates == 0


def test_avaliar_por_horizonte_horizonte_maior_que_teste_da_nan():
    res = utils.avaliar_por_horizonte(_ModeloNaive(1.0), pd.Series([1.0, 2.0]), horizontes=(1, 7))
    assert not np.isnan(res["MAE_D+1"]) and np.isnan(res["MAE_D+7"])


def test_avaliar_por_horizonte_piso_zero():
    class _Negativo(_ModeloNaive):
        def predict(self, n_periods, X=None):
            return np.full(n_periods, -100.0)
    res = utils.avaliar_por_horizonte(_Negativo(0), pd.Series([5.0, 5.0]), horizontes=(1,))
    assert res["MAE_D+1"] == pytest.approx(5.0)


def test_ic_conjunto_mais_estreito_que_soma_dos_limites_quando_erros_anticorrelacionados():
    rng = np.random.default_rng(1)
    r_p2 = rng.normal(0, 5, 365)
    r_p3 = -r_p2 + rng.normal(0, 0.5, 365)  # anticorrelacionados: a soma quase não varia
    prev = {"P2": np.full(7, 15.0), "P3": np.full(7, 55.0)}
    res = utils.bootstrap_prediction_interval_conjunto({"P2": r_p2, "P3": r_p3}, prev, n_boot=500)
    largura_total = res["total"]["ic_superior"] - res["total"]["ic_inferior"]
    largura_soma_limites = (res["P2"]["ic_superior"] + res["P3"]["ic_superior"]) - (res["P2"]["ic_inferior"] + res["P3"]["ic_inferior"])
    assert (largura_total < largura_soma_limites).all()
    assert res["total"]["w_inferior"] <= 70 * 7 <= res["total"]["w_superior"]


def test_ic_conjunto_piso_zero_e_chaves_divergentes():
    res = utils.bootstrap_prediction_interval_conjunto(
        {"P2": np.array([-50.0, -40.0, 10.0])}, {"P2": np.array([1.0, 1.0])}, n_boot=100)
    assert (res["P2"]["ic_inferior"] >= 0).all()
    with pytest.raises(ValueError):
        utils.bootstrap_prediction_interval_conjunto({"P2": np.zeros(3)}, {"P3": np.zeros(2)})
    with pytest.raises(ValueError):
        utils.bootstrap_prediction_interval_conjunto({"P2": np.zeros(3), "P3": np.zeros(4)}, {"P2": np.zeros(2), "P3": np.zeros(2)})


def test_taxa_violacao_historica_por_prioridade_recorte_recente():
    df = pd.DataFrame({
        "Prioridade": ["P2"] * 4 + ["P3"] * 4,
        "target": [1, 0, 0, 0, 0, 0, 1, 1],
        "Aberto": pd.to_datetime(["2025-01-01", "2025-06-01", "2025-11-01", "2025-12-01"] * 2),
    })
    tudo = utils.taxa_violacao_historica_por_prioridade(df)
    recente = utils.taxa_violacao_historica_por_prioridade(df, time_col="Aberto", semanas_recentes=8)
    assert tudo["P2"] == pytest.approx(0.25) and tudo["P3"] == pytest.approx(0.5)
    assert recente["P2"] == 0.0 and recente["P3"] == 1.0
    with pytest.raises(ValueError):
        utils.taxa_violacao_historica_por_prioridade(df, semanas_recentes=8)


def test_projetar_ola_esperado_soma_e_ic():
    prev = {"P2": np.array([10.0, 10.0]), "P3": np.array([50.0, 60.0])}
    taxa = {"P2": 0.01, "P3": 0.02}
    out = utils.projetar_ola_esperado(prev, taxa, ic_superior_por_prioridade={"P2": np.array([20.0, 20.0]), "P3": np.array([80.0, 80.0])})
    assert out["ola_esperado_total"].tolist() == pytest.approx([1.1, 1.3])
    assert out["ola_esperado_total_ic_sup"].tolist() == pytest.approx([1.8, 1.8])
    with pytest.raises(ValueError):
        utils.projetar_ola_esperado(prev, {"P2": 0.01})


# ---------------------------------------------------------------------
# 4. Seção 19 — threshold fora do teste (CatBoost)
# ---------------------------------------------------------------------

def test_separar_validacao_temporal_respeita_ordem():
    df = pd.DataFrame({"t": pd.date_range("2025-01-01", periods=10)[::-1], "v": range(10)})
    tr, va = utils.separar_validacao_temporal(df, "t", 0.3)
    assert len(tr) == 7 and len(va) == 3
    assert tr["t"].max() < va["t"].min()


def test_avaliar_threshold_contas_basicas():
    y = np.array([1, 0, 1, 0, 0])
    s = np.array([0.9, 0.8, 0.2, 0.1, 0.1])
    res = utils.avaliar_threshold(y, s, 0.5)
    assert res == {"threshold": 0.5, "precisao": 0.5, "recall": 0.5, "vp": 1, "fp": 1, "fn": 1, "n_alertas": 2}


def _df_classificacao(n=600, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "Aberto": pd.date_range("2025-01-01", periods=n, freq="6h"),
        "Prioridade": rng.choice(["2 - Alta", "3 - Média"], n),
        "x1": rng.normal(size=n),
        "x2": rng.normal(size=n),
    })
    logit = -3 + 2.0 * df["x1"] + (df["Prioridade"] == "2 - Alta") * 0.8
    df["target"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


@pytest.mark.slow
def test_calibrar_threshold_fold_usa_so_treino():
    pytest.importorskip("catboost")
    df = _df_classificacao()
    params = {"iterations": 60, "depth": 3, "learning_rate": 0.1}
    res = utils.calibrar_threshold_fold(
        df, "target", ["Prioridade"], None, "Aberto", params, 1, 15, frac_validacao=0.25)
    assert 0 < res["threshold_otimo"] < 1
    assert res["n_validacao"] == 150 and res["n_positivos_validacao"] > 0


@pytest.mark.slow
def test_calibrar_threshold_fold_sem_positivos_na_validacao_levanta_erro():
    pytest.importorskip("catboost")
    df = _df_classificacao()
    df.loc[df["Aberto"] >= df["Aberto"].quantile(0.75), "target"] = 0
    with pytest.raises(ValueError):
        utils.calibrar_threshold_fold(df, "target", ["Prioridade"], None, "Aberto",
                                      {"iterations": 20}, 1, 15, frac_validacao=0.25)


@pytest.mark.slow
def test_treinar_catboost_fold_nao_recebe_eval_set_de_teste():
    """Pendência 6: o fit não pode mais receber o teste. Checa pela assinatura
    do resultado e pela ausência de métricas de eval no modelo."""
    pytest.importorskip("catboost")
    df = _df_classificacao()
    tr, te = df.iloc[:450], df.iloc[450:]
    res = utils.treinar_catboost_fold(tr, te, "target", ["Prioridade"], None,
                                      params={"iterations": 30, "depth": 3}, time_col="Aberto")
    assert len(res["y_score"]) == len(te)
    assert res["modelo"].get_evals_result() == {} or "validation" not in res["modelo"].get_evals_result()


# ---------------------------------------------------------------------
# 5. Seção 20 — SHAP e leitura descritiva
# ---------------------------------------------------------------------

def test_ranquear_features_por_shap_ordena_por_magnitude():
    shap = np.array([[1.0, -0.1, 0.0], [-1.0, -0.1, 0.0], [1.0, -0.1, 0.0]])
    r = utils.ranquear_features_por_shap(shap, ["a", "b", "c"], top_n=3)
    assert r["feature"].tolist() == ["a", "b", "c"]
    assert r.loc[0, "shap_media_com_sinal"] == pytest.approx(1 / 3)
    assert r.loc[1, "shap_media_com_sinal"] == pytest.approx(-0.1)


def test_explicar_chamado_individual_direcao_e_top_n():
    shap = np.array([[0.5, -2.0, 0.1]])
    x = pd.Series(["texto", 3.0, 9], index=["a", "b", "c"])
    e = utils.explicar_chamado_individual(shap, ["a", "b", "c"], x, 0, -5.0, top_n=2)
    assert e["feature"].tolist() == ["b", "a"]
    assert e["empurra_risco"].tolist() == ["para baixo", "para cima"]
    assert e.loc[0, "valor_no_chamado"] == 3.0


def test_top_razoes_por_chamado_formato():
    shap = np.array([[0.5, -2.0, 0.1]])
    assert utils.top_razoes_por_chamado(shap, ["a", "b", "c"], 0, top_n=2) == "b (-); a (+)"


def test_intervalo_wilson_dois_em_trinta_e_largo():
    inf, sup = utils.intervalo_wilson(np.array([2]), np.array([30]))
    assert inf[0] < 0.02 and sup[0] > 0.20  # ~1% a ~22%, indistinguível da média de 1%
    inf0, sup0 = utils.intervalo_wilson(np.array([0]), np.array([100]))
    assert inf0[0] == 0.0 and 0.02 < sup0[0] < 0.05


def test_taxa_violacao_por_categoria_min_casos_e_ordenacao_por_ic():
    df = pd.DataFrame({
        "tpl": ["raro"] * 30 + ["comum"] * 1000 + ["pequeno"] * 5,
        "target": [1, 1] + [0] * 28 + [1] * 30 + [0] * 970 + [1] * 5,
    })
    por_taxa = utils.taxa_violacao_por_categoria(df, "tpl", "target", min_casos=30, top_n=5)
    assert "pequeno" not in por_taxa["tpl"].tolist()
    assert por_taxa.iloc[0]["tpl"] == "raro"  # 6,67% > 3%
    por_ic = utils.taxa_violacao_por_categoria(df, "tpl", "target", min_casos=30, top_n=5, ordenar_por="ic_inferior_pct")
    assert por_ic.iloc[0]["tpl"] == "comum"  # limite inferior de 30/1000 supera o de 2/30
    assert set(["n_casos", "n_violacoes", "taxa_violacao_pct", "ic_inferior_pct", "ic_superior_pct"]) <= set(por_ic.columns)
    with pytest.raises(ValueError):
        utils.taxa_violacao_por_categoria(df, "tpl", "target", ordenar_por="nao_existe")


@pytest.mark.slow
def test_calcular_shap_values_propriedade_aditiva():
    pytest.importorskip("catboost")
    from catboost import CatBoostClassifier, Pool
    from scipy.special import logit

    df = _df_classificacao(n=400)
    X, y = df[["Prioridade", "x1", "x2"]], df["target"]
    modelo = CatBoostClassifier(iterations=40, depth=3, verbose=False, random_state=0)
    modelo.fit(Pool(X, y, cat_features=["Prioridade"]))

    shap, base = utils.calcular_shap_values(modelo, X, ["Prioridade"], None)
    assert shap.shape == (400, 3)
    p = modelo.predict_proba(Pool(X, cat_features=["Prioridade"]))[:, 1]
    reconstruido = shap.sum(axis=1) + base
    assert np.allclose(reconstruido, logit(np.clip(p, 1e-9, 1 - 1e-9)), atol=1e-4)
