import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="BTC Probabilístico Regime", layout="wide")

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

st.title("₿ BTC Probabilístico (Sem Sequência Fixa)")

st.markdown("""
Modelo baseado em **probabilidade de continuação em tendência**, não em padrões fixos.

✔ regime de mercado  
✔ força da tendência  
✔ compressão/expansão  
✔ breakout estatístico  
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

lookback = 30

# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data(periodo):
    return yf.download("BTC-USD", period=f"{periodo}y", interval="1d", auto_adjust=True)

df = load_data(anos)

# =========================================================
# INDICADORES BASE
# =========================================================

df["EMA69"] = df["Close"].ewm(span=69, adjust=False).mean()

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

df["RET"] = df["Close"].pct_change()

df["VOL"] = df["RET"].rolling(14).std()

# =========================================================
# REGIME DE TENDÊNCIA
# =========================================================

def trend_score(i):

    if i < 70:
        return 0

    above_ema = df["Close"].iloc[i] > df["EMA69"].iloc[i]

    ema_slope = df["EMA69"].iloc[i] - df["EMA69"].iloc[i-5]

    vol = df["VOL"].iloc[i]

    score = 0

    if above_ema:
        score += 40

    if ema_slope > 0:
        score += 20

    if vol > df["VOL"].mean():
        score += 20

    return score

# =========================================================
# FORÇA DE EXPANSÃO
# =========================================================

def expansion_score(i):

    high = df["High"].iloc[i-lookback:i].max()
    low = df["Low"].iloc[i-lookback:i].min()

    move = (high - low) / low

    if move > 0.05:
        return 30
    elif move > 0.03:
        return 20
    elif move > 0.015:
        return 10

    return 0

# =========================================================
# COMPRESSÃO / PULLBACK (flexível)
# =========================================================

def pullback_score(i):

    high = df["High"].iloc[i-lookback:i].max()

    retrace = (high - df["Low"].iloc[i]) / high

    if retrace < 0.2:
        return 30
    elif retrace < 0.35:
        return 20
    elif retrace < 0.5:
        return 10

    return 5

# =========================================================
# BREAKOUT PROBABILÍSTICO (SEM JANELA FIXA)
# =========================================================

def breakout_score(i):

    recent_high = df["High"].iloc[i-lookback:i].max()

    if df["Close"].iloc[i] > recent_high:
        return 40

    if df["High"].iloc[i] > recent_high * 0.98:
        return 20

    return 0

# =========================================================
# BACKTEST PROBABILÍSTICO
# =========================================================

resultados = []

for i in range(lookback, len(df)-5):

    try:

        ts = trend_score(i)
        ex = expansion_score(i)
        ps = pullback_score(i)
        bs = breakout_score(i)

        total_score = ts + ex + ps + bs

        # FILTRO MÍNIMO DE CONTEXTO
        if total_score < 70:
            continue

        entry = df["Close"].iloc[i]

        target = entry * (1 + alvo/100)

        win = False
        days = 0
        dd = 0

        for k in range(i+1, len(df)):

            price = df["Close"].iloc[k]

            dd = min(dd, (price/entry - 1)*100)

            days += 1

            if price >= target:
                win = True
                break

        resultados.append({
            "Data": df.index[i],
            "Entrada": entry,
            "Score": total_score,
            "Gain": win,
            "Dias": days,
            "DD_%": round(dd,2)
        })

    except:
        pass

# =========================================================
# RESULTADOS
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:
    st.warning("Nenhum setup probabilístico encontrado.")
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

st.header("📊 Modelo Probabilístico BTC")

c1,c2,c3 = st.columns(3)

c1.metric("Probabilidade +3%", f"{taxa:.2f}%")
c2.metric("Dias médios", f"{dias_medios:.1f}")
c3.metric("Total setups", total)

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

st.header("📋 Setups Detectados")

st.dataframe(res.sort_values("Score", ascending=False), use_container_width=True)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura do Modelo")

st.write(f"""
Modelo sem sequência fixa:

- tendência (EMA69)
- expansão de volatilidade
- pullback probabilístico
- breakout estatístico

Taxa histórica: {taxa:.2f}%
""")
