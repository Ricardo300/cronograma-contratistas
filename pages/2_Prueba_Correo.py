import streamlit as st
import smtplib
from email.mime.text import MIMEText

st.set_page_config(
    page_title="Prueba Correo",
    layout="wide"
)

st.title("📧 Prueba de envío de correo")

correo_destino = st.text_input(
    "Correo destino",
    value="ricardo.aragon1@gmail.com"
)

if st.button("Enviar correo de prueba", type="primary"):

    try:
        cuerpo = """
Hola,

Este es un correo de prueba enviado desde la aplicación de cronograma.

Si recibes este correo, la configuración SMTP está funcionando correctamente.

Saludos.
"""

        mensaje = MIMEText(cuerpo, "plain", "utf-8")
        mensaje["Subject"] = "Prueba correo cronograma"
        mensaje["From"] = st.secrets["EMAIL_FROM"]
        mensaje["To"] = correo_destino

        servidor = smtplib.SMTP(
            st.secrets["EMAIL_HOST"],
            int(st.secrets["EMAIL_PORT"])
        )

        servidor.starttls()

        servidor.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )

        servidor.sendmail(
            st.secrets["EMAIL_FROM"],
            [correo_destino],
            mensaje.as_string()
        )

        servidor.quit()

        st.success("Correo enviado correctamente.")

    except Exception as e:
        st.error(f"Error enviando correo: {e}")