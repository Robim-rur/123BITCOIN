import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BTC Modelo por Janela Probabilística",
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

st.title("₿ BTC Modelo por Janela Probabilística")

st.markdown("""
Este modelo detecta **zonas de entrada reais**, não candles isolados.

✔ análise por janela (10–20 candles)  
✔ regime de tendência  
✔ compressão + expansão  
✔ breakout estrutural  
✔ probabilidade de +3%  
""")

# =========================================================
# INPUTS
# =========================================================

col1, col2 = st.columns(2)

with col1:
    alvo = st.slider("Alvo (%)", 1.0, 10.0, 3.0, 0.5)

with col2:
    anos = st.slider("Histórico (anos)", 1, 15, 10)

window = 15

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

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

df["RET"] = df["Close"].pct_change()

df["VOL"] = df["RET"].rolling(14).std()

# =========================================================
# REGIME DE TENDÊNCIA
# =========================================================

def trend(i):
    if i < 70:
        return False
    return df["Close"].iloc[i] > df["EMA69"].iloc[i]

# =========================================================
# SCORE DE JANELA (NÚCLEO DO MODELO)
# =========================================================

def window_score(i):

    score = 0

    start = max(i-window, 0)

    # 1. tendência consistente na janela
    trend_hits = 0

    for t in range(start, i):
        if df["Close"].iloc[t] > df["EMA69"].iloc[t]:
            trend_hits += 1

    if trend_hits / window > 0.7:
        score += 35

    # 2. compressão de volatilidade
    atr_now = df["ATR"].iloc[i]
    atr_mean = df["ATR"].iloc[start:i].mean()

    if pd.notna(atr_now) and atr_now < atr_mean * 0.85:
        score += 20

    # 3. expansão recente
    high = df["High"].iloc[start:i].max()
    low = df["Low"].iloc[start:i].min()

    move = (high - low) / low

    if move > 0.05:
        score += 20
    elif move > 0.03:
        score += 10

    # 4. breakout iminente (proximidade da máxima)
    distance = (high - df["Close"].iloc[i]) / high

    if distance < 0.01:
        score += 25
    elif distance < 0.03:
        score += 15

    return score

# =========================================================
# DETECÇÃO POR JANELA
# =========================================================

resultados = []

for i in range(window, len(df)-5):

    try:

        sc = window_score(i)

        # filtro calibrado (janela já agrega info)
        if sc < 60:
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
            "Score_Janela": sc,
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
    st.warning("Nenhuma janela de entrada detectada.")
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

st.header("📊 Modelo por Janela BTC")

c1,c2,c3 = st.columns(3)

c1.metric("Probabilidade +3%", f"{taxa:.2f}%")
c2.metric("Dias médios", f"{dias_medios:.1f}")
c3.metric("Setups (janelas)", total)

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

st.header("📋 Janelas detectadas")

st.dataframe(res.sort_values("Score_Janela", ascending=False), use_container_width=True)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura do Modelo")

st.write(f"""
Modelo por janela:

- não depende de candle isolado
- detecta contexto de 10–20 candles
- identifica zonas de entrada reais
- alinhado com comportamento do BTC

Taxa histórica: {taxa:.2f}%
""")
