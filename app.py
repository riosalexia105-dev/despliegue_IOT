import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Monitoreo Ambiental ESP32",
    page_icon="🌡️",
    layout="wide"
)

# Carga de credenciales con respaldo local opcional para pruebas
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    MQTT_BROKER = st.secrets["hivemq"]["MQTT_BROKER"]
    MQTT_PORT = int(st.secrets["hivemq"]["MQTT_PORT"])
    MQTT_USER = st.secrets["hivemq"]["MQTT_USER"]
    MQTT_PASS = st.secrets["hivemq"]["MQTT_PASS"]
    MQTT_TOPIC = st.secrets["hivemq"]["MQTT_TOPIC"]
except Exception:
    # Respaldo temporal para pruebas locales
    SUPABASE_URL = "https://etujhhaffatmobyaqftd.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0dWpoaGFmZmF0bW9ieWFxZnRkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjE2MzU4OCwiZXhwIjoyMTAxNzM5NTg4fQ.o0C94lPHjaEG7tZ4XyCXLiBhYwqCDizJDNaU8ZX9xzQ"
    MQTT_BROKER = "6a27f69ee3d5461f8991096bdfcaaf3c.s1.eu.hivemq.cloud"
    MQTT_PORT = 8883
    MQTT_USER = "adminhive"
    MQTT_PASS = "adminhive"
    MQTT_TOPIC = "sensores/esp32/datos"

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Error: Las credenciales de Supabase no están configuradas correctamente.")
    st.stop()

@st.cache_resource
def iniciar_servicios():
    # 1. Inicializar cliente de Supabase
    client_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 2. Configurar y arrancar el cliente MQTT para escuchar HiveMQ en segundo plano
    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            data = {
                "Temperatura": float(payload.get("Temperatura", 0.0)),
                "Humedad": float(payload.get("Humedad", 0.0)),
                "Presion": float(payload.get("Presion", 0.0)),
                "Fecha": payload.get("Fecha", datetime.now().isoformat()),
                "Gas-Ppm": float(payload.get("Gas-Ppm", 0.0))
            }
            # Inserta automáticamente el paquete recibido del ESP32 a Supabase
            client_supabase.table("Lecturas").insert(data).execute()
        except Exception as e:
            print(f"Error procesando mensaje MQTT: {e}")

    try:
        client_mqtt = mqtt.Client()
        client_mqtt.username_pw_set(MQTT_USER, MQTT_PASS)
        client_mqtt.tls_set()  # Habilita seguridad TLS requerida por HiveMQ Cloud
        client_mqtt.on_message = on_message
        client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        client_mqtt.subscribe(MQTT_TOPIC)
        client_mqtt.loop_start()  # Mantiene el hilo escuchando en segundo plano
    except Exception as e:
        print(f"No se pudo inicializar la conexión MQTT: {e}")

    return client_supabase

supabase = iniciar_servicios()

# Funciones para obtener datos de Supabase para los gráficos
def obtener_segun(limite: int = 50):
    try:
        res = supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).limit(limite).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def obtener_ultimo():
    try:
        res = supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).limit(1).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

# Interfaz Principal
def main():
    st.title("🌱 Sistema de Monitoreo Ambiental ESP32")
    st.markdown("Visualización en tiempo real conectada mediante **MQTT (HiveMQ)** y almacenamiento en **Supabase**.")

    # Botón para actualizar datos manualmente
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

    df_datos = obtener_segun(50)
    df_ultimo = obtener_ultimo()

    if df_datos.empty or df_ultimo.empty:
        st.warning("⚠️ No se encontraron registros en la tabla 'Lecturas' de Supabase. Esperando publicaciones del ESP32 vía MQTT...")
        st.stop()

    # Asegurar orden cronológico ascendente para los gráficos utilizando Pandas/NumPy
    if "Fecha" in df_datos.columns:
        df_datos["Fecha"] = pd.to_datetime(df_datos["Fecha"])
        df_datos = df_datos.sort_values("Fecha", ascending=True)

    # Extraer valores actuales
    gas_actual = float(df_ultimo["Gas-Ppm"].iloc[0]) if "Gas-Ppm" in df_ultimo.columns else 0.0
    temp_actual = float(df_ultimo["Temperatura"].iloc[0]) if "Temperatura" in df_ultimo.columns else 0.0
    hum_actual = float(df_ultimo["Humedad"].iloc[0]) if "Humedad" in df_ultimo.columns else 0.0
    presion_actual = float(df_ultimo["Presion"].iloc[0]) if "Presion" in df_ultimo.columns else 0.0

    # Gráficos de líneas temporales con Plotly
    fig_temp = px.line(df_datos, x='Fecha', y='Temperatura', title='Evolución de la Temperatura', markers=True, template='plotly_dark')
    fig_temp.update_traces(line_color='#FF4B4B')

    fig_hum = px.line(df_datos, x='Fecha', y='Humedad', title='Evolución de la Humedad Relativa', markers=True, template='plotly_dark')
    fig_hum.update_traces(line_color='#0068C9')

    fig_presion = px.line(df_datos, x='Fecha', y='Presion', title='Evolución de la Presión Atmosférica', markers=True, template='plotly_dark')
    fig_presion.update_traces(line_color='#83C9FF')

    fig_gas_line = px.line(df_datos, x='Fecha', y='Gas-Ppm', title='Evolución de la Concentración de Gas (PPM)', markers=True, template='plotly_dark')
    fig_gas_line.update_traces(line_color='#00CC96')

    # Tacómetro (Gauge Chart) para el Gas (PPM) en vivo
    fig_gas = go.Figure(go.Indicator(
        mode="gauge+number",
        value=gas_actual,
        title={'text': "Concentración de Gas (PPM)", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 1000], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#00CC96"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 400], 'color': 'rgba(0, 204, 150, 0.3)'},
                {'range': [400, 700], 'color': 'rgba(255, 183, 77, 0.3)'},
                {'range': [700, 1000], 'color': 'rgba(255, 75, 75, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 700
            }
        }
    ))
    fig_gas.update_layout(template='plotly_dark', margin=dict(t=50, b=20, l=20, r=20), height=300)

    # Organización en Pestañas (Tabs)
    tab1, tab2, tab3 = st.tabs(["📊 Estado Actual", "📈 Tendencias Históricas", "📋 Registros de Base de Datos"])

    with tab1:
        st.subheader("Estado actual de los sensores (En vivo)")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("🌡️ Temperatura", f"{temp_actual} °C")
        with col_m2:
            st.metric("💧 Humedad", f"{hum_actual} %")
        with col_m3:
            st.metric("📊 Presión", f"{presion_actual} hPa")
        with col_m4:
            st.metric("🧪 Gas (PPM)", f"{gas_actual} PPM")
        
        st.markdown("---")
        col_g1, col_g2, col_g3 = st.columns([1, 2, 1])
        with col_g2:
            st.plotly_chart(fig_gas, use_container_width=True)

    with tab2:
        st.subheader("Evolución temporal de variables climáticas")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_temp, use_container_width=True)
            st.plotly_chart(fig_hum, use_container_width=True)
        with col2:
            st.plotly_chart(fig_presion, use_container_width=True)
            st.plotly_chart(fig_gas_line, use_container_width=True)

    with tab3:
        st.subheader(f"Últimos {len(df_datos)} registros en la Base de Datos")
        st.dataframe(df_datos, use_container_width=True)

if __name__ == '__main__':
    main()
