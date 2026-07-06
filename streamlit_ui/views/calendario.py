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


def _hhmmss(valor: str) -> time:
    """'HH:MM[:SS]' → time (para precargar los time_input de la grilla)."""
    hh, mm, *_ = str(valor).split(":")
    return time(int(hh), int(mm))


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


def _sembrar_grilla(dias_fuente: dict, marcar_libre_si_falta: bool) -> None:
    """Precarga los widgets de la grilla (session_state) desde `dias_fuente` (por día).

    `dias_fuente`: {dia: turno_dict}. Para días sin dato: si `marcar_libre_si_falta`
    (al cargar otra semana) se dejan libres; si no (semana en edición) se ponen con el
    horario por defecto para facilitar el alta. Debe llamarse ANTES de crear los widgets.
    """
    for d in DIAS:
        t = dias_fuente.get(d)
        libre = bool(t["es_libre"]) if t else marcar_libre_si_falta
        st.session_state[f"tp_libre_{d}"] = libre
        st.session_state[f"tp_in_{d}"] = (
            _hhmmss(t["entrada"]) if (t and not libre and t.get("entrada")) else time(18, 0)
        )
        st.session_state[f"tp_out_{d}"] = (
            _hhmmss(t["salida"]) if (t and not libre and t.get("salida")) else time(23, 0)
        )


def _tab_turnos(api, turnos: list[dict]) -> None:
    """Turnos personales estilo all_in_one: grilla semanal editable (upsert por día).

    Se elige la semana a editar; la grilla precarga los turnos existentes de esa semana.
    'Cargar desde otra semana' trae los horarios de otra semana AL formulario (editables
    antes de guardar). 'Guardar semana' hace upsert de cada día (reescribir un día lo
    reemplaza, no falla). La tabla resumen va debajo del formulario.
    """
    st.subheader("Turnos personales (PedidosYa)")
    sem_iso = _lunes(
        st.date_input("Semana a editar (lunes)", value=_lunes(date.today()), key="tp_sem")
    ).isoformat()
    por_dia = {t["dia"]: t for t in turnos if t["semana_inicio"] == sem_iso}

    # Precarga de la grilla: al cambiar de semana (desde la existente) o al pulsar
    # 'Cargar' (desde otra semana). Se hace ANTES de instanciar los widgets.
    origen = st.session_state.pop("tp_cargar_origen", None)
    if origen is not None:
        fuente = {t["dia"]: t for t in turnos if t["semana_inicio"] == origen}
        _sembrar_grilla(fuente, marcar_libre_si_falta=True)
        st.session_state["tp_grid_week"] = sem_iso
    elif st.session_state.get("tp_grid_week") != sem_iso:
        _sembrar_grilla(por_dia, marcar_libre_si_falta=False)
        st.session_state["tp_grid_week"] = sem_iso

    with st.expander("📋 Cargar desde otra semana (para editar antes de guardar)"):
        otras = [s for s in _semanas(turnos) if s != sem_iso]
        if otras:
            sel = st.selectbox("Semana origen", otras, key="tp_carga_sel")
            st.caption("Trae esos horarios al formulario; edítalos y luego pulsa Guardar.")
            if st.button("📥 Cargar al formulario", key="tp_carga_btn"):
                st.session_state["tp_cargar_origen"] = sel
                st.rerun()
        else:
            st.info("No hay otras semanas para cargar.")

    st.markdown("**Configura la semana** — marca *Libre* o define entrada/salida por día:")
    cols = st.columns(7)
    for col, d in zip(cols, DIAS):
        with col:
            st.markdown(f"**{d[:3]}**")
            libre = st.checkbox("Libre", key=f"tp_libre_{d}")
            st.time_input("Entrada", key=f"tp_in_{d}", disabled=libre, label_visibility="collapsed")
            st.time_input("Salida", key=f"tp_out_{d}", disabled=libre, label_visibility="collapsed")

    if st.button("💾 Guardar semana", type="primary", key="tp_guardar"):
        errores = []
        for d in DIAS:
            libre = st.session_state[f"tp_libre_{d}"]
            payload = {"semana_inicio": sem_iso, "dia": d, "es_libre": libre}
            if not libre:
                payload["entrada"] = st.session_state[f"tp_in_{d}"].strftime("%H:%M:%S")
                payload["salida"] = st.session_state[f"tp_out_{d}"].strftime("%H:%M:%S")
            try:
                api.create("turnos-personales", payload)  # upsert por (semana, día)
            except APIError as exc:
                errores.append(f"{d}: {exc.detalle or exc}")
        if errores:
            st.error("No se pudieron guardar algunos días:\n" + "\n".join(f"- {e}" for e in errores))
        else:
            st.success(f"Semana {sem_iso} guardada.")
            st.rerun()

    # Resumen de la semana (debajo del formulario).
    st.divider()
    if por_dia:
        st.dataframe(pd.DataFrame(por_dia.values()), width="stretch", hide_index=True)
        m1, m2 = st.columns(2)
        m1.metric("Horas netas", round(sum(t.get("neto", 0) for t in por_dia.values()), 2))
        m2.metric("Horas extra", round(sum(t.get("extra", 0) for t in por_dia.values()), 2))
    else:
        st.info("Sin turnos guardados en esta semana. Configúralos arriba y guarda.")


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
        _tab_turnos(api, turnos)

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
