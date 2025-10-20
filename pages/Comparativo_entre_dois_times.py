import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.title("⚽ Comparativo entre clubes")

# Conexão com SQLite
engine = create_engine("sqlite:///data/database.sqlite")

# Carregar tabelas básicas
teams = pd.read_sql("SELECT team_api_id, team_long_name FROM Team", engine)
leagues = pd.read_sql("SELECT id AS league_id, name AS league_name FROM League", engine)

# Query principal de partidas
query = """
SELECT 
    M.match_api_id,
    M.league_id,
    L.name AS league_name,
    M.season,
    M.home_team_api_id,
    M.away_team_api_id,
    M.home_team_goal,
    M.away_team_goal
FROM Match M
JOIN League L ON M.league_id = L.id
"""
matches = pd.read_sql(query, engine)

# Juntar nomes dos times (home e away)
matches = matches.merge(
    teams, left_on="home_team_api_id", right_on="team_api_id", how="left"
).rename(columns={"team_long_name": "team_home"})
matches = matches.merge(
    teams, left_on="away_team_api_id", right_on="team_api_id", how="left"
).rename(columns={"team_long_name": "team_away"})

matches = matches[
    [
        "match_api_id",
        "league_id",
        "league_name",
        "season",
        "team_home",
        "team_away",
        "home_team_goal",
        "away_team_goal",
    ]
]




selected_league = st.selectbox(
    "Selecione a Liga", leagues["league_name"].sort_values()
)

# Filtrar apenas a liga escolhida
league_matches = matches[matches["league_name"] == selected_league]

# Filtro de período (temporadas)
seasons = sorted(league_matches["season"].unique())
selected_seasons = st.multiselect(
    "Selecione a(s) Temporada(s)",
    seasons,
    default=seasons[-1:]  # última temporada como padrão
)

league_matches = league_matches[league_matches["season"].isin(selected_seasons)]

# Lista de times da liga
all_teams = pd.unique(league_matches[["team_home", "team_away"]].values.ravel("K"))
team1 = st.selectbox("Time 1", sorted(all_teams))
team2 = st.selectbox("Time 2", sorted(all_teams))

# -------------------------------
# 🔹 Função de estatísticas
# -------------------------------
def stats(df, team_name):
    df_team = df[
        (df["team_home"] == team_name) | (df["team_away"] == team_name)
    ]

    gols_marcados = df_team.apply(
        lambda row: row["home_team_goal"] if row["team_home"] == team_name else row["away_team_goal"],
        axis=1,
    ).sum()

    gols_sofridos = df_team.apply(
        lambda row: row["away_team_goal"] if row["team_home"] == team_name else row["home_team_goal"],
        axis=1,
    ).sum()

    partidas = len(df_team)

    # Vitórias, empates, derrotas
    vitorias = df_team.apply(
        lambda row: 1 if 
        ((row["team_home"] == team_name and row["home_team_goal"] > row["away_team_goal"]) or
         (row["team_away"] == team_name and row["away_team_goal"] > row["home_team_goal"])) else 0,
        axis=1
    ).sum()

    empates = df_team.apply(
        lambda row: 1 if row["home_team_goal"] == row["away_team_goal"] else 0,
        axis=1
    ).sum()

    derrotas = partidas - vitorias - empates

    return {
        "Partidas": partidas,
        "Gols Marcados": gols_marcados,
        "Gols Sofridos": gols_sofridos,
        "Vitórias": vitorias,
        "Empates": empates,
        "Derrotas": derrotas
    }

# -------------------------------
# 🔹 Calculando estatísticas
# -------------------------------
stats_team1 = stats(league_matches, team1)
stats_team2 = stats(league_matches, team2)

# -------------------------------
# 🔹 Criando tabela comparativa
# -------------------------------
df_stats = pd.DataFrame([stats_team1, stats_team2], index=[team1, team2])
st.subheader(f"📊 Estatísticas — {selected_league}")
st.write(f"🗓️ Temporadas: {', '.join(selected_seasons)}")
st.dataframe(df_stats)  # tabela interativa

# -------------------------------
# 🔹 Gráfico comparativo
# -------------------------------
df_plot = pd.DataFrame({
    "Time": [team1, team2],
    "Gols Marcados": [stats_team1["Gols Marcados"], stats_team2["Gols Marcados"]],
    "Gols Sofridos": [stats_team1["Gols Sofridos"], stats_team2["Gols Sofridos"]],
    "Vitórias": [stats_team1["Vitórias"], stats_team2["Vitórias"]],
    "Empates": [stats_team1["Empates"], stats_team2["Empates"]],
    "Derrotas": [stats_team1["Derrotas"], stats_team2["Derrotas"]],
})

fig = px.bar(
    df_plot,
    x="Time",
    y=["Gols Marcados", "Gols Sofridos", "Vitórias", "Derrotas", "Empates"],
    barmode="group",
    title="Comparação entre Times",
    labels={"variable": "Análise", "value": "Quantidade"}
)

st.plotly_chart(fig)

st.subheader("📖 Comparação entre os times")

story = f"""
No período selecionado ({', '.join(selected_seasons)}), na liga **{selected_league}**:

- O time que marcou mais gols foi **{team1 if stats_team1['Gols Marcados'] > stats_team2['Gols Marcados'] else team2}**.
- O time com mais vitórias foi **{team1 if stats_team1['Vitórias'] > stats_team2['Vitórias'] else team2}**.
- O time com menos derrotas foi **{team1 if stats_team1['Derrotas'] < stats_team2['Derrotas'] else team2}**.
"""

st.markdown(story)

st.subheader("📊 Comparativo de porcentagens")

# Função para calcular porcentagem
def calc_percent(valor, total):
    return round((valor / total) * 100, 1) if total > 0 else 0

# Criar um DataFrame com porcentagens
df_percent = pd.DataFrame({
    "Categoria": ["Vitórias", "Empates", "Derrotas"],
    team1: [
        calc_percent(stats_team1["Vitórias"], stats_team1["Partidas"]),
        calc_percent(stats_team1["Empates"], stats_team1["Partidas"]),
        calc_percent(stats_team1["Derrotas"], stats_team1["Partidas"])
    ],
    team2: [
        calc_percent(stats_team2["Vitórias"], stats_team2["Partidas"]),
        calc_percent(stats_team2["Empates"], stats_team2["Partidas"]),
        calc_percent(stats_team2["Derrotas"], stats_team2["Partidas"])
    ]
})

# Exibir os cards lado a lado
for categoria in df_percent["Categoria"]:
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label=f"{team1} - {categoria}",
            value=f"{df_percent.loc[df_percent['Categoria'] == categoria, team1].values[0]}%"
        )
    with col2:
        st.metric(
            label=f"{team2} - {categoria}",
            value=f"{df_percent.loc[df_percent['Categoria'] == categoria, team2].values[0]}%"
        )
        
st.subheader("📖 Comparação entre os times (Percentuais)")

# Função para calcular aumento percentual relativo
def percentual_relativo(valor1, valor2, menos_eh_melhor=False):
    """
    Calcula a diferença percentual entre valor1 e valor2.
    Retorna uma string do tipo 'X% mais' ou 'X% menos' de forma automática.
    
    Se menos_eh_melhor=True, então menor valor é considerado melhor.
    """
    if valor1 == valor2:
        return "igual"
    
    if menos_eh_melhor:
        # Menor é melhor: inverte a lógica do "mais/menos"
        if valor1 < valor2:
            diff = ((valor2 - valor1) / valor2) * 100
            return f"{round(diff,1)}% menos"
        else:
            diff = ((valor1 - valor2) / valor1) * 100
            return f"{round(diff,1)}% menos"
    else:
        # Maior é melhor
        if valor1 > valor2:
            diff = ((valor1 - valor2) / valor2) * 100
            return f"{round(diff,1)}% mais"
        else:
            diff = ((valor2 - valor1) / valor1) * 100
            return f"{round(diff,1)}% mais"
        
def time_oposto(time_atual):
    return team2 if time_atual == team1 else team1

# Função para determinar qual time se destaca
def comparativo(valor1, valor2, nome_time1, nome_time2, menos_eh_melhor=False):
    if valor1 == valor2:
        return "igual", f"igual ao {time_oposto(nome_time1)}"
    if menos_eh_melhor:
        if valor1 < valor2:
            return nome_time1, percentual_relativo(valor1, valor2, menos_eh_melhor=True)
        else:
            return nome_time2, percentual_relativo(valor2, valor1, menos_eh_melhor=True)
    else:
        if valor1 > valor2:
            return nome_time1, percentual_relativo(valor1, valor2)
        else:
            return nome_time2, percentual_relativo(valor2, valor1)

# Comparativos
time_gols_marcados, gols_marcados_comp = comparativo(
    stats_team1['Gols Marcados'], stats_team2['Gols Marcados'], team1, team2
)
time_gols_sofridos, gols_sofridos_comp = comparativo(
    stats_team1['Gols Sofridos'], stats_team2['Gols Sofridos'], team1, team2, menos_eh_melhor=True
)
time_vitorias, vitorias_comp = comparativo(
    stats_team1['Vitórias'], stats_team2['Vitórias'], team1, team2
)
time_empates, empates_comp = comparativo(
    stats_team1['Empates'], stats_team2['Empates'], team1, team2
)
time_derrotas, derrotas_comp = comparativo(
    stats_team1['Derrotas'], stats_team2['Derrotas'], team1, team2, menos_eh_melhor=True
)



story_percent = f"""
No período selecionado ({', '.join(selected_seasons)}), na liga **{selected_league}**:

- **{team1}** jogou {stats_team1['Partidas']} partidas, marcando {stats_team1['Gols Marcados']} gols e sofrendo {stats_team1['Gols Sofridos']} gols. 
  Eles tiveram {stats_team1['Vitórias']} vitórias, {stats_team1['Empates']} empates e {stats_team1['Derrotas']} derrotas.

- **{team2}** jogou {stats_team2['Partidas']} partidas, marcando {stats_team2['Gols Marcados']} gols e sofrendo {stats_team2['Gols Sofridos']} gols. 
  Eles tiveram {stats_team2['Vitórias']} vitórias, {stats_team2['Empates']} empates e {stats_team2['Derrotas']} derrotas.

Comparando os números percentualmente:

- **Gols marcados:** {time_gols_marcados} ({gols_marcados_comp}).  
- **Gols sofridos:** {time_gols_sofridos} ({gols_sofridos_comp}).  
- **Vitórias:** {time_vitorias} ({vitorias_comp}).  
- **Empates:** {time_empates} ({empates_comp}).  
- **Derrotas:** {time_derrotas} ({derrotas_comp}).
"""

st.markdown(story_percent)

