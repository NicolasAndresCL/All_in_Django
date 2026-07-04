"""Vista de Calendario: clases y turnos personales (CRUD, copiar semana, PDF, Gantt)."""

from datetime import date, time, timedelta

import pandas as pd
import streamlit as st

from api_client import APIError, get_client
from gantt import generar_gantt

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _lunes(d: date) -> date:
    """Lunes de la semana de `d` (para el default de semana_inicio)."""
    return d - timedelta(days=d.weekday())


def _semanas(items: list[dict]) -> list[str]:
    """Semanas distintas presentes en `items`, más recientes primero."""
    return sorted({i["semana_inicio"] for i in items}, reverse=True)


def _copiar_ui(api, recurso: str, semanas: list[str], key: str) -> None:
    """Expander para crear una semana basándose en otra ya registrada."""
    with st.expander("📋 Copiar / basar en otra semana"):
        if not semanas:
            st.info("Aún no hay otras semanas para copiar.")
            return
        origen = st.selectbox("Semana origen", semanas, key=f"cp_o_{key}")
        destino = st.date_input("Semana destino (lunes)", value=_lunes(date.today()), key=f"cp_d_{key}")
        st.caption("⚠️ Reemplaza lo que haya en la semana destino.")
        if st.button("📥 Copiar", key=f"cp_b_{key}"):
            try:
                res = api.post_action(recurso, "copiar_semana",
                                      {"origen": origen, "destino": destino.isoformat()})
                st.success(f"{res['copiadas']} registros copiados a {res['destino']}.")
                st.rerun()
            except APIError as exc:
                st.error(f"Error al copiar: {exc.detalle or exc}")


def _pdf_ui(api, label: str, path: str, semana: str, filename: str, key: str) -> None:
    """Botón que genera un PDF (descarga desde la API) y ofrece guardarlo."""
    if st.button(label, key=key):
        try:
            data, _ = api.download(path, semana_inicio=semana)
            st.download_button("⬇️ Descargar", data, filename, "application/pdf", key=f"dl_{key}")
        except APIError as exc:
            st.error(f"Error al generar el PDF: {exc}")


def render() -> None:
    """Vista de calendario: pestañas de clases, turnos personales e impresión/Gantt."""
    st.title("📅 Calendario")
    api = get_client()

    try:
        clases = api.list("clases")
        turnos = api.list("turnos-personales")
    except APIError as exc:
        st.error(f"No se pudieron cargar los datos: {exc}")
        clases, turnos = [], []

    tab_clases, tab_turnos, tab_impr = st.tabs(
        ["Clases", "Turnos personales", "Impresión y Gantt"]
    )

    # ------------------------------------------------------------------ Clases
    with tab_clases:
        st.subheader("Clases (Santo Tomás)")
        if clases:
            st.dataframe(pd.DataFrame(clases), width="stretch", hide_index=True)
        else:
            st.info("Sin clases registradas.")

        _copiar_ui(api, "clases", _semanas(clases), key="clase")

        with st.form("nueva_clase", clear_on_submit=True):
            st.markdown("**Nueva clase**")
            c1, c2, c3 = st.columns(3)
            semana = c1.date_input("Semana (lunes)", value=_lunes(date.today()), key="cl_sem")
            dia = c2.selectbox("Día", DIAS, key="cl_dia")
            asignatura = c3.text_input("Asignatura", key="cl_asig")
            c4, c5 = st.columns(2)
            entrada = c4.time_input("Entrada", value=time(8, 0), key="cl_in")
            salida = c5.time_input("Salida", value=time(10, 0), key="cl_out")
            if st.form_submit_button("Crear clase", type="primary"):
                try:
                    api.create("clases", {
                        "semana_inicio": semana.isoformat(), "dia": dia, "asignatura": asignatura,
                        "entrada": entrada.strftime("%H:%M:%S"), "salida": salida.strftime("%H:%M:%S"),
                    })
                    st.success("Clase creada.")
                    st.rerun()
                except APIError as exc:
                    st.error(f"Error al crear: {exc.detalle or exc}")

        _bloque_borrar(api, "clases", clases, etiqueta=_etq_clase)

    # -------------------------------------------------------- Turnos personales
    with tab_turnos:
        st.subheader("Turnos personales (PedidosYa)")
        if turnos:
            st.dataframe(pd.DataFrame(turnos), width="stretch", hide_index=True)
            m1, m2 = st.columns(2)
            m1.metric("Horas netas", round(sum(t.get("neto", 0) for t in turnos), 2))
            m2.metric("Horas extra", round(sum(t.get("extra", 0) for t in turnos), 2))
        else:
            st.info("Sin turnos registrados.")

        _copiar_ui(api, "turnos-personales", _semanas(turnos), key="turno")

        with st.form("nuevo_turno", clear_on_submit=True):
            st.markdown("**Nuevo turno**")
            c1, c2 = st.columns(2)
            semana = c1.date_input("Semana (lunes)", value=_lunes(date.today()), key="tp_sem")
            dia = c2.selectbox("Día", DIAS, key="tp_dia")
            es_libre = st.checkbox("Día libre", key="tp_libre")
            c3, c4 = st.columns(2)
            entrada = c3.time_input("Entrada", value=time(18, 0), disabled=es_libre, key="tp_in")
            salida = c4.time_input("Salida", value=time(23, 0), disabled=es_libre, key="tp_out")
            if st.form_submit_button("Crear turno", type="primary"):
                payload = {"semana_inicio": semana.isoformat(), "dia": dia, "es_libre": es_libre}
                if not es_libre:
                    payload["entrada"] = entrada.strftime("%H:%M:%S")
                    payload["salida"] = salida.strftime("%H:%M:%S")
                try:
                    api.create("turnos-personales", payload)
                    st.success("Turno creado.")
                    st.rerun()
                except APIError as exc:
                    st.error(f"Error al crear: {exc.detalle or exc}")

        _bloque_borrar(api, "turnos-personales", turnos, etiqueta=_etq_turno)

    # ------------------------------------------------------- Impresión y Gantt
    with tab_impr:
        st.subheader("Impresión y visualización")
        semanas = sorted(set(_semanas(clases)) | set(_semanas(turnos)), reverse=True)
        if not semanas:
            st.info("Registra clases o turnos para imprimir o graficar.")
        else:
            sem = st.selectbox("Semana", semanas, key="impr_sem")
            cls_sem = [c for c in clases if c["semana_inicio"] == sem]
            tur_sem = [t for t in turnos if t["semana_inicio"] == sem]

            m1, m2, m3 = st.columns(3)
            h_est = round(sum(c.get("horas", 0) for c in cls_sem), 1)
            h_lab = round(sum(t.get("neto", 0) for t in tur_sem), 1)
            m1.metric("Carga académica", f"{h_est} h")
            m2.metric("Carga laboral (neto)", f"{h_lab} h")
            m3.metric("Ocupación total", f"{round(h_est + h_lab, 1)} h")

            st.plotly_chart(generar_gantt(cls_sem, tur_sem, sem), width="stretch")

            st.markdown("**Descargar PDF**")
            c1, c2, c3 = st.columns(3)
            with c1:
                _pdf_ui(api, "📄 Estudio", "clases/imprimir/", sem, f"Estudio_{sem}.pdf", "pdf_est")
            with c2:
                _pdf_ui(api, "📄 Laboral", "turnos-personales/imprimir/", sem, f"PeYa_{sem}.pdf", "pdf_lab")
            with c3:
                _pdf_ui(api, "📄 Maestro", "clases/imprimir_maestro/", sem, f"Master_{sem}.pdf", "pdf_mae")


# -- helpers de UI reutilizables ------------------------------------------------
def _etq_clase(c: dict) -> str:
    return f"#{c['id']} · {c['semana_inicio']} · {c['dia']} · {c['asignatura']}"


def _etq_turno(t: dict) -> str:
    estado = "LIBRE" if t.get("es_libre") else f"{t.get('entrada')}–{t.get('salida')}"
    return f"#{t['id']} · {t['semana_inicio']} · {t['dia']} · {estado}"


def _bloque_borrar(api, recurso: str, items: list[dict], etiqueta) -> None:
    """Selector + botón para eliminar un registro del recurso."""
    if not items:
        return
    with st.expander("Eliminar registro"):
        opciones = {etiqueta(i): i["id"] for i in items}
        sel = st.selectbox("Registro", list(opciones), key=f"del_{recurso}")
        if st.button("Eliminar", key=f"btn_del_{recurso}"):
            try:
                api.delete(recurso, opciones[sel])
                st.success("Eliminado.")
                st.rerun()
            except APIError as exc:
                st.error(f"Error al eliminar: {exc}")
