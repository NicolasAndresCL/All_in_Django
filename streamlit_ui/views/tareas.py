"""Vista de Registro de Tareas: dashboard (6 métricas + 6 gráficos), CRUD y filtro."""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import APIError, get_client


def _template() -> str:
    """Plantilla Plotly acorde al tema activo de Streamlit."""
    try:
        return "plotly_dark" if st.context.theme.base == "dark" else "plotly_white"
    except Exception:
        return "plotly_dark"


def construir_figuras(resumen: dict, template: str = "plotly_dark") -> dict:
    """
    Construye las 6 figuras Plotly del dashboard a partir del resumen de la API.

    Función pura (sin llamadas a Streamlit) → testeable. Devuelve un dict con las
    claves: jerarquia, esfuerzo, intensidad, semanal, dia_semana, acumulado. Las
    que dependen de datos que podrían faltar (jerarquia, intensidad, acumulado)
    valen None si no hay datos.
    """
    figs: dict = {}

    df_t = pd.DataFrame(resumen["por_tarea"])
    if not df_t.empty:
        fig = px.sunburst(df_t, path=["proyecto", "tarea"], values="horas",
                          color_discrete_sequence=px.colors.qualitative.Pastel, template=template)
        fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=350)
        figs["jerarquia"] = fig
    else:
        figs["jerarquia"] = None

    df_p = pd.DataFrame(resumen["por_proyecto"]).sort_values("horas")
    fig = px.bar(df_p, x="horas", y="proyecto", orientation="h",
                 color="horas", color_continuous_scale="Blues", template=template)
    fig.update_layout(height=350, showlegend=False)
    figs["esfuerzo"] = fig

    df_dia = pd.DataFrame(resumen["por_dia"])
    if not df_dia.empty:
        df_dia["fecha"] = pd.to_datetime(df_dia["fecha"])
        fig = px.area(df_dia, x="fecha", y="horas",
                      color_discrete_sequence=["#0e639c"], template=template)
        fig.update_layout(height=300)
        figs["intensidad"] = fig

        df_cum = df_dia.sort_values("fecha").copy()
        df_cum["acumuladas"] = df_cum["horas"].cumsum()
        fig = px.line(df_cum, x="fecha", y="acumuladas",
                      color_discrete_sequence=["#2ecc71"], template=template)
        fig.update_traces(fill="tozeroy", fillcolor="rgba(46,204,113,0.15)")
        fig.update_layout(height=300, yaxis_title="Horas acumuladas")
        figs["acumulado"] = fig
    else:
        figs["intensidad"] = figs["acumulado"] = None

    fig = px.bar(pd.DataFrame(resumen["por_semana"]), x="semana", y="horas",
                 color_discrete_sequence=["#0e639c"], template=template)
    fig.update_layout(height=300)
    figs["semanal"] = fig

    fig = px.bar(pd.DataFrame(resumen["por_dia_semana"]), x="dia", y="horas",
                 color="horas", color_continuous_scale="Teal", template=template)
    fig.update_layout(height=300, showlegend=False, xaxis_title=None)
    figs["dia_semana"] = fig

    return figs


def _grafico(col, titulo: str, fig) -> None:
    """Coloca una figura (o un aviso si es None) en `col` dentro de un contenedor."""
    with col, st.container(border=True):
        st.subheader(titulo)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Sin datos suficientes.")


def _dashboard(resumen: dict) -> None:
    """Renderiza las 6 métricas (incl. racha) y los 6 gráficos del resumen."""
    with st.container(border=True):
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Tareas Totales", resumen["tareas"])
        m2.metric("Proyectos Activos", resumen["proyectos"])
        m3.metric("Horas Acumuladas", f"{resumen['horas_total']:.1f} h")
        racha = resumen["racha_dias"]
        m4.metric("Racha Actual", f"{racha} días", delta="🔥 activa" if racha else None)
        m5.metric("Promedio Diario", f"{resumen['promedio_diario']:.1f} h")
        m6.metric("Promedio Semanal", f"{resumen['promedio_semanal']:.1f} h")

    st.divider()

    figs = construir_figuras(resumen, _template())
    fila1 = st.columns(2)
    _grafico(fila1[0], "Jerarquía Proyecto / Tarea", figs["jerarquia"])
    _grafico(fila1[1], "Esfuerzo por Proyecto", figs["esfuerzo"])
    fila2 = st.columns(2)
    _grafico(fila2[0], "Intensidad Diaria", figs["intensidad"])
    _grafico(fila2[1], "Productividad Semanal", figs["semanal"])
    fila3 = st.columns(2)
    _grafico(fila3[0], "Actividad por Día de la Semana", figs["dia_semana"])
    _grafico(fila3[1], "Progreso Acumulado", figs["acumulado"])


def render() -> None:
    """Vista de tareas: dashboard de resumen, listado con filtro, alta y borrado."""
    st.title("✅ Registro de Tareas")
    api = get_client()

    try:
        todas = api.list("tareas")
    except APIError as exc:
        st.error(f"No se pudieron cargar las tareas: {exc}")
        todas = []

    proyectos = sorted({t["proyecto"] for t in todas})

    # -- dashboard (acción /tareas/resumen/) -------------------------------
    st.subheader("Resumen")
    try:
        resumen = api.action("tareas", "resumen")
    except APIError as exc:
        st.warning(f"No se pudo cargar el resumen: {exc}")
        resumen = None

    if resumen and resumen.get("tareas"):
        _dashboard(resumen)
    elif resumen is not None:
        st.info("Aún no hay tareas registradas: agrega una para ver el dashboard.")

    st.divider()

    # -- listado con filtro ------------------------------------------------
    st.subheader("Registros")
    filtro = st.selectbox("Filtrar por proyecto", ["(todos)"] + proyectos, key="tk_filtro")
    registros = api.list("tareas", proyecto=None if filtro == "(todos)" else filtro)
    if registros:
        st.dataframe(pd.DataFrame(registros), width="stretch", hide_index=True)
    else:
        st.info("Sin registros para el filtro actual.")

    st.divider()

    # -- alta (con autocompletado desde lo ya registrado) ------------------
    st.subheader("Nueva tarea")
    st.caption("Elige un proyecto/tarea existente para reutilizarlo, o crea uno nuevo.")
    NUEVO_P, NUEVA_T = "➕ Nuevo proyecto...", "➕ Nueva tarea..."

    # Fuera de st.form: así al elegir proyecto se filtran sus tareas al instante.
    c1, c2 = st.columns(2)
    fecha = c1.date_input("Fecha", value=date.today(), key="tk_fecha")
    p_sel = c2.selectbox("Proyecto", proyectos + [NUEVO_P], key="tk_proy_sel")
    proyecto = (st.text_input("Nombre del proyecto", key="tk_proy_new")
                if p_sel == NUEVO_P else p_sel)

    # Tareas ya usadas en ese proyecto → referencia para no reescribirlas.
    tareas_prev = (sorted({t["tarea"] for t in todas if t["proyecto"] == p_sel})
                   if p_sel != NUEVO_P else [])
    t_sel = st.selectbox("Tarea", tareas_prev + [NUEVA_T], key="tk_tarea_sel")
    tarea = (st.text_input("Nombre de la tarea", key="tk_tarea_new")
             if t_sel == NUEVA_T else t_sel)

    c3, c4 = st.columns(2)
    horas = c3.number_input("Horas", min_value=0, max_value=23, value=1, key="tk_h")
    minutos = c4.number_input("Minutos", min_value=0, max_value=59, value=0, key="tk_m")
    if st.button("Crear tarea", type="primary", key="tk_crear"):
        if not str(proyecto).strip() or not str(tarea).strip():
            st.error("Completa proyecto y tarea.")
        elif horas == 0 and minutos == 0:
            st.error("La duración no puede ser 0.")
        else:
            try:
                api.create("tareas", {
                    "fecha": fecha.isoformat(),
                    "proyecto": proyecto,
                    "tarea": tarea,
                    # DurationField DRF acepta "HH:MM:SS".
                    "duracion": f"{int(horas):02d}:{int(minutos):02d}:00",
                })
                st.success("Tarea creada.")
                st.rerun()
            except APIError as exc:
                st.error(f"Error al crear: {exc.detalle or exc}")

    # -- borrar ------------------------------------------------------------
    if registros:
        with st.expander("Eliminar registro"):
            opciones = {
                f"#{r['id']} · {r['fecha']} · {r['proyecto']} · {r['tarea']}": r["id"]
                for r in registros
            }
            sel = st.selectbox("Registro", list(opciones), key="tk_del")
            if st.button("Eliminar", key="tk_btn_del"):
                try:
                    api.delete("tareas", opciones[sel])
                    st.success("Eliminado.")
                    st.rerun()
                except APIError as exc:
                    st.error(f"Error al eliminar: {exc}")
