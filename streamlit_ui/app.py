"""
app.py — Interfaz Streamlit para All in Django.

Cliente visual de la API REST (DRF). Un único `st.set_page_config` aquí; la
navegación se arma con `st.navigation` y cada módulo vive en `views/`.

Uso recomendado (un solo comando, levanta API + UI en orden):
    python streamlit_ui/run_ui.py

`run_ui.py` arranca la API Django si no está viva, espera a que responda y luego abre
esta UI en el puerto 8501 (o el siguiente libre). Si prefieres ejecutar solo esta app
(`streamlit run app.py`), asegúrate de tener el backend corriendo aparte. La URL de la
API se configura con API_BASE (por defecto http://localhost:8000/api).
"""

import streamlit as st

st.set_page_config(
    page_title="All in Django · UI",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from views import calendario, inicio, liveops, notas, tareas, tv  # noqa: E402

# `url_path` explícito y único por página: como todas las vistas exponen una
# función `render`, Streamlit infería el mismo pathname y lanzaba
# StreamlitAPIException ("URL pathnames must be unique").
PAGINAS = [
    st.Page(inicio.render, title="Inicio", icon="🏠", url_path="inicio", default=True),
    st.Page(calendario.render, title="Calendario", icon="📅", url_path="calendario"),
    st.Page(liveops.render, title="LiveOps Equipo", icon="👥", url_path="liveops"),
    st.Page(tareas.render, title="Registro de Tareas", icon="✅", url_path="tareas"),
    st.Page(notas.render, title="Notas", icon="📝", url_path="notas"),
    st.Page(tv.render, title="TV Chile", icon="📺", url_path="tv"),
]

st.sidebar.title("🗂️ All in Django")
st.sidebar.caption("Cliente Streamlit de la API REST")

st.navigation(PAGINAS).run()
