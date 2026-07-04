"""Vista de Notas: crear, editar, previsualizar y exportar (md/txt)."""

import streamlit as st

from api_client import APIError, get_client

FORMATOS = {"md": "Markdown", "txt": "Texto plano"}


def render() -> None:
    """Vista de notas: lista, editor (crear/editar/eliminar), exportación y preview."""
    st.title("📝 Notas")
    api = get_client()

    try:
        notas = api.list("notas")
    except APIError as exc:
        st.error(f"No se pudieron cargar las notas: {exc}")
        notas = []

    col_lista, col_editor = st.columns([1, 2])

    # -- lista / selección -------------------------------------------------
    with col_lista:
        st.subheader("Tus notas")
        if st.button("➕ Nueva nota", width="stretch"):
            st.session_state["nota_sel"] = None
        opciones = {"— Nueva —": None}
        opciones.update({f"#{n['id']} · {n['titulo'] or 'sin título'}": n["id"] for n in notas})
        etiqueta = st.radio("Seleccionar", list(opciones), key="nota_radio")
        sel_id = opciones[etiqueta]

    nota = next((n for n in notas if n["id"] == sel_id), None)

    # -- editor ------------------------------------------------------------
    with col_editor:
        st.subheader("Editar" if nota else "Crear nota")
        titulo = st.text_input("Título", value=(nota or {}).get("titulo", ""), key="nt_tit")
        formato = st.selectbox(
            "Formato",
            list(FORMATOS),
            index=list(FORMATOS).index((nota or {}).get("formato", "md")),
            format_func=lambda f: FORMATOS[f],
            key="nt_fmt",
        )
        contenido = st.text_area(
            "Contenido", value=(nota or {}).get("contenido", ""), height=260, key="nt_cont"
        )

        c1, c2, c3 = st.columns(3)
        if c1.button("💾 Guardar", type="primary"):
            payload = {"titulo": titulo, "contenido": contenido, "formato": formato}
            try:
                if nota:
                    api.update("notas", nota["id"], payload)
                else:
                    api.create("notas", payload)
                st.success("Nota guardada.")
                st.rerun()
            except APIError as exc:
                st.error(f"Error al guardar: {exc.detalle or exc}")

        if nota and c2.button("🗑️ Eliminar"):
            try:
                api.delete("notas", nota["id"])
                st.success("Nota eliminada.")
                st.rerun()
            except APIError as exc:
                st.error(f"Error al eliminar: {exc}")

        if nota:
            fmt_dl = c3.selectbox("Exportar", ["md", "txt"], key="nt_exp")
            if c3.button("⬇️ Descargar"):
                try:
                    data, mime = api.download(f"notas/{nota['id']}/exportar/", fmt=fmt_dl)
                    st.download_button(
                        f"Descargar .{fmt_dl}",
                        data=data,
                        file_name=f"nota_{nota['id']}.{fmt_dl}",
                        mime=mime,
                        key="nt_dlbtn",
                    )
                except APIError as exc:
                    st.error(f"Error al exportar: {exc}")

        # Previsualización.
        if contenido:
            st.divider()
            st.caption("Previsualización")
            if formato == "md":
                st.markdown(contenido)
            else:
                st.text(contenido)
