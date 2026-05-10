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
Este aplicativo detecta automaticamente padrões **1-2-3 de compra**
no gráfico diário do Bitcoin e calcula:

- probabilidade histórica de atingir gain;
- tempo médio até o alvo;
- drawdown antes do gain;
- score probabilístico;
- similaridade histórica;
- qualidade da formação.
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
    score_min = st.slider(
        "Score mínimo",
        min_value=0,
        max_value=100,
        value=70
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

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

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
# DETECÇÃO 1-2-3
# =========================================================

resultados = []

for i in range(30, len(df) - 30):

    try:

        c1 = df.iloc[i - 2]
        c2 = df.iloc[i - 1]
        c3 = df.iloc[i]

        # =========================================
        # ESTRUTURA 1-2-3
        # =========================================

        fundo1 = c1['Low']
        topo2 = c2['High']
        fundo3 = c3['Low']

        estrutura_valida = (
            fundo3 > fundo1
        )

        rompimento = (
            df.iloc[i + 1]['Close'] > topo2
        )

        tendencia = (
            c3['Close'] > c3['EMA69']
        )

        dmi_ok = (
            c3['DI+'] > c3['DI-']
        )

        adx_ok = (
            c3['ADX'] > adx_min
        )

        if (
            estrutura_valida
            and rompimento
            and tendencia
            and dmi_ok
            and adx_ok
        ):

            entrada = df.iloc[i + 1]['Close']

            alvo_preco = entrada * (
                1 + alvo / 100
            )

            # =========================================
            # MÉTRICAS DO PADRÃO
            # =========================================

            candle_range = (
                (c3['High'] - c3['Low'])
                / c3['Close']
            ) * 100

            distancia_ema = (
                (c3['Close'] - c3['EMA69'])
                / c3['EMA69']
            ) * 100

            atr_perc = (
                c3['ATR']
                / c3['Close']
            ) * 100

            score = 0

            # =========================================
            # SCORE
            # =========================================

            if candle_range > 2:
                score += 20

            if distancia_ema < 8:
                score += 20

            if c3['ADX'] > 25:
                score += 20

            if c3['DI+'] > c3['DI-']:
                score += 20

            if atr_perc < 5:
                score += 20

            # =========================================
            # BACKTEST
            # =========================================

            gain = False
            dias = 0
            pior_dd = 0

            for j in range(i + 2, len(df)):

                preco = df.iloc[j]['Close']

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
                'Data': df.index[i],
                'Entrada': round(entrada, 2),
                'Score': score,
                'Gain': gain,
                'Dias': dias,
                'Pior_DD_%': round(pior_dd, 2),
                'ADX': round(c3['ADX'], 2),
                'ATR_%': round(atr_perc, 2),
                'Dist_EMA_%': round(distancia_ema, 2)
            })

    except:
        pass

# =========================================================
# DATAFRAME
# =========================================================

res = pd.DataFrame(resultados)

if len(res) == 0:

    st.warning("Nenhum setup encontrado.")

    st.stop()

# =========================================================
# FILTRO SCORE
# =========================================================

res = res[
    res['Score'] >= score_min
]

if len(res) == 0:

    st.warning(
        "Nenhum setup encontrado para o score."
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
# INTERPRETAÇÃO
# =========================================================

st.subheader("🧠 Interpretação")

if taxa >= 80:
    st.success(
        "Padrão historicamente muito forte."
    )

elif taxa >= 65:
    st.info(
        "Boa probabilidade histórica."
    )

elif taxa >= 50:
    st.warning(
        "Probabilidade moderada."
    )

else:
    st.error(
        "Probabilidade historicamente fraca."
    )

# =========================================================
# GRÁFICO BTC
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
    height=650,
    title="Bitcoin Diário"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================================
# HISTÓRICO
# =========================================================

st.subheader("📋 Histórico dos Setups")

st.dataframe(
    res.sort_values(
        by='Score',
        ascending=False
    ).reset_index(drop=True),
    use_container_width=True
)

# =========================================================
# SIMILARIDADE HISTÓRICA
# =========================================================

st.subheader("🧬 Top 10 padrões mais fortes")

top = res.sort_values(
    by=['Score', 'Pior_DD_%'],
    ascending=[False, False]
).head(10)

st.dataframe(
    top,
    use_container_width=True
)

# =========================================================
# STATUS ATUAL
# =========================================================

ultimo = df.iloc[-1]

st.header("📌 Situação Atual")

status = []

if ultimo['Close'] > ultimo['EMA69']:
    status.append("✅ Acima EMA69")
else:
    status.append("❌ Abaixo EMA69")

if ultimo['DI+'] > ultimo['DI-']:
    status.append("✅ DI+ acima DI-")
else:
    status.append("❌ DI+ abaixo DI-")

if ultimo['ADX'] > adx_min:
    status.append("✅ ADX forte")
else:
    status.append("❌ ADX fraco")

for s in status:
    st.write(s)

# =========================================================
# CONCLUSÃO
# =========================================================

st.header("📘 Conclusão Matemática")

st.write(f"""
Historicamente:

- o padrão 1-2-3 atingiu +{alvo}% em
aproximadamente {taxa:.2f}% das vezes;

- o tempo médio foi de
{dias_medio:.1f} dias;

- o pior drawdown histórico foi de
{pior_dd:.2f}%;

- o maior tempo preso em operação foi
de {tempo_max} dias.

O sistema NÃO prevê o futuro.

Ele mede probabilidades históricas
condicionais.
""")
