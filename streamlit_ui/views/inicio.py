"""Vista de Inicio: estado de conexión y resumen de cada módulo."""

import streamlit as st

from api_client import APIError, get_client


def render() -> None:
    """Panel de inicio: verifica la conexión con la API y muestra conteos por módulo."""
    st.title("🏠 All in Django")
    st.caption("Panel visual sobre la API REST (Django + DRF).")

    api = get_client()

    if not api.ping():
        st.error(
            f"No se pudo conectar con la API en **{api.base}**.\n\n"
            "Levanta el backend con `python manage.py runserver` o ajusta la "
            "variable de entorno `API_BASE`."
        )
        st.stop()

    st.success(f"Conectado a la API en `{api.base}`")

    # Conteos rápidos por recurso (una llamada por módulo).
    recursos = {
        "Clases": "clases",
        "Turnos personales": "turnos-personales",
        "Turnos equipo": "turnos-equipo",
        "Tareas": "tareas",
        "Notas": "notas",
    }

    st.subheader("Resumen")
    cols = st.columns(len(recursos))
    for col, (label, recurso) in zip(cols, recursos.items()):
        try:
            total = len(api.list(recurso))
            col.metric(label, total)
        except APIError as exc:
            col.metric(label, "—")
            col.caption(f"error: {exc.status}")

    st.divider()
    st.markdown(
        """
        **Módulos disponibles** (menú lateral):

        - 📅 **Calendario** — clases de estudio y turnos personales.
        - 👥 **LiveOps Equipo** — turnos del equipo + importación CSV/Excel.
        - ✅ **Registro de Tareas** — actividades por proyecto + dashboard.
        - 📝 **Notas** — notas Markdown/texto con exportación.
        - 📺 **TV Chile** — grilla de canales (solo lectura).
        """
    )
