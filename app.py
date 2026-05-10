import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="BTC 1-2-3 Probabilístico",
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

    senha = st.text_input(
        "Digite a senha:",
        type="password"
    )

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

st.title("₿ Bitcoin 1-2-3 Probabilístico")

st.markdown("""
Detector estrutural de pivô 1-2-3 no gráfico diário do Bitcoin.

O sistema calcula:

- probabilidade histórica;
- tempo médio até o gain;
- drawdown histórico;
- score probabilístico;
- qualidade estrutural do pivô.
""")

# =========================================================
# INPUTS
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    alvo = st.slider(
        "Gain (%)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5
    )

with col2:
    anos = st.slider(
        "Histórico (anos)",
        min_value=1,
        max_value=15,
        value=10
    )

with col3:
    adx_min = st.slider(
        "ADX mínimo",
        min_value=10,
        max_value=40,
        value=20
    )

with col4:
    pivots = st.slider(
        "Força do pivô",
        min_value=2,
        max_value=10,
        value=3
    )

# =========================================================
# DOWNLOAD
# =========================================================

@st.cache_data
def load_data(periodo):

    df = yf.download(
        "BTC-USD",
        period=f"{periodo}y",
        interval="1d",
        auto_adjust=True
    )

    return df

df = load_data(anos)

# =========================================================
# INDICADORES
# =========================================================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_dmi(data, period=14):

    high = data['High']
    low = data['Low']
    close = data['Close']

    plus_dm = high.diff()
    minus_dm = low.diff() * -1

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = (
        100 *
        (plus_dm.rolling(period).mean() / atr)
    )

    minus_di = (
        100 *
        (minus_dm.rolling(period).mean() / atr)
    )

    dx = (
        abs(plus_di - minus_di)
        / (plus_di + minus_di)
    ) * 100

    adx = dx.rolling(period).mean()

    return plus_di, minus_di, adx

def atr(df, period=14):

    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())

    ranges = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    )

    true_range = ranges.max(axis=1)

    return true_range.rolling(period).mean()

# =========================================================
# CALCULA INDICADORES
# =========================================================

df['EMA69'] = ema(df['Close'], 69)

plus_di, minus_di, adx = calculate_dmi(df)

df['DI+'] = plus_di
df['DI-'] = minus_di
df['ADX'] = adx
df['ATR'] = atr(df)

# =========================================================
# SWINGS REAIS
# =========================================================

def swing_low(df, i, n=3):

    return (
        df['Low'].iloc[i]
        == min(df['Low'].iloc[i-n:i+n+1])
    )

def swing_high(df, i, n=3):

    return (
        df['High'].iloc[i]
        == max(df['High'].iloc[i-n:i+n+1])
    )

# =========================================================
# DETECÇÃO PIVÔ 1-2-3
# =========================================================

resultados = []

for i in range(30, len(df)-30):

    try:

        # =========================================
        # PROCURA PONTO 1
        # =========================================

        if not swing_low(df, i, pivots):
            continue

        p1_idx = i
        p1 = df.iloc[p1_idx]

        # =========================================
        # PROCURA PONTO 2
        # =========================================

        p2_idx = None

        for j in range(
            p1_idx + 1,
            p1_idx + 15
        ):

            if swing_high(df, j, pivots):

                p2_idx = j
                break

        if p2_idx is None:
            continue

        p2 = df.iloc[p2_idx]

        # =========================================
        # PROCURA PONTO 3
        # =========================================

        p3_idx = None

        for k in range(
            p2_idx + 1,
            p2_idx + 15
        ):

            if swing_low(df, k, pivots):

                if (
                    df.iloc[k]['Low']
                    > p1['Low']
                ):

                    p3_idx = k
                    break

        if p3_idx is None:
            continue

        p3 = df.iloc[p3_idx]

        # =========================================
        # ROMPIMENTO
        # =========================================

        rompimento_idx = None

        for r in range(
            p3_idx + 1,
            min(p3_idx + 15, len(df))
        ):

            if (
                df.iloc[r]['High']
                > p2['High']
            ):

                rompimento_idx = r
                break

        if rompimento_idx is None:
            continue

        entrada = df.iloc[rompimento_idx]['Close']

        # =========================================
        # FILTROS
        # =========================================

        if entrada < p3['EMA69']:
            continue

        if p3['DI+'] < p3['DI-']:
            continue

        if p3['ADX'] < adx_min:
            continue

        # =========================================
        # SCORE
        # =========================================

        score = 0

        # candle força
        candle_range = (
            (p3['High'] - p3['Low'])
            / p3['Close']
        ) * 100

        if candle_range > 2:
            score += 20

        # distância EMA
        dist_ema = (
            (p3['Close'] - p3['EMA69'])
            / p3['EMA69']
        ) * 100

        if dist_ema < 8:
            score += 20

        # adx
        if p3['ADX'] > 25:
            score += 20

        # dmi
        if p3['DI+'] > p3['DI-']:
            score += 20

        # atr
        atr_perc = (
            p3['ATR']
            / p3['Close']
        ) * 100

        if atr_perc < 5:
            score += 20

        # =========================================
        # BACKTEST
        # =========================================

        alvo_preco = (
            entrada *
            (1 + alvo/100)
        )

        gain = False
        dias = 0
        pior_dd = 0

        for z in range(
            rompimento_idx + 1,
            len(df)
        ):

            preco = df.iloc[z]['Close']

            dd = (
                (preco / entrada) - 1
            ) * 100

            if dd < pior_dd:
                pior_dd = dd

            dias += 1

            if preco >= alvo_preco:

                gain = True
                break

        resultados.append({

            'Data': df.index[rompimento_idx],
            'Entrada': round(entrada, 2),
            'P1': round(p1['Low'], 2),
            'P2': round(p2['High'], 2),
            'P3': round(p3['Low'], 2),
            'Score': score,
            'Gain': gain,
            'Dias': dias,
            'Pior_DD_%': round(pior_dd, 2),
            'ADX': round(p3['ADX'], 2),
            'ATR_%': round(atr_perc, 2),
            'Dist_EMA_%': round(dist_ema, 2)

        })

    except:
        pass

# =========================================================
# DATAFRAME
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:

    st.warning(
        "Nenhum pivô encontrado."
    )

    st.stop()

# =========================================================
# ESTATÍSTICAS
# =========================================================

total = len(res)

wins = len(
    res[res['Gain'] == True]
)

taxa = (
    wins / total
) * 100

dias_medio = (
    res[
        res['Gain'] == True
    ]['Dias'].mean()
)

pior_dd = res['Pior_DD_%'].min()

tempo_max = res['Dias'].max()

score_medio = res['Score'].mean()

# =========================================================
# DASHBOARD
# =========================================================

st.header("📊 Estatísticas")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Probabilidade",
    f"{taxa:.2f}%"
)

c2.metric(
    "Dias Médios",
    f"{dias_medio:.1f}"
)

c3.metric(
    "Pior Drawdown",
    f"{pior_dd:.2f}%"
)

c4.metric(
    "Maior Tempo",
    f"{tempo_max} dias"
)

c5.metric(
    "Score Médio",
    f"{score_medio:.1f}"
)

# =========================================================
# SETUP ATUAL
# =========================================================

st.header("📌 Último Setup Detectado")

ultimo = res.iloc[-1]

st.write(f"""
### Data:
{ultimo['Data']}

### Entrada:
{ultimo['Entrada']}

### Score:
{ultimo['Score']}

### Probabilidade histórica:
{taxa:.2f}%

### Pior drawdown histórico:
{pior_dd:.2f}%
""")

# =========================================================
# GRÁFICO
# =========================================================

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df['Close'],
        name='BTC'
    )
)

fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df['EMA69'],
        name='EMA69'
    )
)

fig.update_layout(
    height=700,
    title="Bitcoin Diário"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================================
# HISTÓRICO
# =========================================================

st.header("📋 Histórico")

st.dataframe(
    res.sort_values(
        by='Score',
        ascending=False
    ).reset_index(drop=True),
    use_container_width=True
)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Conclusão Matemática")

st.write(f"""
O sistema encontrou:

- {total} padrões 1-2-3;
- taxa histórica de gain:
{taxa:.2f}%;
- tempo médio:
{dias_medio:.1f} dias;
- pior drawdown:
{pior_dd:.2f}%.

O modelo NÃO prevê o futuro.

Ele mede probabilidade histórica
condicional baseada na estrutura
do pivô 1-2-3.
""")
