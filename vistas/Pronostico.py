import streamlit as st
import pandas as pd

import utilidades as util

util.cargarCSS()
util.generarMenu()

st.logo(
    "lg.png",
    link="https://monitoreo-ambiental-iot.streamlit.app/",
    size="large",
    icon_image="logo.png",
)

st.subheader("🌤️ Pronóstico del Tiempo Extendido (7 Días)")

df_clima_7d = util.obtener_pronostico_7_dias()

if df_clima_7d is not None and not df_clima_7d.empty:
    columnas_dias = st.columns(7)
            
    for idx, row in df_clima_7d.iterrows():
        with columnas_dias[idx]:
            nombre_dia = "Hoy" if idx == 0 else row["Fecha"].strftime("%a %d/%m")
                    
            st.markdown(f"""
                <div style="
                    background-color: #262730; 
                    padding: 12px; 
                    border-radius: 8px; 
                    text-align: center;
                    border: 1px solid #00CC96;
                    margin-bottom: 10px;
                    min-height: 210px;">
                    <b style="color: #00CC96; font-size: 0.95rem;">{nombre_dia}</b><br>
                    <span style="font-size: 1.25rem; display:block; margin: 4px 0; min-height: 38px;">{row['Estado']}</span>
                    <hr style="margin: 6px 0; border-color: #41444C;">
                    <small style="color: #FFAAAA; display:block;">🔥 Max: {row['Máxima (°C)']}°C</small>
                    <small style="color: #AACCFF; display:block;">❄️ Min: {row['Mínima (°C)']}°C</small>
                    <small style="color: #90E0EF; display:block; margin-top: 4px;">🌧️ Acum: {row['Cant_Precip (mm)']} mm</small>
                    <small style="color: #F4A261; display:block;">💨 Viento: {row['Viento_Max (km/h)']} km/h</small>
                </div>
            """, unsafe_allow_html=True)
else:
    st.error("No se pudieron cargar los datos meteorológicos.")

