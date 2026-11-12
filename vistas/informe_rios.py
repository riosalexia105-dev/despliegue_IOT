import streamlit as st
import sys
import os
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import utilidades as util
import streamlit.components.v1 as components

# Asegurar importación de utilidades.py desde la subcarpeta pages/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Menú lateral unificado
util.cargarCSS()

st.title("🌊 Nivel e Hidrología de Ríos - Santa Fe")
st.markdown("Visualización hidrométrica en tiempo real integrada al panel IoT.")

df_rios = util.obtener_datos_hidro()

# --- TARJETAS MÉTRICAS (Igual al estilo de Temperatura / Humedad) ---
col1, col2, col3 = st.columns(3)

caudal_actual = df_rios["Caudal (m³/s)"].iloc[-1]
caudal_previo = df_rios["Caudal (m³/s)"].iloc[-2]
variacion = caudal_actual - caudal_previo

# Estimación referencial de altura para la zona
altura_estimada = round(caudal_actual / 3500, 2) 

with col1:
    st.metric(
        label="🌊 Caudal Actual (Paraná/Salado)", 
        value=f"{caudal_actual:,.1f} m³/s", 
        delta=f"{variacion:+,.1f} m³/s"
    )

with col2:
    st.metric(
        label="📏 Altura Estimada (Puerto Santa Fe)", 
        value=f"{altura_estimada} m", 
        delta=f"{round(variacion/3500, 2):+} m"
    )

with col3:
    estado = "NORMAL" if altura_estimada < 4.3 else ("ALERTA" if altura_estimada < 5.3 else "EVACUACIÓN")
    st.metric(
        label="⚠️ Estado Hidrométrico", 
        value=estado
    )

st.divider()

# --- GRÁFICO INTERACTIVO DE TENDENCIA (Plotly Express) ---
st.subheader("📈 Tendencia Histórica y Pronóstico (14 días)")

fig = px.line(
    df_rios, 
    x="Fecha", 
    y="Caudal (m³/s)", 
    markers=True,
    title="Comportamiento del Río en la Región",
    template="plotly_dark"
)

fig.update_traces(line_color="#00CC96", line_width=3)
fig.update_layout(xaxis_title="Fecha", yaxis_title="Caudal Estimado (m³/s)")

st.plotly_chart(fig, use_container_width=True)

# Tabla desplegable de datos
with st.expander("📄 Ver registros detallados"):
    st.dataframe(df_rios, use_container_width=True)


components.iframe(
    src="https://alerta.ina.gob.ar/pub/mapa",
    height=700,
    scrolling=True
)
