import streamlit as st
import smtplib
from email.mime.text import MIMEText

st.set_page_config(
    page_title="Prueba Correo",
    layout="wide"
)

st.title("📧 Prueba controlada de correo")

st.info("Esta prueba envía correos individuales, uno por uno.")

destinatarios_texto = st.text_area(
    "Correos destino, uno por línea",
    value="""j.aragona@ccicsa.com.mx
ricardo.aragon1@gmail.com"""
)

if st.button("Enviar prueba", type="primary"):

    destinatarios = [
        correo.strip()
        for correo in destinatarios_texto.splitlines()
        if correo.strip()
    ]

    enviados = []
    errores = []

    try:
        servidor = smtplib.SMTP(
            st.secrets["EMAIL_HOST"],
            st.secrets["EMAIL_PORT"]
        )

        servidor.starttls()

        servidor.login(
            st.secrets["EMAIL_USER"],
            st.secrets["EMAIL_PASSWORD"]
        )

        for destinatario in destinatarios:
            try:
                cuerpo = f"""
Hola,

Este es un correo de prueba individual enviado desde la aplicación de cronograma.

Destinatario probado:
{destinatario}

Si recibes este correo, la entrega individual está funcionando correctamente.

Saludos.
"""

                mensaje = MIMEText(cuerpo, "plain", "utf-8")
                mensaje["Subject"] = "Prueba individual correo cronograma"
                mensaje["From"] = st.secrets["EMAIL_FROM"]
                mensaje["To"] = destinatario

                servidor.sendmail(
                    st.secrets["EMAIL_FROM"],
                    destinatario,
                    mensaje.as_string()
                )

                enviados.append(destinatario)

            except Exception as e:
                errores.append({
                    "correo": destinatario,
                    "error": str(e)
                })

        servidor.quit()

        st.success(f"Correos enviados correctamente: {len(enviados)}")

        if enviados:
            st.write("Enviados:")
            st.write(enviados)

        if errores:
            st.error(f"Correos con error: {len(errores)}")
            st.write(errores)

    except Exception as e:
        st.error(f"Error general SMTP: {e}")