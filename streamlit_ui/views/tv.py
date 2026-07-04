"""Vista de TV Chile: grilla de canales (solo lectura, endpoint cacheado)."""

import streamlit as st

from api_client import APIError, get_client


def render() -> None:
    """Vista de TV: buscador y grilla de canales (logo + enlace), solo lectura."""
    st.title("📺 TV Chile")
    st.caption("Grilla de canales de TV chilena (datos cacheados 1h en el backend).")
    api = get_client()

    buscar = st.text_input("Buscar canal", key="tv_buscar")

    try:
        data = api.tv_canales(buscar or None)
    except APIError as exc:
        st.error(f"No se pudieron obtener los canales: {exc.detalle or exc}")
        return

    canales = data.get("canales", [])
    st.write(f"**{data.get('total', len(canales))}** canales")

    if not canales:
        st.info("No hay canales para la búsqueda.")
        return

    # Grilla de 4 columnas con logo, nombre y enlace.
    columnas = st.columns(4)
    for i, canal in enumerate(canales):
        with columnas[i % 4]:
            with st.container(border=True):
                if canal.get("logo"):
                    st.image(canal["logo"], width="stretch")
                st.markdown(f"**{canal['name']}**")
                if canal.get("url"):
                    st.link_button("Ver", canal["url"], width="stretch")
