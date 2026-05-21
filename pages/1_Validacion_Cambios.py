import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

st.set_page_config(
    page_title="Validación Cambios",
    layout="wide"
)

if "logueado" not in st.session_state:
    st.warning("Debes iniciar sesión.")
    st.stop()

if st.session_state.get("rol") not in ["admin", "supervisor"]:
    st.error("No tienes acceso a esta página.")
    st.stop()

st.title("✅ Validación cambios cronograma")

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


@st.cache_data(ttl=60)
def cargar_pendientes():
    cambios = (
        supabase
        .schema("cronograma")
        .table("historial_cambios_rol")
        .select("*")
        .eq("estado_validacion", "PENDIENTE")
        .order("fecha_cambio", desc=True)
        .execute()
    )

    tecnicos = (
        supabase
        .table("tabla_tecnicos_contrata")
        .select("identificador_tecnico, contrata, supervisor")
        .execute()
    )

    df_cambios = pd.DataFrame(cambios.data)
    df_tecnicos = pd.DataFrame(tecnicos.data)

    if df_cambios.empty:
        return df_cambios

    if not df_tecnicos.empty:
        df_cambios = df_cambios.merge(
            df_tecnicos,
            left_on="codigo_tecnico",
            right_on="identificador_tecnico",
            how="left"
        )

    return df_cambios


def validar_cambio(id_cambio, resultado):
    supabase.schema("cronograma").table("historial_cambios_rol").update({
        "estado_validacion": "VALIDADO",
        "resultado_validacion": resultado,
        "validado_por": st.session_state.get("usuario", "sistema"),
        "validado_en": datetime.now().isoformat()
    }).eq("id", id_cambio).execute()


df = cargar_pendientes()

if df.empty:
    st.success("No hay cambios pendientes de validación.")
    st.stop()
    
# ==========================================
# FILTRO SUPERVISOR
# ==========================================

filtro_supervisor = st.selectbox(
    "Supervisor",
    ["Todos"] + sorted(
        df["supervisor"].dropna().unique().tolist()
    )
)

if filtro_supervisor != "Todos":
    df = df[df["supervisor"] == filtro_supervisor]

if df.empty:
    st.success("No hay cambios pendientes de validación.")
    st.stop()

st.subheader("📋 Cambios pendientes")

for _, row in df.iterrows():

    with st.container(border=True):
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"### 👷 {row['codigo_tecnico']}")
            st.write(f"Contrata: {row.get('contrata', 'Sin dato')}")
            st.write(f"Supervisor: {row.get('supervisor', 'Sin dato')}")

        with col2:
            st.write(f"Fecha afectada: {row['fecha_afectada']}")
            st.write(f"Cambio: {row['estado_anterior']} → {row['estado_nuevo']}")
            st.write(f"Usuario cambio: {row['usuario_cambio']}")

        with col3:
            st.write(f"Fecha cambio: {row.get('fecha_cambio', '')}")

            btn1, btn2 = st.columns(2)

            with btn1:
                if st.button(
                    "✅ Justificado",
                    key=f"justificado_{row['id']}",
                    use_container_width=True
                ):
                    validar_cambio(row["id"], "JUSTIFICADO")
                    st.cache_data.clear()
                    st.success("Cambio validado como JUSTIFICADO.")
                    st.rerun()

            with btn2:
                if st.button(
                    "❌ Penalizado",
                    key=f"penalizado_{row['id']}",
                    use_container_width=True
                ):
                    validar_cambio(row["id"], "PENALIZADO")
                    st.cache_data.clear()
                    st.warning("Cambio validado como PENALIZADO.")
                    st.rerun()