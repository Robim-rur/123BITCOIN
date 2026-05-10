import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="BTC 1-2-3 Híbrido", layout="wide")

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

st.title("₿ BTC 1-2-3 HÍBRIDO (Reversão + Continuação)")

st.markdown("""
Modelo híbrido:

✔ 1-2-3 reversão (clássico)  
✔ 1-2-3 continuação (BTC real)  
✔ regime de tendência (EMA69)  
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

lookback = 25

# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data(periodo):
    return yf.download("BTC-USD", period=f"{periodo}y", interval="1d", auto_adjust=True)

df = load_data(anos)

# =========================================================
# INDICADORES
# =========================================================

df["EMA69"] = df["Close"].ewm(span=69, adjust=False).mean()

df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

# =========================================================
# REGIME DE MERCADO
# =========================================================

def trend_up(i):
    return df["Close"].iloc[i] > df["EMA69"].iloc[i]

# =========================================================
# DETECÇÃO SWING SIMPLIFICADA (menos rígida)
# =========================================================

def swing_low(i):
    return df["Low"].iloc[i] == df["Low"].iloc[i-3:i+4].min()

def swing_high(i):
    return df["High"].iloc[i] == df["High"].iloc[i-3:i+4].max()

# =========================================================
# DETECÇÃO HÍBRIDA 1-2-3
# =========================================================

resultados = []

for i in range(lookback, len(df)-lookback):

    try:

        # =====================================================
        # REGIME
        # =====================================================

        bullish = trend_up(i)

        # =====================================================
        # 1-2-3 REVERSÃO (modo clássico)
        # =====================================================

        if not bullish:

            if not swing_low(i):
                continue

            p1 = df.iloc[i]

            p2_idx = None
            for j in range(i+1, i+10):
                if swing_high(j):
                    p2_idx = j
                    break

            if p2_idx is None:
                continue

            p2 = df.iloc[p2_idx]

            p3_idx = None
            for k in range(p2_idx+1, p2_idx+15):
                if swing_low(k) and df.iloc[k]["Low"] > p1["Low"]:
                    p3_idx = k
                    break

            if p3_idx is None:
                continue

            entry_idx = None
            for r in range(p3_idx+1, p3_idx+15):
                if df.iloc[r]["High"] > p2["High"]:
                    entry_idx = r
                    break

            if entry_idx is None:
                continue

            entry = df.iloc[entry_idx]["Close"]

        # =====================================================
        # 1-2-3 CONTINUAÇÃO (BTC REAL)
        # =====================================================

        else:

            impulse_high = df["High"].iloc[i-lookback:i].max()
            impulse_low = df["Low"].iloc[i-lookback:i].min()

            impulse = (impulse_high - impulse_low) / impulse_low

            if impulse < 0.02:
                continue

            pullback = (impulse_high - df["Low"].iloc[i]) / impulse_high

            if pullback > 0.75:
                continue

            entry_idx = None

            for j in range(i, i+20):

                if j >= len(df):
                    break

                if df.iloc[j]["High"] > impulse_high:
                    entry_idx = j
                    break

            if entry_idx is None:
                continue

            entry = df.iloc[entry_idx]["Close"]

        # =====================================================
        # BACKTEST +3%
        # =====================================================

        target = entry * (1 + alvo/100)

        win = False
        dias = 0
        dd = 0

        for k in range(entry_idx+1, len(df)):

            price = df.iloc[k]["Close"]

            dd = min(dd, (price/entry - 1)*100)

            dias += 1

            if price >= target:
                win = True
                break

        resultados.append({
            "Data": df.index[entry_idx],
            "Entrada": entry,
            "Gain": win,
            "Dias": dias,
            "DD_%": round(dd,2),
            "Regime": "Trend" if bullish else "Reversal"
        })

    except:
        pass

# =========================================================
# RESULTADOS
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:
    st.warning("Nenhum setup encontrado.")
    st.stop()

# =========================================================
# ESTATÍSTICAS
# =========================================================

total = len(res)
wins = len(res[res["Gain"] == True])

taxa = (wins/total)*100

dias_medios = res[res["Gain"]==True]["Dias"].mean()

# =========================================================
# DASHBOARD
# =========================================================

st.header("📊 Estatísticas Híbridas")

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

st.header("📋 Operações")

st.dataframe(res.sort_values("Gain", ascending=False), use_container_width=True)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura do Modelo")

st.write(f"""
Modelo híbrido:

- Reversão 1-2-3 tradicional em tendência de baixa
- Continuação 1-2-3 em tendência de alta (BTC real)

Taxa histórica: {taxa:.2f}%
""")
