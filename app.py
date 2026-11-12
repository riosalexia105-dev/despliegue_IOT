import streamlit as st

st.set_page_config(
    page_title="Monitoreo Ambiental IoT",
    page_icon="🌡️",
    layout="wide"
)

st.logo(
    "lg.png",
    link="https://monitoreo-ambiental-iot.streamlit.app/",
    size="large",
    icon_image="logo.png")

pagina_inicio = st.Page(
    "vistas/Inicio.py", 
    title="Inicio", 
    icon=":material/dashboard:", 
    default=True  # Esta será la página que se abra por defecto
)

pagina_pronostico = st.Page(
    "vistas/Pronostico.py", 
    title="Pronostico Semanal", 
    icon=":material/partly_cloudy_day:"
)

pagina_rios = st.Page(
    "vistas/informe_rios.py", 
    title="Visualización de Graficos", 
    icon=":material/waves:"
)

pagina_admin = st.Page(
    "vistas/Admin.py", 
    title="Dashboard admin", 
    icon=":material/supervisor_account:"
)

navegacion = st.navigation({
    "Principal": [pagina_inicio],
    "Elementos": [pagina_pronostico, pagina_rios, pagina_admin]
})

navegacion.run()
