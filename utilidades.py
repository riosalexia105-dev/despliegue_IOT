import streamlit as st

import pandas as pd
from supabase import create_client
import plotly.graph_objects as go
from datetime import datetime
import json
import numpy as np
import logging
import paho.mqtt.client as mqtt
import requests
log = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"  # API para pronósticos
RIOS_URL = "https://flood-api.open-meteo.com/v1/flood?latitude=-31.6488&longitude=-60.7087&daily=river_discharge,river_discharge_median,river_discharge_mean,river_discharge_max,river_discharge_min&past_days=7&forecast_days=7"
SUPABASE_URL = ""
SUPABASE_KEY = ""

# Coordenadas de Santa Fe Capital (Paraná/Salado)
LATITUDE = -31.6333
LONGITUDE = -60.7000

@st.cache_resource
def iniciar_servicios():
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

    client_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def on_connect(client, userdata, flags, rc, properties=None):
        log.info(f"MQTT conectado, rc={rc}")
        client.subscribe(MQTT_TOPIC)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            data = {
                "Temperatura": float(payload.get("Temperatura", 0.0)),
                "Humedad": float(payload.get("Humedad", 0.0)),
                "Presion": float(payload.get("Presion", 0.0)),
                "Fecha": payload.get("Fecha", datetime.now().isoformat()),
                "Gas-Ppm": float(payload.get("Gas-Ppm", 0.0)),
            }
            res = client_supabase.table("Lecturas").insert(data).execute()
            log.info(f"Insertado: {res.data}")
        except Exception:
            log.exception("Error procesando mensaje MQTT")

    client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # paho 2.x
    client_mqtt.username_pw_set(MQTT_USER, MQTT_PASS)
    client_mqtt.tls_set()
    client_mqtt.on_connect = on_connect
    client_mqtt.on_message = on_message
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
    return client_supabase

client_supabase = iniciar_servicios()

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

@st.cache_data(ttl=3600)  #Garda los datos en cache por 1 hora
def obtener_pronostico_7_dias():
    params = {#santa fe
        "latitude": -31.6333,
        "longitude": -60.7,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code",
        "timezone": "auto"
    }
    try:
        respuesta = requests.get(FORECAST_URL, params=params, timeout=5)
        respuesta.raise_for_status()

        daily_data = respuesta.json().get("daily", {})
        if not daily_data:
            return pd.DataFrame()

        dataframe = pd.DataFrame(daily_data).head(7)
        dataframe["time"] = pd.to_datetime(dataframe["time"])

        mapeo_codigos = {
            0: "☀️ Despejado", 1: "🌤️ Despejado", 2: "🌤️ Parcialmente Nublado", 3: "☁️ Nublado",
            45: "🌫️ Niebla", 48: "🌫️ Niebla", 51: "🌦️ Llovizna", 53: "🌦️ Llovizna", 55: "🌦️ Llovizna",
            61: "🌧️ Lluvia Débil", 63: "🌧️ Lluvia", 65: "🌧️ Lluvia Fuerte", 80: "🌧️ Chubascos",
            81: "🌧️ Chubascos", 82: "🌧️ Chubascos", 95: "⛈️ Tormenta", 96: "⛈️ Tormenta", 99: "⛈️ Tormenta"
        }
                
        dataframe["Estado"] = dataframe["weather_code"].map(mapeo_codigos).fillna("❓ Variable")
        return dataframe.rename(
            columns={
                "time": "Fecha",
                "temperature_2m_max": "Máxima (°C)",
                "temperature_2m_min": "Mínima (°C)",
                "precipitation_sum": "Cant_Precip (mm)",
                "wind_speed_10m_max": "Viento_Max (km/h)",
            }
        )[
            [
                "Fecha",
                "Máxima (°C)",
                "Mínima (°C)",
                "Cant_Precip (mm)",
                "Viento_Max (km/h)",
                "Estado",
            ]
        ]

    except Exception as e:
        st.error(f"Error al conectar con Open-Meteo: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def obtener_datos_hidro():
    url = f"https://flood-api.open-meteo.com/v1/flood?latitude={LATITUDE}&longitude={LONGITUDE}&daily=river_discharge&forecast_days=7&past_days=7"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame({
                "Fecha": pd.to_datetime(data["daily"]["time"]),
                "Caudal (m³/s)": data["daily"]["river_discharge"]
            })
            return df
    except Exception:
        pass
    
    # Fallback/Simulación en caso de no conectar a internet
    fechas = pd.date_range(end=pd.Timestamp.now(), periods=14, freq='D')
    caudales = np.random.normal(loc=12500, scale=300, size=14)
    return pd.DataFrame({"Fecha": fechas, "Caudal (m³/s)": caudales})

def generarMenu():
    with st.sidebar:
        st.page_link("app.py", label="Monitoreo Ambiental", icon=":material/thermostat:")
        st.page_link("vistas/informe_rios.py", label="Informes de Ríos", icon=":material/waves:")
        st.page_link("vistas/Pronostico.py", label="Pronostico Semanal", icon=":material/partly_cloudy_day:")
        st.page_link("vistas/admin_dashboard.py", label="Administrador", icon=":material/supervisor_account:")
        

def cargarCSS():
    # Inyección de estilos CSS
    st.markdown("""
        <style>
        header[data-testid="stHeader"] {
            background-color: #1A1C24 !important;
            border-bottom: 1px solid #00CC96 !important;
            height: 3.5rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            position: relative !important;
        }
        div[data-testid="stToolbar"] {
            position: absolute !important;
            right: 15px !important;
            z-index: 1 !important;
        }
        header[data-testid="stHeader"]::after {
            content: "Instituto Superior Domingo Guzman Silva";
            color: #ffffff !important;
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            margin-left: 140px !important;
            white-space: nowrap;
            z-index: 2 !important;
        }
        img[data-testid="stLogo"] {
            position: fixed !important;
            top: 5px !important;
            margin-left: 50px;
            height: 3rem !important;
            width: auto !important;
            z-index: 999999 !important;
        }
        section[data-testid="stSidebar"] {
            background-color: #1A1C24 !important;
        }
        section[data-testid="stSidebar"] > div {
            background-color: #1A1C24 !important;
        }
        section[data-testid="stSidebar"] img[data-testid="stLogo"] {
            position: static !important;
            height: 5rem !important;
            width: auto !important;
            margin-top: 0px !important;
            margin-bottom: 15px !important;
            margin-left: 90px !important;
        }
        [data-testid="collapsedControl"] {
            display: block !important;
            z-index: 999999 !important;
        }
        [data-testid="collapsedControl"] svg {
            fill: #00CC96 !important;
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

# Funciones para obtener datos de Supabase para los gráficos
def obtener_todos():
    try:
        res = client_supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def obtener_segun(limite: int = 50):
    try:
        res = client_supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).limit(limite).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def obtener_penultimo():
    try:
        res = client_supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha,\"Gas-Ppm\"").order("id", desc=True).limit(2).execute()
        if res.data and len(res.data) >= 2:
            return res.data[1] 
        return {}
            
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return {}

def obtener_ultimo():
    try:
        res = client_supabase.table("Lecturas").select("Temperatura, Humedad, Presion, Fecha, \"Gas-Ppm\"").order("id", desc=True).limit(1).execute()
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
