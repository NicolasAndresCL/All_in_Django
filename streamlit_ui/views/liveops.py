"""Vista de LiveOps: turnos del equipo, importación CSV/Excel y exportación."""

from datetime import date, time, timedelta

import pandas as pd
import streamlit as st

from api_client import APIError, get_client
from gantt import generar_gantt_equipo

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def render() -> None:
    """Vista de LiveOps: filtros, listado, alta manual, importación y exportación."""
    st.title("👥 LiveOps Equipo")
    api = get_client()

    # -- filtros -----------------------------------------------------------
    with st.container(border=True):
        f1, f2 = st.columns(2)
        usar_semana = f1.checkbox("Filtrar por semana", key="lo_fs")
        semana = f1.date_input(
            "Semana (lunes)", value=_lunes(date.today()), disabled=not usar_semana, key="lo_sem"
        )
        trabajador = f2.selectbox("Trabajador", ["(todos)"] + TRABAJADORES, key="lo_trab")

    params = {}
    if usar_semana:
        params["semana_inicio"] = semana.isoformat()
    if trabajador != "(todos)":
        params["trabajador"] = trabajador

    try:
        turnos = api.list("turnos-equipo", **params)
    except APIError as exc:
        st.error(f"No se pudieron cargar los turnos: {exc}")
        turnos = []

    if turnos:
        st.dataframe(pd.DataFrame(turnos), width="stretch", hide_index=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Turnos", len(turnos))
        m2.metric("Horas netas", round(sum(t.get("neto", 0) for t in turnos), 2))
        m3.metric("Horas extra", round(sum(t.get("extra", 0) for t in turnos), 2))
        st.plotly_chart(generar_gantt_equipo(turnos), width="stretch")
    else:
        st.info("Sin turnos para los filtros actuales.")

    st.divider()
    col_form, col_io = st.columns(2)

    # -- alta manual -------------------------------------------------------
    with col_form:
        st.subheader("Nuevo turno")
        with st.form("nuevo_turno_eq", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_semana = c1.date_input("Semana (lunes)", value=_lunes(date.today()), key="lo_fsem")
            f_trab = c2.selectbox("Trabajador", TRABAJADORES, key="lo_ftrab")
            f_dia = st.selectbox("Día", DIAS, key="lo_fdia")
            es_libre = st.checkbox("Día libre", key="lo_flibre")
            c3, c4 = st.columns(2)
            entrada = c3.time_input("Entrada", value=time(9, 0), disabled=es_libre, key="lo_fin")
            salida = c4.time_input("Salida", value=time(18, 0), disabled=es_libre, key="lo_fout")
            if st.form_submit_button("Crear turno", type="primary"):
                payload = {
                    "semana_inicio": f_semana.isoformat(),
                    "trabajador": f_trab,
                    "dia": f_dia,
                    "es_libre": es_libre,
                }
                if not es_libre:
                    payload["entrada"] = entrada.strftime("%H:%M:%S")
                    payload["salida"] = salida.strftime("%H:%M:%S")
                try:
                    api.create("turnos-equipo", payload)
                    st.success("Turno creado.")
                    st.rerun()
                except APIError as exc:
                    st.error(f"Error al crear: {exc.detalle or exc}")

    # -- importar / exportar ----------------------------------------------
    with col_io:
        st.subheader("Importar / Exportar")
        archivo = st.file_uploader(
            "Importar turnos (CSV o Excel con Fecha, Agente, Entrada, Salida)",
            type=["csv", "xlsx", "xls"],
            key="lo_upl",
        )
        if archivo is not None and st.button("Importar archivo", type="primary"):
            try:
                res = api.upload("turnos-equipo", "importar", archivo)
                st.success(f"Importadas {res.get('importadas', 0)} filas.")
                if res.get("errores"):
                    st.warning("Errores:\n" + "\n".join(f"- {e}" for e in res["errores"]))
                st.rerun()
            except APIError as exc:
                st.error(f"Error al importar: {exc.detalle or exc}")

        st.markdown("**Exportar / imprimir** (respeta los filtros de arriba)")
        e1, e2, e3 = st.columns(3)
        _boton_exportar(api, e1, "excel", params)
        _boton_exportar(api, e2, "pdf", params)
        with e3:
            if st.button("PDF con formato", key="lo_pdf_fmt"):
                try:
                    data, _ = api.download("turnos-equipo/imprimir/", **params)
                    st.download_button("⬇️ Descargar", data, "Horario_equipo.pdf",
                                       "application/pdf", key="lo_dl_fmt")
                except APIError as exc:
                    st.error(f"Error: {exc}")


def _boton_exportar(api, col, formato: str, params: dict) -> None:
    ext = "xlsx" if formato == "excel" else "pdf"
    if col.button(formato.upper(), key=f"exp_{formato}"):
        try:
            contenido, mime = api.download(
                "turnos-equipo/exportar/", formato=formato, **params
            )
            col.download_button(
                f"Descargar {ext}",
                data=contenido,
                file_name=f"turnos_equipo.{ext}",
                mime=mime,
                key=f"dl_{formato}",
            )
        except APIError as exc:
            col.error(f"Error: {exc}")
