import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(layout="wide")
st.title("⚽ Análise de Jogadores")

# -------------------------------
# 🔹 Conexão com o banco SQLite
# -------------------------------
engine = create_engine("sqlite:///data/database.sqlite")

# Carregar tabelas
players = pd.read_sql("""
SELECT 
    player_api_id,
    player_name,
    birthday,
    height,
    weight
FROM Player
""", engine)

player_attributes = pd.read_sql("""
SELECT 
    player_api_id,
    date,
    overall_rating,
    potential,
    crossing, finishing, heading_accuracy, short_passing, volleys,
    dribbling, curve, free_kick_accuracy, long_passing, ball_control,
    acceleration, sprint_speed, agility, reactions, balance,
    shot_power, jumping, stamina, strength, long_shots,
    aggression, interceptions, positioning, vision, penalties, marking,
    standing_tackle, sliding_tackle, gk_diving, gk_handling, gk_kicking, gk_positioning, gk_reflexes
FROM Player_Attributes
""", engine)

# -------------------------------
# 🔹 Busca por nome do jogador
# -------------------------------
player_name = st.text_input("Digite o nome do jogador:")

if player_name:
    results = players[players["player_name"].str.contains(player_name, case=False, na=False)]
    
    if results.empty:
        st.warning("⚠️ Nenhum jogador encontrado com esse nome.")
    else:
        selected_player = st.selectbox("Selecione o jogador:", results["player_name"].unique())
        player_id = results[results["player_name"] == selected_player]["player_api_id"].values[0]

        player_data = player_attributes[player_attributes["player_api_id"] == player_id]
        if not player_data.empty:
            latest = player_data.sort_values("date", ascending=False).iloc[0]

            # Selecionar atributos principais
            atributos = {
                "Passe": latest["short_passing"],
                "Chute": latest["finishing"],
                "Drible": latest["dribbling"],
                "Defesa": latest["marking"],
                "Físico": latest["strength"],
                "Velocidade": latest["sprint_speed"]
            }

            # -------------------------------
            # 🔹 Exibir atributos e radar
            # -------------------------------
            st.subheader(f"📋 Atributos Técnicos de {selected_player}")
            st.write(pd.DataFrame(atributos.items(), columns=["Atributo", "Valor"]).set_index("Atributo"))

            radar_df = pd.DataFrame({
                "Atributo": list(atributos.keys()),
                "Valor": list(atributos.values())
            })

            fig_radar = px.line_polar(
                radar_df,
                r="Valor",
                theta="Atributo",
                line_close=True,
                title=f"🎯 Perfil Técnico de {selected_player}",
                range_r=[0, 100]
            )
            fig_radar.update_traces(fill="toself")
            st.plotly_chart(fig_radar, use_container_width=True)

            # -------------------------------
            # 🔹 Storytelling sobre o estilo de jogo
            # -------------------------------
            st.subheader("🧠 Interpretação e Utilidade em Campo")

            passe = atributos["Passe"]
            chute = atributos["Chute"]	
            drible = atributos["Drible"]
            defesa = atributos["Defesa"]
            fisico = atributos["Físico"]
            velocidade = atributos["Velocidade"]

            if chute > 80 and drible > 75:
                estilo = "um atacante habilidoso, com boa finalização e capacidade de criar jogadas individuais."
            elif passe > 75 and latest["vision"] > 70:
                estilo = "um meio-campista criativo, que dita o ritmo do jogo e encontra passes decisivos."
            elif defesa > 75 and fisico > 75:
                estilo = "um defensor sólido, com ótimo posicionamento e imposição física."
            elif velocidade > 80 and drible > 70:
                estilo = "um ponta veloz, que leva perigo constante pelas laterais."
            else:
                estilo = "um jogador versátil, que contribui em várias fases do jogo."

            st.markdown(f"**Análise Tática:** {selected_player} é {estilo}")
		
else:
    st.warning("⚠️ Nenhum atributo disponível para esse jogador.")
