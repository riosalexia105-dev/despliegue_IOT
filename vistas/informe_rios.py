import streamlit as st
import sys
import os
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit.components.v1 as components
import plotly.graph_objects as go

import utilidades as util
util.cargarCSS()

# Asegurar importación de utilidades.py desde la subcarpeta pages/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

st.title("🌊 Nivel e Hidrología de Ríos - Santa Fe")
st.markdown("Visualizacion hidrometrica en tiempo real integrada al panel IoT.")

dias = st.segmented_control("Período", [7, 15, 30], default=7, format_func=lambda d: f"{d} días")

try:
    info, serie = util.obtener_altura_santafe(dias or 7)
except Exception as e:
    st.error("No se pudieron obtener los datos del INA. Intenta de nuevo en unos minutos.")
    with st.expander("Detalle tecnico"):
        st.exception(e)
    st.stop()

#Estado
estado = info["estado"].upper()
if estado.startswith("EVAC"):
    st.error(f"🚨 EVACUACION: el rio supero {info['evacuacion']} m")
elif estado.startswith("ALERTA"):
    st.warning(f"⚠️ ALERTA: el rio supero {info['alerta']} m")
else:
    st.success("✅ Nivel normal")

st.markdown(
    """
        <style>
            div[data-testid="stMetric"] {
                padding: 12px; 
                border-radius: 8px;
                border: 1px solid #00CC96;
                min-height:130px;                
            }
            div[data-testid="stMetricValue"] {
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(
        label="📏 Altura actual",
        value=f"{info['altura']:.2f} m",
        delta=f"{info['variacion']:+.2f} m",
    )
with c2:
    st.metric(label="📈 Tendencia", value=info["tendencia"].capitalize())
with c3:
    st.metric(
        label="⚠️ Alerta / Evacuacion",
        value=f"{info['alerta']} / {info['evacuacion']} m",
    )
with c4:
    st.metric(label="🕒 Ultimo registro", value=f"{info['fecha']:%d/%m %H:%M}")


st.divider()

#Grafico
fig = go.Figure()
fig.add_trace(go.Scatter(x=serie["Fecha"], y=serie["Altura (m)"], mode="lines+markers", name="Altura", line=dict(color="#00CC96", width=3)))
fig.add_hline(y=info["alerta"], line_dash="dash", line_color="orange", annotation_text=f"Alerta ({info['alerta']} m)")
fig.add_hline(y=info["evacuacion"], line_dash="dash", line_color="red", annotation_text=f"Evacuación ({info['evacuacion']} m)")
fig.update_layout(template="plotly_dark", title="Altura hidrométrica - Santa Fe", xaxis_title="Fecha", yaxis_title="Altura (m)")
st.plotly_chart(fig, use_container_width=True)

#Tabla
with st.expander("📄 Ver registros"):
    st.dataframe(serie.sort_values("Fecha", ascending=False), use_container_width=True, hide_index=True)

st.caption("Fuente: Prefectura Naval Argentina via INA (alerta.ina.gob.ar).")

#Mapa Del INA
with st.expander("🗺️ Mapa del INA"):
    import streamlit.components.v1 as components
    components.iframe("https://alerta.ina.gob.ar/pub/mapa", height=700, scrolling=True)
