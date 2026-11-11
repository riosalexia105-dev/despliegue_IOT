import streamlit as st
import utilidades as util

st.set_page_config(
    page_title="Monitoreo Ambiental IoT",
    page_icon="🌡️",
    layout="wide"
)

util.generarMenu()

st.title("Panel Principal de Monitoreo Ambiental IoT")
# ... resto de tu código de sensores
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"  # API para pronósticos

@st.cache_data(ttl=3600)  # La caché guardará los datos por 1 hora completa
def obtener_pronostico_7_dias():
    try:
        url = FORECAST_URL
        params = {
            "latitude": -31.6333,
            "longitude": -60.7,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
            "timezone": "auto"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MonitorAmbientalIoT/1.0"
        }
        
        # Agregamos un tiempo límite estricto de 5 segundos para que la app no se cuelgue si falla internet
        r = requests.get(url, params=params, headers=headers, timeout=5)
        
        if r.status_code == 200:
            daily_data = r.json().get("daily", {})
            if daily_data and "time" in daily_data:
                df = pd.DataFrame({
                    "Fecha": pd.to_datetime(daily_data.get("time")),
                    "Máxima (°C)": [float(x) if x is not None else 0.0 for x in daily_data.get("temperature_2m_max", [])],
                    "Mínima (°C)": [float(x) if x is not None else 0.0 for x in daily_data.get("temperature_2m_min", [])],
                    "Cant_Precip (mm)": [float(x) if x is not None else 0.0 for x in daily_data.get("precipitation_sum", [])],
                    "Viento_Max (km/h)": [float(x) if x is not None else 0.0 for x in daily_data.get("wind_speed_10m_max", [])],
                    "Código": [int(x) if x is not None else 0 for x in daily_data.get("weather_code", [])]
                })
                
                mapeo_codigos = {
                    0: "☀️ Despejado", 1: "🌤️ Despejado", 2: "🌤️ Parcialmente Nublado", 3: "☁️ Nublado",
                    45: "🌫️ Niebla", 48: "🌫️ Niebla", 51: "🌦️ Llovizna", 53: "🌦️ Llovizna", 55: "🌦️ Llovizna",
                    61: "🌧️ Lluvia Débil", 63: "🌧️ Lluvia", 65: "🌧️ Lluvia Fuerte", 80: "🌧️ Chubascos",
                    81: "🌧️ Chubascos", 82: "🌧️ Chubascos", 95: "⛈️ Tormenta", 96: "⛈️ Tormenta", 99: "⛈️ Tormenta"
                }
                
                df["Estado"] = df["Código"].apply(lambda x: mapeo_codigos.get(x, "❓ Variable"))
                return df.head(7)
    except Exception as e:
        print(f"Error crítico de red en Open-Meteo: {e}")
    return pd.DataFrame()

# Llamada a la función
df_clima_7d = obtener_pronostico_7_dias()

# 2. Inyección de estilos CSS
st.markdown("""
    <style>
    img[data-testid="stLogo"] {
        position: fixed;
        top: 1px;
        height: 3rem !important;
        width: auto !important;
    }
    header[data-testid="stHeader"] {
        background-color: #1A1C24 !important;
        border-bottom: 1px solid #00CC96 !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Este bloque es el que inyecta el título correctamente */
    header[data-testid="stHeader"]::after {
        content: "Instituto Superior Domingo Guzman Silva";
        color: #ffff !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        margin-left: 100px !important; /* Espacio para que no se encima con los botones de la izquierda */
        white-space: nowrap;
    }
    .custom-card {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .card-title {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        margin-bottom: 10px;
        opacity: 0.9;
    }
    .card-value {
        font-size: 2.2rem !important;
        font-weight: bold !important;
        color: #FFFFFF !important;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

# Carga de credenciales con respaldo local opcional para pruebas
SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]
MQTT_BROKER = st.secrets["hivemq"]["MQTT_BROKER"]
MQTT_PORT = int(st.secrets["hivemq"]["MQTT_PORT"])
MQTT_USER = st.secrets["hivemq"]["MQTT_USER"]
MQTT_PASS = st.secrets["hivemq"]["MQTT_PASS"]
MQTT_TOPIC = st.secrets["hivemq"]["MQTT_TOPIC"]

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Error: Las credenciales de Supabase no están configuradas correctamente.")
    st.stop()

if not MQTT_BROKER:
    st.error("Error: Las credenciales de HiveMQ no están configuradas correctamente.")
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
            # 3. Inserta automáticamente el paquete recibido del ESP32 a Supabase
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
def obtener_todos():
    try:
        res = supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

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

def crear_gauge(valor_actual):
    fig_gas = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor_actual,
        title={'text': "Concentración de Gas (PPM)", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 1400], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#00CC96"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 399], 'color': 'rgba(0, 204, 150, 0.3)'},
                {'range': [400, 699], 'color': 'rgba(255, 183, 77, 0.3)'},
                {'range': [700, 1400], 'color': 'rgba(255, 75, 75, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': valor_actual
            }
        }
    ))
    fig_gas.update_layout(template='plotly_dark', margin=dict(t=50, b=20, l=20, r=20), height=300)
    return fig_gas

@st.fragment(run_every=10)
def renderizar_tiempo_real():
    st.logo(
    "lg.png",
    link="https://monitoreo-ambiental-iot.streamlit.app/",
    size="large",
    icon_image="logo.png")
    df_ultimo_vivo = obtener_ultimo()
    
    if not df_ultimo_vivo.empty:
        temp_vivo = df_ultimo_vivo["Temperatura"].iloc[0]
        hum_vivo = df_ultimo_vivo["Humedad"].iloc[0]
        presion_vivo = df_ultimo_vivo["Presion"].iloc[0]
        fecha_iso_raw = df_ultimo_vivo["Fecha"].iloc[0]
        gas_vivo = df_ultimo_vivo["Gas-Ppm"].iloc[0]

        fig_gas_viva = crear_gauge(gas_vivo)
        
        col_gauge, col_cards = st.columns([3, 1])
        with col_cards:
            st.markdown(f"""
                <div class="custom-card" style="border: 1px solid #00CC96;">
                    <div class="card-title">🌡️ Temperatura</div>
                    <div class="card-value">{temp_vivo} °C</div>
                </div>
            """, unsafe_allow_html=True)
                
            st.markdown(f"""
                <div class="custom-card" style="border: 1px solid #00CC96;">
                    <div class="card-title">💧 Humedad</div>
                    <div class="card-value">{hum_vivo} %</div>
                </div>
            """, unsafe_allow_html=True)
                
            st.markdown(f"""
                <div class="custom-card" style=" border: 1px solid #00CC96;">
                    <div class="card-title">⏲ Presión</div>
                    <div class="card-value">{presion_vivo} hPa</div>
                </div>
            """, unsafe_allow_html=True)
                
            st.markdown(f"""
                <div class="custom-card" style="border: 1px solid #00CC96;">
                    <div class="card-title">🍃 Gas (PPM)</div>
                    <div class="card-value">{gas_vivo} PPM</div>
                </div>
            """, unsafe_allow_html=True)

        with col_gauge:
            st.header('')
            fig_gas = crear_gauge(gas_vivo)
            fig_gas.update_layout(height=480) 
            st.plotly_chart(fig_gas, use_container_width=True)

            dt_actual = datetime.fromisoformat(str(fecha_iso_raw))
            fecha_formateada = dt_actual.strftime("%d/%m/%Y")
            hora_formateada = dt_actual.strftime("%H:%M:%S")
            st.caption(f"⏱️ Última actualización del sensor: **{fecha_formateada}** a las **{hora_formateada}**")
    else:
        st.warning("No hay lecturas en tiempo real disponibles.")

def main():
    st.title("🌱 Sistema de Monitoreo Ambiental ESP32")
    st.markdown("Visualización en tiempo real conectada mediante **MQTT (HiveMQ)** y almacenamiento en **Supabase**.")

    df_datos = obtener_segun(50)
    
    if df_datos.empty:
        st.warning("⚠️ No se encontraron registros en la tabla 'Lecturas' de Supabase. Esperando publicaciones del ESP32 vía MQTT...")
        st.stop()

    if "Fecha" in df_datos.columns:
        df_datos["Fecha"] = pd.to_datetime(df_datos["Fecha"])
        df_datos = df_datos.sort_values("Fecha", ascending=True)

    # Gráficos de líneas temporales con Plotly
    fig_temp = px.line(df_datos, x='Fecha', y='Temperatura', title='Evolución de la Temperatura', markers=True, template='plotly_dark')
    fig_temp.update_traces(line_color='#FF4B4B')

    fig_hum = px.line(df_datos, x='Fecha', y='Humedad', title='Evolución de la Humedad Relativa', markers=True, template='plotly_dark')
    fig_hum.update_traces(line_color='#0068C9')

    fig_presion = px.line(df_datos, x='Fecha', y='Presion', title='Evolución de la Presión Atmosférica', markers=True, template='plotly_dark')
    fig_presion.update_traces(line_color='#83C9FF')

    fig_gas_line = px.line(df_datos, x='Fecha', y='Gas-Ppm', title='Evolución de la Concentración de Gas (PPM)', markers=True, template='plotly_dark')
    fig_gas_line.update_traces(line_color='#00CC96')

    # Organización en Pestañas (Tabs)
    tab1, tab2, tab3 = st.tabs(["📊 Estado Actual", "📈 Tendencias Históricas", "📋 Registros de Base de Datos"])

    with tab1:
        st.subheader("Estado actual de los sensores (En vivo)")
        renderizar_tiempo_real()
        st.subheader("🌤️ Pronóstico del Tiempo Extendido (7 Días)")

        df_clima_7d = obtener_pronostico_7_dias()

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
        modo = st.radio("¿Cómo deseas ingresar el número?", ["Elegir de la lista", "Escribir número personalizado"])
        if modo == "Elegir de la lista":
            opcion = st.selectbox("registros: ", ["todos", "100", "300", "500"], index=None, placeholder="Selecciona una opcion")
        else:
            opcion = st.number_input("Escribe cualquier número:", value=0, step=1)
        
        if opcion is not None:
            st.write(f"Has seleccionado: {opcion}")
            plot_container = st.empty()
            if opcion == "todos":
                df_datos = obtener_todos()
            else:
                df_datos = obtener_segun(int(opcion))

            with plot_container.container(): 
                progress_bar = st.progress(0, text="Calculando datos del gráfico...")
                for percent_complete in range(100):
                    time.sleep(0.01)  # Simula procesamiento rápido
                    progress_bar.progress(percent_complete + 1)
            plot_container.empty()
            st.subheader(f"Últimos {len(df_datos)} registros en la Base de Datos (Supabase)")
            st.dataframe(df_datos, use_container_width=True, hide_index=False)
        else:
            st.info("Por favor, selecciona una opción para cargar los datos.")
    
if __name__ == '__main__':
    main()
