import streamlit as st
import os
import requests

DB_PATH = "data/database.sqlite"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DB_URL = "https://drive.google.com/file/d/14koOa6FWE6PVaAIMTAJUy3IlWkZgFxJd/view?usp=sharing"

if not os.path.exists(DB_PATH):
    st.info("Baixando banco de dados...")
    r = requests.get(DB_URL)
    with open(DB_PATH, "wb") as f:
        f.write(r.content)
    st.success("Download concluído!")

st.set_page_config(
    page_title="Dashboard de Futebol",
    page_icon="⚽",
    layout="wide"
)

st.title("🏟️ Dashboard de Futebol")
st.write("""
Bem-vindo ao Dashboard de Futebol!  

Use o menu lateral para navegar entre as páginas disponíveis:
- Futebol Insights (estatísticas, gráficos e comparativos entre times)
- Outras páginas que você criar futuramente
""")