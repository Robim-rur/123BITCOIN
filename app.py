import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BTC Detector Real de Entradas",
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

st.title("₿ BTC Detector Real de Entradas (Regime + Breakout)")

st.markdown("""
Este modelo detecta **entradas reais do BTC diário**, baseado em:

✔ regime de tendência  
✔ compressão de volatilidade  
✔ expansão (impulso real)  
✔ breakout de estrutura  
✔ probabilidade de +3%  

❌ não usa 1-2-3  
❌ não usa pivô rígido  
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

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

df["VOL"] = df["Close"].pct_change().rolling(14).std()

# =========================================================
# REGIME DE TENDÊNCIA
# =========================================================

def is_trend(i):

    if i < 70:
        return False

    return df["Close"].iloc[i] > df["EMA69"].iloc[i]

# =========================================================
# COMPRESSÃO DE MERCADO
# =========================================================

def is_compression(i):

    atr_now = df["ATR"].iloc[i]
    atr_mean = df["ATR"].iloc[i-lookback:i].mean()

    if pd.isna(atr_now) or pd.isna(atr_mean):
        return False

    return atr_now < atr_mean * 0.8

# =========================================================
# EXPANSÃO (IMPULSO REAL)
# =========================================================

def is_expansion(i):

    recent_high = df["High"].iloc[i-lookback:i].max()
    recent_low = df["Low"].iloc[i-lookback:i].min()

    move = (recent_high - recent_low) / recent_low

    return move > 0.03

# =========================================================
# BREAKOUT REAL
# =========================================================

def breakout(i):

    resistance = df["High"].iloc[i-lookback:i].max()

    return df["High"].iloc[i] >= resistance * 0.995

# =========================================================
# SCORE DE ENTRADA REAL
# =========================================================

def entry_score(i):

    score = 0

    if is_trend(i):
        score += 40

    if is_compression(i):
        score += 20

    if is_expansion(i):
        score += 20

    if breakout(i):
        score += 20

    return score

# =========================================================
# DETECÇÃO DE ENTRADAS
# =========================================================

resultados = []

for i in range(lookback, len(df)-5):

    try:

        sc = entry_score(i)

        # filtro calibrado (não bloqueia tudo)
        if sc < 50:
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
    st.warning("Nenhuma entrada real detectada ainda.")
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

st.header("📊 Entradas Reais BTC")

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

st.header("📋 Entradas detectadas")

st.dataframe(res.sort_values("Score", ascending=False), use_container_width=True)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura do Modelo")

st.write(f"""
Este modelo detecta entradas reais do BTC baseadas em:

- tendência (EMA69)
- compressão de volatilidade
- expansão (impulso)
- breakout de estrutura

Taxa histórica: {taxa:.2f}%
""")
