import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import date, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import smtplib
from email.mime.text import MIMEText
from io import BytesIO

st.set_page_config(page_title="Cronograma Contratistas", layout="wide")

usuarios = {
    "ricardo": {"password": "1234", "rol": "admin", "contrata": "Todas"},
    "breyssy": {"password": "Breylinda12", "rol": "admin", "contrata": "Todas"},
    "jeffrey": {"password": "12345", "rol": "admin", "contrata": "Todas"},
    "hector": {"password": "123456", "rol": "admin", "contrata": "Todas"},
    "soluciones_rg": {"password": "Rgsoluciones26!", "rol": "contratista", "contrata": "SOLUCIONES RG"},
    "gruposic": {"password": "Gruposic2026", "rol": "contratista", "contrata": "GRUPOSIC S.A. DE C.V."},
    "innovaciones_sym": {"password": "1234", "rol": "contratista", "contrata": "INNOVACIONES SYM S.A"},
    "internos_carso": {"password": "1234", "rol": "contratista", "contrata": "INTERNOS CARSO"},
    "supervisor": {"password": "abcd", "rol": "supervisor", "contrata": "Todas"},
}

if "logueado" not in st.session_state:
    st.session_state["logueado"] = False

if "modal_activo" not in st.session_state:
    st.session_state["modal_activo"] = False

if "modal_tipo" not in st.session_state:
    st.session_state["modal_tipo"] = "warning"

if "modal_titulo" not in st.session_state:
    st.session_state["modal_titulo"] = ""

if "modal_mensaje" not in st.session_state:
    st.session_state["modal_mensaje"] = ""


def abrir_modal(tipo, titulo, mensaje):
    st.session_state["modal_activo"] = True
    st.session_state["modal_tipo"] = tipo
    st.session_state["modal_titulo"] = titulo
    st.session_state["modal_mensaje"] = mensaje


@st.dialog("Mensaje del sistema")
def mostrar_modal():
    tipo = st.session_state["modal_tipo"]
    titulo = st.session_state["modal_titulo"]
    mensaje = st.session_state["modal_mensaje"]

    icono = "⚠️" if tipo == "warning" else "✅" if tipo == "success" else "❌"

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <h1 style='text-align:center; font-size:52px; margin-bottom:10px;'>{icono}</h1>
            <h2 style='text-align:center; font-size:26px; margin-bottom:10px;'>{titulo}</h2>
            <p style='text-align:center; font-size:18px; color:#D1D5DB;'>{mensaje}</p>
            """,
            unsafe_allow_html=True
        )

    if st.button("Cerrar", use_container_width=True):
        st.session_state["modal_activo"] = False
        st.rerun()


def login():
    st.title("🔐 Acceso Cronograma")
    usuario = st.text_input("Usuario")
    contraseña = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario in usuarios and usuarios[usuario]["password"] == contraseña:
            st.session_state["logueado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["rol"] = usuarios[usuario]["rol"]
            st.session_state["contrata_usuario"] = usuarios[usuario]["contrata"]
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")


if not st.session_state["logueado"]:
    login()
    st.stop()


st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    max-width: 98%;
}

h1 {
    font-size: 30px !important;
}

div[data-testid="stMetricValue"] {
    font-size: 30px !important;
}

div.stButton > button {
    min-height: 48px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    white-space: normal !important;
    line-height: 1.2 !important;
}
</style>
""", unsafe_allow_html=True)


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


def cargar_destinatarios_correo():
    response = (
        supabase
        .schema("cronograma")
        .table("correos_notificacion")
        .select("correo")
        .eq("activo", True)
        .execute()
    )

    return [
        item["correo"]
        for item in response.data
        if item.get("correo")
    ]


def enviar_correo_cambios(lista_cambios, semana, lunes, domingo, semana_cerrada=False):
    try:
        destinatarios = cargar_destinatarios_correo()

        if not destinatarios:
            return False, "No hay destinatarios activos configurados."

        usuario = st.session_state.get("usuario", "sistema")
        titulo = "Cronograma cerrado modificado" if semana_cerrada else "Cronograma actualizado"

        cuerpo = f"""
{titulo}

Semana: {semana}
Periodo: {lunes} al {domingo}
Usuario: {usuario}

Cambios realizados:
"""

        for cambio in lista_cambios:
            cuerpo += f"""
- Técnico: {cambio["tecnico"]}
  Contrata: {cambio["contrata"]}
  Día: {cambio["dia"]}
  Cambio: {cambio["estado_anterior"]} → {cambio["estado_nuevo"]}
"""

        asunto = (
            f"ALERTA cambio posterior cierre - Semana {semana}"
            if semana_cerrada
            else f"Cambio cronograma - Semana {semana}"
        )

        mensaje = MIMEText(cuerpo, "plain", "utf-8")
        mensaje["Subject"] = asunto
        mensaje["From"] = st.secrets["EMAIL_FROM"]
        mensaje["To"] = ", ".join(destinatarios)

        servidor = smtplib.SMTP(
            st.secrets["EMAIL_HOST"],
            st.secrets["EMAIL_PORT"]
        )

        servidor.starttls()
        servidor.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )

        servidor.sendmail(
            st.secrets["EMAIL_FROM"],
            destinatarios,
            mensaje.as_string()
        )

        servidor.quit()

        return True, None

    except Exception as e:
        return False, str(e)


def enviar_correo_cierre_semana(semana, lunes, domingo):
    try:
        destinatarios = cargar_destinatarios_correo()

        if not destinatarios:
            return False, "No hay destinatarios activos configurados."

        usuario = st.session_state.get("usuario", "sistema")

        cuerpo = f"""
Cronograma oficial cerrado

Semana: {semana}
Periodo: {lunes} al {domingo}
Cerrado por: {usuario}

A partir de este momento, cualquier cambio posterior quedará pendiente de validación.
"""

        mensaje = MIMEText(cuerpo, "plain", "utf-8")
        mensaje["Subject"] = f"Cronograma oficial cerrado - Semana {semana}"
        mensaje["From"] = st.secrets["EMAIL_FROM"]
        mensaje["To"] = ", ".join(destinatarios)

        servidor = smtplib.SMTP(
            st.secrets["EMAIL_HOST"],
            st.secrets["EMAIL_PORT"]
        )

        servidor.starttls()
        servidor.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )

        servidor.sendmail(
            st.secrets["EMAIL_FROM"],
            destinatarios,
            mensaje.as_string()
        )

        servidor.quit()

        return True, None

    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=300)
def cargar_tecnicos():
    response = (
        supabase
        .table("tabla_tecnicos_contrata")
        .select("*")
        .eq("estado_tecnico", "Activo")
        .order("identificador_tecnico")
        .execute()
    )
    return response.data


@st.cache_data(ttl=300)
def cargar_rol(fecha_inicio, fecha_fin):
    response = (
        supabase
        .schema("cronograma")
        .table("rol_trabajo")
        .select("*")
        .gte("fecha", str(fecha_inicio))
        .lte("fecha", str(fecha_fin))
        .execute()
    )
    return response.data


def cargar_semana_rol(fecha_inicio, fecha_fin):
    response = (
        supabase
        .schema("cronograma")
        .table("semanas_rol")
        .select("*")
        .eq("semana_inicio", str(fecha_inicio))
        .eq("semana_fin", str(fecha_fin))
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return {"estado_semana": "BORRADOR"}


def cerrar_semana_oficial(fecha_inicio, fecha_fin):
    usuario = st.session_state.get("usuario", "sistema")

    data = {
        "semana_inicio": str(fecha_inicio),
        "semana_fin": str(fecha_fin),
        "estado_semana": "CERRADA",
        "cerrado_por": usuario
    }

    supabase.schema("cronograma").table("semanas_rol").upsert(
        data,
        on_conflict="semana_inicio,semana_fin"
    ).execute()


def guardar_estado(codigo_tecnico, fecha, estado_rol):
    data = {
        "codigo_tecnico": codigo_tecnico,
        "fecha": str(fecha),
        "estado_rol": estado_rol,
        "actualizado_por": st.session_state.get("usuario", "sistema")
    }

    supabase.schema("cronograma").table("rol_trabajo").upsert(
        data,
        on_conflict="codigo_tecnico,fecha"
    ).execute()


def registrar_historial_cambio(cambio, correo_enviado):
    data = {
        "codigo_tecnico": cambio["tecnico"],
        "fecha_afectada": cambio["fecha_afectada"],
        "estado_anterior": cambio["estado_anterior"],
        "estado_nuevo": cambio["estado_nuevo"],
        "motivo": "Cambio posterior cierre",
        "autorizado_por": None,
        "usuario_cambio": st.session_state.get("usuario", "sistema"),
        "correo_enviado": correo_enviado,
        "estado_validacion": "PENDIENTE",
        "resultado_validacion": None,
        "validado_por": None,
        "validado_en": None
    }

    supabase.schema("cronograma").table("historial_cambios_rol").insert(data).execute()


def reiniciar_semana(fecha_inicio, fecha_fin):
    supabase.schema("cronograma").table("rol_trabajo") \
        .delete() \
        .gte("fecha", str(fecha_inicio)) \
        .lte("fecha", str(fecha_fin)) \
        .execute()


def obtener_estado(df_rol, codigo, dia):
    if df_rol.empty:
        return "Trabaja"

    fila = df_rol[
        (df_rol["codigo_tecnico"] == codigo) &
        (df_rol["fecha"] == str(dia))
    ]

    if fila.empty:
        return "Trabaja"

    return fila.iloc[0]["estado_rol"]

def convertir_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cronograma")
    return output.getvalue()


with st.sidebar:
    st.markdown("## 🎛 Filtros")

    semana_actual = date.today().isocalendar().week

    año = st.selectbox(
        "Año",
        [2026, 2025, 2024],
        index=0
    )

    semana = st.number_input(
        "Semana del año",
        min_value=1,
        max_value=53,
        value=semana_actual,
        step=1
    )

    lunes = date.fromisocalendar(año, int(semana), 1)
    domingo = date.fromisocalendar(año, int(semana), 7)


semana_rol = cargar_semana_rol(lunes, domingo)
estado_semana = semana_rol.get("estado_semana", "BORRADOR")
semana_cerrada = estado_semana == "CERRADA"


st.markdown("# 📅 Cronograma de Trabajo")

st.markdown(
    f"""
    <div style="
        font-size:26px;
        font-weight:700;
        margin-bottom:10px;
        margin-top:-10px;
    ">
    📆 Semana {semana}: {lunes} al {domingo}
    </div>
    """,
    unsafe_allow_html=True
)

if semana_cerrada:
    st.markdown(
        """
        <div style="
            background:#7F1D1D;
            color:white;
            padding:10px 16px;
            border-radius:12px;
            font-size:17px;
            font-weight:800;
            margin-bottom:12px;
            display:inline-block;
        ">
            🔒 Semana CERRADA oficialmente
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div style="
            background:#92400E;
            color:white;
            padding:10px 16px;
            border-radius:12px;
            font-size:17px;
            font-weight:800;
            margin-bottom:12px;
            display:inline-block;
        ">
            🟡 Semana en BORRADOR
        </div>
        """,
        unsafe_allow_html=True
    )


tecnicos = cargar_tecnicos()
df_tecnicos = pd.DataFrame(tecnicos)

if df_tecnicos.empty:
    abrir_modal(
        "warning",
        "Sin técnicos activos",
        "No hay técnicos activos cargados."
    )
    if st.session_state["modal_activo"]:
        mostrar_modal()
    st.stop()

opciones_contrata = ["Todas"] + sorted(
    df_tecnicos["contrata"].dropna().unique().tolist()
)

opciones_tecnologia = ["Todas"] + sorted(
    df_tecnicos["tecnologia"].dropna().unique().tolist()
)

with st.sidebar:
    if st.session_state.get("rol") == "contratista":
        filtro_contrata = st.session_state.get("contrata_usuario")
        st.info(f"Contrata: {filtro_contrata}")
    else:
        filtro_contrata = st.selectbox(
            "Contrata",
            opciones_contrata
        )

    filtro_tecnologia = st.selectbox(
        "Tecnología",
        opciones_tecnologia
    )

if filtro_contrata != "Todas":
    df_tecnicos = df_tecnicos[df_tecnicos["contrata"] == filtro_contrata]

if filtro_tecnologia != "Todas":
    df_tecnicos = df_tecnicos[df_tecnicos["tecnologia"] == filtro_tecnologia]

rol = cargar_rol(lunes, domingo)
df_rol = pd.DataFrame(rol)

dias = [lunes + timedelta(days=i) for i in range(7)]
nombres_base = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
nombres_dias = [
    f"{nombres_base[i]} {dias[i].strftime('%d/%m')}"
    for i in range(7)
]

estados = [
    "Trabaja",
    "Libre",
    "Vacaciones",
    "Incapacidad",
    "Permiso",
    "Suspendido",
    "Vehiculo-averiado"
]


filas = []

for _, tecnico in df_tecnicos.iterrows():
    codigo = tecnico["identificador_tecnico"]

    fila = {
        "Tecnico": codigo,
        "Contrata": tecnico["contrata"]
    }

    for i, dia in enumerate(dias):
        fila[nombres_dias[i]] = obtener_estado(
            df_rol,
            codigo,
            dia
        )

    filas.append(fila)

df_tablero = pd.DataFrame(filas)


# ==========================================
# BOTONES ARRIBA
# ==========================================
es_admin = st.session_state.get("rol") == "admin"

if semana_cerrada:
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1.4, 1.3, 1.3, 1.5])
else:
    if es_admin:
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(
            [1.4, 1.7, 1.3, 1.3, 1.5]
        )
    else:
        col_btn1, col_btn3, col_btn4, col_btn5 = st.columns(
            [1.4, 1.3, 1.3, 1.5]
        )

with col_btn1:
    guardar = st.button(
        "💾 Guardar cambios",
        type="primary",
        use_container_width=True
    )

if not semana_cerrada and es_admin:

    with col_btn2:
        cerrar_semana = st.button(
            "🔒 Cerrar semana oficial",
            use_container_width=True
        )

else:
    cerrar_semana = False

with col_btn3:
    reiniciar = st.button(
        "♻️ Reiniciar semana",
        use_container_width=True
    )

with col_btn4:
    actualizar = st.button(
        "🔄 Actualizar",
        use_container_width=True
    )

if semana_cerrada:
    with col_btn4:
        st.download_button(
            label="📥 Exportar Excel",
            data=convertir_excel(df_tablero),
            file_name=f"cronograma_semana_{semana}_{año}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    with col_btn5:
        st.download_button(
            label="📥 Exportar Excel",
            data=convertir_excel(df_tablero),
            file_name=f"cronograma_semana_{semana}_{año}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


st.markdown("### 📌 Resumen de la semana")

resumen_cols = st.columns(7)

for i, nombre_dia in enumerate(nombres_dias):
    total_trabaja = (df_tablero[nombre_dia] == "Trabaja").sum()

    resumen_cols[i].metric(
        nombre_dia,
        int(total_trabaja)
    )

st.markdown("""
<div style="
    display:flex;
    gap:22px;
    flex-wrap:wrap;
    margin-bottom:20px;
    margin-top:10px;
    font-size:18px;
">
    <span>🟢 Trabaja</span>
    <span>🟡 Libre</span>
    <span>🔵 Vacaciones</span>
    <span>🟣 Incapacidad</span>
    <span>🟠 Permiso</span>
    <span>⚫ Suspendido</span>
    <span>🔴 Vehiculo-averiado</span>
</div>
""", unsafe_allow_html=True)


gb = GridOptionsBuilder.from_dataframe(df_tablero)

gb.configure_column("Tecnico", editable=False, pinned="left", width=120)
gb.configure_column("Contrata", editable=False, pinned="left", width=200)

cellstyle_jscode = JsCode("""
function(params) {

    if (params.value == 'Trabaja') {
        return {'backgroundColor': '#2E7D32', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Libre') {
        return {'backgroundColor': '#FBC02D', 'color': 'black', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Vacaciones') {
        return {'backgroundColor': '#1976D2', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Incapacidad') {
        return {'backgroundColor': '#7B1FA2', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Permiso') {
        return {'backgroundColor': '#F57C00', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Suspendido') {
        return {'backgroundColor': '#424242', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

    if (params.value == 'Vehiculo-averiado') {
        return {'backgroundColor': '#C62828', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}
    }

}
""")

for nombre_columna in nombres_dias:
    gb.configure_column(
        nombre_columna,
        editable=True,
        cellEditor='agSelectCellEditor',
        cellEditorParams={'values': estados},
        cellStyle=cellstyle_jscode,
        width=130
    )

gb.configure_default_column(
    resizable=True,
    sortable=True,
    filter=True
)

gridOptions = gb.build()

st.markdown("### 👷 Tablero editable")

grid_response = AgGrid(
    df_tablero,
    gridOptions=gridOptions,
    height=600,
    width='100%',
    update_mode=GridUpdateMode.VALUE_CHANGED,
    allow_unsafe_jscode=True,
    fit_columns_on_grid_load=False,
    theme="streamlit"
)

df_editado = pd.DataFrame(grid_response["data"])


if guardar:
    lista_cambios = []

    for _, fila_editada in df_editado.iterrows():
        codigo = fila_editada["Tecnico"]
        contrata = fila_editada["Contrata"]

        fila_original = df_tablero[df_tablero["Tecnico"] == codigo]

        if fila_original.empty:
            continue

        fila_original = fila_original.iloc[0]

        for i, dia in enumerate(dias):
            nombre_dia = nombres_dias[i]

            estado_anterior = fila_original[nombre_dia]
            estado_nuevo = fila_editada[nombre_dia]

            if estado_anterior != estado_nuevo:
                lista_cambios.append({
                    "tecnico": codigo,
                    "contrata": contrata,
                    "dia": nombre_dia,
                    "fecha_afectada": str(dia),
                    "estado_anterior": estado_anterior,
                    "estado_nuevo": estado_nuevo
                })

                guardar_estado(
                    codigo,
                    dia,
                    estado_nuevo
                )

    if lista_cambios:

        if semana_cerrada:
            correo_ok, error_correo = enviar_correo_cambios(
                lista_cambios,
                semana,
                lunes,
                domingo,
                semana_cerrada=True
            )

            for cambio in lista_cambios:
                registrar_historial_cambio(
                    cambio,
                    correo_ok
                )

            if correo_ok:
                abrir_modal(
                    "warning",
                    "Cambio posterior cierre",
                    f"Se guardaron {len(lista_cambios)} cambio(s), quedaron pendientes de validación y se envió el correo."
                )
            else:
                abrir_modal(
                    "warning",
                    "Cambio posterior cierre",
                    f"Se guardaron {len(lista_cambios)} cambio(s), quedaron pendientes de validación, pero falló el correo: {error_correo}"
                )

        else:
            abrir_modal(
                "success",
                "Cambios guardados",
                f"Se guardaron {len(lista_cambios)} cambio(s) correctamente."
            )

        st.cache_data.clear()

    else:
        abrir_modal(
            "warning",
            "No se detectaron cambios",
            "No hay modificaciones para guardar."
        )


if cerrar_semana:
    if semana_cerrada:
        abrir_modal(
            "warning",
            "Semana ya cerrada",
            "Esta semana ya está cerrada oficialmente."
        )
    else:
        cerrar_semana_oficial(lunes, domingo)

        correo_ok, error_correo = enviar_correo_cierre_semana(
            semana,
            lunes,
            domingo
        )

        if correo_ok:
            abrir_modal(
                "success",
                "Semana cerrada",
                "El cronograma quedó cerrado oficialmente y se envió el correo."
            )
        else:
            abrir_modal(
                "warning",
                "Semana cerrada",
                f"El cronograma quedó cerrado oficialmente, pero falló el correo: {error_correo}"
            )

        st.cache_data.clear()


if reiniciar:
    if semana_cerrada:
        abrir_modal(
            "warning",
            "Acción bloqueada",
            "No se puede reiniciar una semana cerrada."
        )
    else:
        reiniciar_semana(lunes, domingo)
        st.cache_data.clear()

        abrir_modal(
            "success",
            "Semana reiniciada",
            "Todos los técnicos quedaron en Trabaja."
        )


if actualizar:
    st.cache_data.clear()
    st.rerun()


if st.session_state["modal_activo"]:
    mostrar_modal()


st.info(
    "En BORRADOR, Guardar cambios solo actualiza el cronograma. "
    "Cuando la semana esté CERRADA, cualquier cambio queda pendiente de validación."
)