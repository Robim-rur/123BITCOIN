import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BTC Probabilístico Calibrado",
    layout="wide"
)

# =========================================================
# SENHA
# =========================================================

SENHA = "LUCRO6"

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:

    st.title("🔐 Acesso Restrito")

    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta")

    st.stop()

# =========================================================
# TÍTULO
# =========================================================

st.title("₿ BTC Probabilístico Calibrado (FUNCIONAL)")

st.markdown("""
Modelo ajustado para:

✔ detectar setups reais do BTC  
✔ evitar excesso de filtro  
✔ usar score normalizado  
✔ capturar continuação e reversão  
✔ foco em +3%
""")

# =========================================================
# INPUTS
# =========================================================

col1, col2 = st.columns(2)

with col1:
    alvo = st.slider("Alvo (%)", 1.0, 10.0, 3.0, 0.5)

with col2:
    anos = st.slider("Histórico (anos)", 1, 15, 10)

lookback = 30

# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data(periodo):
    return yf.download(
        "BTC-USD",
        period=f"{periodo}y",
        interval="1d",
        auto_adjust=True
    )

df = load_data(anos)

# =========================================================
# INDICADORES
# =========================================================

df["EMA69"] = df["Close"].ewm(span=69, adjust=False).mean()

df["RET"] = df["Close"].pct_change()

df["VOL"] = df["RET"].rolling(14).std()

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

# =========================================================
# FUNÇÕES DE CONTEXTO
# =========================================================

def trend(i):
    if i < 70:
        return False
    return df["Close"].iloc[i] > df["EMA69"].iloc[i]

def slope(i):
    return df["EMA69"].iloc[i] - df["EMA69"].iloc[i-5]

def expansion(i):

    high = df["High"].iloc[i-lookback:i].max()
    low = df["Low"].iloc[i-lookback:i].min()

    return (high - low) / low

def pullback(i):

    high = df["High"].iloc[i-lookback:i].max()

    return (high - df["Low"].iloc[i]) / high

def breakout(i):

    recent_high = df["High"].iloc[i-lookback:i].max()

    return df["High"].iloc[i] >= recent_high * 0.995

# =========================================================
# SCORE NORMALIZADO (0–100)
# =========================================================

def score(i):

    s = 0

    # tendência
    if trend(i):
        s += 35

    # inclinação EMA
    if slope(i) > 0:
        s += 15

    # expansão
    exp = expansion(i)
    if exp > 0.05:
        s += 20
    elif exp > 0.03:
        s += 12
    elif exp > 0.015:
        s += 6

    # pullback saudável
    pb = pullback(i)
    if pb < 0.2:
        s += 20
    elif pb < 0.35:
        s += 12
    elif pb < 0.5:
        s += 6

    # breakout leve (wick incluído)
    if breakout(i):
        s += 10

    return s

# =========================================================
# DETECÇÃO
# =========================================================

resultados = []

for i in range(lookback, len(df)-5):

    try:

        sc = score(i)

        # =====================================================
        # CALIBRAÇÃO (IMPORTANTE)
        # =====================================================

        if sc < 35:
            continue

        entry = df["Close"].iloc[i]

        target = entry * (1 + alvo/100)

        win = False
        dias = 0
        dd = 0

        for k in range(i+1, len(df)):

            price = df["Close"].iloc[k]

            dd = min(dd, (price/entry - 1)*100)

            dias += 1

            if price >= target:
                win = True
                break

        resultados.append({
            "Data": df.index[i],
            "Entrada": entry,
            "Score": sc,
            "Gain": win,
            "Dias": dias,
            "DD_%": round(dd, 2)
        })

    except:
        pass

# =========================================================
# RESULTADOS
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:
    st.warning("Nenhum setup detectado (ainda).")
    st.stop()

# =========================================================
# ESTATÍSTICAS
# =========================================================

total = len(res)
wins = len(res[res["Gain"] == True])

taxa = (wins / total) * 100

dias_medios = res[res["Gain"] == True]["Dias"].mean()

# =========================================================
# DASHBOARD
# =========================================================

st.header("📊 Estatísticas BTC")

c1,c2,c3 = st.columns(3)

c1.metric("Probabilidade +3%", f"{taxa:.2f}%")
c2.metric("Dias médios", f"{dias_medios:.1f}")
c3.metric("Setups", total)

# =========================================================
# GRÁFICO
# =========================================================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["Close"],
    name="BTC"
))

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["EMA69"],
    name="EMA69"
))

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# TABELA
# =========================================================

st.header("📋 Setups detectados")

st.dataframe(res.sort_values("Score", ascending=False), use_container_width=True)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura do Modelo")

st.write(f"""
Modelo calibrado com score probabilístico.

- não usa sequência fixa
- detecta contexto de tendência
- captura pullbacks e rompimentos leves

Taxa histórica: {taxa:.2f}%
""")
