import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BTC Pullback Probabilístico",
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

    senha = st.text_input("Digite a senha:", type="password")

    if st.button("Entrar"):
        if senha == SENHA:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.stop()

# =========================================================
# TÍTULO
# =========================================================

st.title("₿ BTC Pullback Continuation Probabilístico (EMA69)")

st.markdown("""
Modelo focado em **continuação de tendência no Bitcoin**:

- tendência via EMA69
- impulso + pullback + rompimento
- probabilidade histórica de +3%
- comportamento estatístico do BTC
""")

# =========================================================
# INPUTS
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:
    alvo = st.slider("Alvo (%)", 1.0, 10.0, 3.0, 0.5)

with col2:
    anos = st.slider("Histórico (anos)", 1, 15, 10)

with col3:
    lookback = st.slider("Lookback estrutura", 10, 80, 30)

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
# INDICADOR BASE
# =========================================================

df["EMA69"] = df["Close"].ewm(span=69, adjust=False).mean()

# =========================================================
# ESTRUTURA DE MERCADO
# =========================================================

def is_uptrend(i):
    return df["Close"].iloc[i] > df["EMA69"].iloc[i]

def highest_high(i1, i2):
    return df["High"].iloc[i1:i2].max()

def lowest_low(i1, i2):
    return df["Low"].iloc[i1:i2].min()

# =========================================================
# DETECÇÃO: PULLBACK CONTINUATION
# =========================================================

resultados = []

for i in range(lookback, len(df) - lookback):

    try:

        # 1. TENDÊNCIA
        if not is_uptrend(i):
            continue

        # 2. IMPULSO (últimos candles)
        impulse_low = lowest_low(i - lookback, i)
        impulse_high = highest_high(i - lookback, i)

        impulse_size = (impulse_high - impulse_low) / impulse_low

        if impulse_size < 0.03:
            continue

        # 3. PULLBACK (últimos candles)
        pullback_low = lowest_low(i - 10, i)
        pullback_retrace = (impulse_high - pullback_low) / impulse_high

        if pullback_retrace > 0.6:
            continue

        # 4. ROMPIMENTO (continuação)
        breakout_level = impulse_high

        entry_idx = None

        for j in range(i, min(i + 10, len(df))):

            if df["High"].iloc[j] > breakout_level:
                entry_idx = j
                break

        if entry_idx is None:
            continue

        entry_price = df["Close"].iloc[entry_idx]

        # 5. FILTRO FINAL DE TENDÊNCIA
        if entry_price < df["EMA69"].iloc[entry_idx]:
            continue

        # =========================================================
        # BACKTEST +3%
        # =========================================================

        target = entry_price * (1 + alvo / 100)

        win = False
        days = 0
        worst_dd = 0

        for k in range(entry_idx + 1, len(df)):

            price = df["Close"].iloc[k]

            dd = (price / entry_price - 1) * 100
            worst_dd = min(worst_dd, dd)

            days += 1

            if price >= target:
                win = True
                break

        resultados.append({
            "Data": df.index[entry_idx],
            "Entrada": entry_price,
            "Impulso%": round(impulse_size * 100, 2),
            "Pullback%": round(pullback_retrace * 100, 2),
            "Gain": win,
            "Dias": days,
            "DD_%": round(worst_dd, 2)
        })

    except:
        pass

# =========================================================
# RESULTADOS
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:
    st.warning("Nenhum padrão de continuação encontrado.")
    st.stop()

# =========================================================
# ESTATÍSTICAS
# =========================================================

total = len(res)
wins = len(res[res["Gain"] == True])

taxa = (wins / total) * 100

dias_medios = res[res["Gain"] == True]["Dias"].mean()

dd_min = res["DD_%"].min()

# =========================================================
# DASHBOARD
# =========================================================

st.header("📊 Estatísticas do Modelo (BTC Continuation)")

c1, c2, c3 = st.columns(3)

c1.metric("Probabilidade de +3%", f"{taxa:.2f}%")
c2.metric("Dias médios até alvo", f"{dias_medios:.1f}")
c3.metric("Pior drawdown", f"{dd_min:.2f}%")

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

fig.update_layout(height=650, title="BTC Diário - Estrutura EMA69")

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# HISTÓRICO
# =========================================================

st.header("📋 Operações Detectadas")

st.dataframe(
    res.sort_values("Gain", ascending=False),
    use_container_width=True
)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Leitura Matemática")

st.write(f"""
O modelo agora mede:

- tendência (EMA69)
- impulso estatístico
- pullback médio
- rompimento de continuação
- probabilidade histórica de atingir +{alvo}%

Taxa observada:
**{taxa:.2f}%**

Isso não prevê o futuro — mede comportamento recorrente do BTC em tendência.
""")
