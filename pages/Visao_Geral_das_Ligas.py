import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(layout="wide")
st.title("📊 Análise por Rodadas da Liga")

# Conexão SQLite
engine = create_engine("sqlite:///data/database.sqlite")

# Carregar tabelas
teams = pd.read_sql("SELECT team_api_id, team_long_name FROM Team", engine)
leagues = pd.read_sql("SELECT id AS league_id, name AS league_name FROM League", engine)

# Query de partidas
query = """
SELECT 
    M.match_api_id,
    M.league_id,
    L.name AS league_name,
    M.season,
    M.stage,
    M.home_team_api_id,
    M.away_team_api_id,
    M.home_team_goal,
    M.away_team_goal
FROM Match M
JOIN League L ON M.league_id = L.id
"""
matches = pd.read_sql(query, engine)

# Juntar nomes dos times
matches = matches.merge(
    teams, left_on="home_team_api_id", right_on="team_api_id", how="left"
).rename(columns={"team_long_name": "team_home"})
matches = matches.merge(
    teams, left_on="away_team_api_id", right_on="team_api_id", how="left"
).rename(columns={"team_long_name": "team_away"})

# -------------------------------
# 🔹 Filtro de liga e temporada
# -------------------------------
selected_league = st.selectbox("Selecione a Liga", leagues["league_name"].sort_values())
league_matches = matches[matches["league_name"] == selected_league]

seasons = sorted(league_matches["season"].unique())
selected_seasons = st.multiselect("Selecione a(s) Temporada(s)", seasons, default=seasons[-1:])
league_matches = league_matches[league_matches["season"].isin(selected_seasons)]

# -------------------------------
# 🔹 Preparar dados por rodada
# -------------------------------
# Total de gols por rodada
gols_por_rodada = league_matches.groupby("stage")[["home_team_goal", "away_team_goal"]].sum()
gols_por_rodada["Total Gols"] = gols_por_rodada["home_team_goal"] + gols_por_rodada["away_team_goal"]
gols_por_rodada.reset_index(inplace=True)

# Resultados por rodada
resultados = []
for stage_num, group in league_matches.groupby("stage"):
    mandante_v = (group["home_team_goal"] > group["away_team_goal"]).sum()
    visitante_v = (group["away_team_goal"] > group["home_team_goal"]).sum()
    empates = (group["home_team_goal"] == group["away_team_goal"]).sum()
    resultados.append({
        "Rodada": stage_num,
        "Vitórias Mandante": mandante_v,
        "Vitórias Visitante": visitante_v,
        "Empates": empates
    })
resultados_df = pd.DataFrame(resultados)

# Média de gols por jogo por rodada
gols_por_rodada["Média Gols por Jogo"] = gols_por_rodada["Total Gols"] / league_matches.groupby("stage").size().values

# Total de gols por partida
league_matches["total_gols"] = league_matches["home_team_goal"] + league_matches["away_team_goal"]

# -------------------------------
# 🔹 Storytelling da Liga
# -------------------------------
total_partidas = len(league_matches)
total_gols = league_matches["total_gols"].sum()
media_gols_jogo = round(total_gols / total_partidas, 2) if total_partidas > 0 else 0
rodada_mais_gols = gols_por_rodada.loc[gols_por_rodada["Total Gols"].idxmax()]["stage"] \
    if not gols_por_rodada.empty else None

story_text = f"""
No período selecionado ({', '.join(selected_seasons)}), na liga **{selected_league}**:

- Foram disputadas **{total_partidas} partidas**, com um total de **{total_gols} gols**.
- A média de gols por partida foi de **{media_gols_jogo}**.
- A rodada com mais gols marcados foi a **rodada {rodada_mais_gols}**, com **{gols_por_rodada['Total Gols'].max()} gols**.
- Observa-se a tendência de partidas mais equilibradas com gols distribuídos ao longo das rodadas.
"""
st.subheader("📖 Storytelling da Liga")
st.markdown(story_text)

# -------------------------------
# 🔹 Tabela de classificação dos clubes
# -------------------------------
# Garantir que não haja NaN nos nomes dos times
league_matches["team_home"] = league_matches["team_home"].fillna("Unknown")
league_matches["team_away"] = league_matches["team_away"].fillna("Unknown")

# Lista de todos os times
all_teams = pd.unique(league_matches[["team_home", "team_away"]].values.ravel("K"))

# Criar lista para armazenar stats
table = []

for team in all_teams:
    home_matches = league_matches[league_matches["team_home"] == team]
    away_matches = league_matches[league_matches["team_away"] == team]
    
    partidas_jogadas = len(home_matches) + len(away_matches)
    
    vitorias = (home_matches["home_team_goal"] > home_matches["away_team_goal"]).sum() + \
               (away_matches["away_team_goal"] > away_matches["home_team_goal"]).sum()
    
    empates = (home_matches["home_team_goal"] == home_matches["away_team_goal"]).sum() + \
              (away_matches["away_team_goal"] == away_matches["home_team_goal"]).sum()
    
    derrotas = partidas_jogadas - vitorias - empates
    
    gols_marcados = home_matches["home_team_goal"].sum() + away_matches["away_team_goal"].sum()
    gols_sofridos = home_matches["away_team_goal"].sum() + away_matches["home_team_goal"].sum()
    
    saldo_gols = gols_marcados - gols_sofridos
    pontos = vitorias*3 + empates
    
    table.append({
        "Time": team,
        "PJ": partidas_jogadas,
        "V": vitorias,
        "E": empates,
        "D": derrotas,
        "GM": gols_marcados,
        "GS": gols_sofridos,
        "SG": saldo_gols,
        "Pts": pontos
    })

# Criar DataFrame e ordenar pelo padrão de campeonato
standings = pd.DataFrame(table)
standings = standings.sort_values(by=["Pts", "SG", "GM"], ascending=[False, False, False]).reset_index(drop=True)

# Mostrar tabela
st.subheader("📋 Tabela de Classificação")
st.table(standings)

# -------------------------------
# 🔹 Percentual de partidas por faixa de gols
# -------------------------------
faixas = [0.5, 1.5, 2.5, 3.5]
contagem = [(league_matches["total_gols"] > f).sum() for f in faixas]

df_barras = pd.DataFrame({
    "Faixa de Gols": [f">{f} gols" for f in faixas],
    "Percentual": [round((c / total_partidas) * 100, 1) for c in contagem]
})

st.subheader("📊 Percentual de Partidas por Faixa de Gols")
cols = st.columns(len(faixas))
for i, (f, qtd) in enumerate(zip(faixas, contagem)):
    percent = round((qtd / total_partidas) * 100, 1) if total_partidas > 0 else 0
    with cols[i]:
        st.metric(label=f">{f} gols", value=f"{percent}%")

fig_barras = px.bar(
    df_barras,
    x="Percentual",
    y="Faixa de Gols",
    orientation="h",
    text="Percentual",
    labels={"Percentual": "% de partidas", "Faixa de Gols": "Faixa de Gols"},
    title="Percentual de Partidas por Faixa de Gols"
)
fig_barras.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig_barras, use_container_width=True)

# -------------------------------
# 🔹 Gráficos inline
# -------------------------------
st.subheader("📈 Análises por Rodada")
col1, col2 = st.columns([1,1])

# 2️⃣ Resultados por rodada
with col1:
    fig_resultados = px.line(
        resultados_df,
        x="Rodada",
        y=["Vitórias Mandante", "Vitórias Visitante", "Empates"],
        title="Resultados por Rodada",
        labels={"value":"Quantidade", "Rodada":"Rodada", "variable":"Resultado"}
    )
    fig_resultados.update_yaxes(range=[0, None])
    st.plotly_chart(fig_resultados, use_container_width=True)

# 3️⃣ Média de gols por jogo
with col2:
    fig_media_gols = px.line(
        gols_por_rodada,
        x="stage",
        y="Média Gols por Jogo",
        title="Média de Gols por Jogo por Rodada",
        labels={"stage":"Rodada", "Média Gols por Jogo":"Gols"},
        range_y=[0, gols_por_rodada["Média Gols por Jogo"].max() * 1.1]
    )
    fig_media_gols.update_yaxes(range=[0, None])
    st.plotly_chart(fig_media_gols, use_container_width=True)
    
# Garantir que não haja NaN nos nomes
league_matches["team_home"] = league_matches["team_home"].fillna("Unknown")
league_matches["team_away"] = league_matches["team_away"].fillna("Unknown")

# Lista de times únicos
faixas = [0.5, 1.5, 2.5, 3.5]

# Lista de times
all_teams = pd.unique(league_matches[["team_home", "team_away"]].values.ravel("K"))

# Criar DataFrame de contagem por time e faixa
ranking = []

for team in all_teams:
    df_team = league_matches[(league_matches["team_home"] == team) | (league_matches["team_away"] == team)]
    total_partidas_time = len(df_team)
    if total_partidas_time == 0:
        continue
    for f in faixas:
        partidas_acima = (df_team["total_gols"] > f).sum()
        percent = (partidas_acima / total_partidas_time) * 100
        ranking.append({
            "Time": team,
            "Faixa de Gols": f">{f} gols",
            "Total Partidas Acima": partidas_acima,
            "Percentual": f"{percent:.2f}%"
        })

ranking_df = pd.DataFrame(ranking)

# Criar colunas inline para as 4 faixas
cols = st.columns(len(faixas))

for i, f in enumerate(faixas):
    faixa_str = f">{f} gols"
    top5 = ranking_df[ranking_df["Faixa de Gols"] == faixa_str].sort_values(
        by="Total Partidas Acima", ascending=False
    ).head(5)
    
    with cols[i]:
        st.markdown(f"**Top 5 clubes em partidas com {faixa_str}**")
        st.table(top5[["Time", "Total Partidas Acima", "Percentual"]].reset_index(drop=True))
