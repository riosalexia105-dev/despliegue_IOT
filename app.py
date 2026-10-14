import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Monitoreo Ambiental ESP32",
    page_icon="🌡️",
    layout="wide"
)

# Cargar credenciales de manera segura con respaldo local
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = "https://etujhhaffatmobyaqftd.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0dWpoaGFmZmF0bW9ieWFxZnRkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNjM1ODgsImV4cCI6MjEwMTczOTU4OH0.KR9j-mFO9RTQCtbusbvBnOh3TQaKy3fKVH1y71s4qNM"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Funciones para obtener datos de Supabase
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
    st.markdown("Visualización de variables ambientales almacenadas en Supabase en tiempo real.")

    # Botón para actualizar datos manualmente
    if st.button("🔄 Actualizar Datos"):
        st.rerun()

    df_datos = obtener_segun(50)
    df_ultimo = obtener_ultimo()

    if df_datos.empty or df_ultimo.empty:
        st.warning("⚠️ No se encontraron registros en la tabla 'Lecturas' de Supabase.")
        st.stop()

    # Asegurar orden cronológico ascendente para los gráficos
    if "Fecha" in df_datos.columns:
        df_datos["Fecha"] = pd.to_datetime(df_datos["Fecha"])
        df_datos = df_datos.sort_values("Fecha", ascending=True)

    # Extraer valores actuales
    gas_actual = float(df_ultimo["Gas-Ppm"].iloc[0]) if "Gas-Ppm" in df_ultimo.columns else 0.0
    temp_actual = float(df_ultimo["Temperatura"].iloc[0]) if "Temperatura" in df_ultimo.columns else 0.0
    hum_actual = float(df_ultimo["Humedad"].iloc[0]) if "Humedad" in df_ultimo.columns else 0.0
    presion_actual = float(df_ultimo["Presion"].iloc[0]) if "Presion" in df_ultimo.columns else 0.0

    # Crear gráficos bonitos e interactivos con Plotly
    fig_temp = px.line(df_datos, x='Fecha', y='Temperatura', title='Evolución de la Temperatura', markers=True, template='plotly_dark')
    fig_temp.update_traces(line_color='#FF4B4B')

    fig_hum = px.line(df_datos, x='Fecha', y='Humedad', title='Evolución de la Humedad Relativa', markers=True, template='plotly_dark')
    fig_hum.update_traces(line_color='#0068C9')

    fig_presion = px.line(df_datos, x='Fecha', y='Presion', title='Evolución de la Presión Atmosférica', markers=True, template='plotly_dark')
    fig_presion.update_traces(line_color='#83C9FF')

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

    with tab2:
        st.subheader("Evolución temporal de variables climáticas")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.plotly_chart(fig_temp, use_container_width=True)
        with col2:
            st.plotly_chart(fig_hum, use_container_width=True)
        with col3:
            st.plotly_chart(fig_presion, use_container_width=True)

    with tab3:
        st.subheader(f"Últimos {len(df_datos)} registros en la Base de Datos")
        st.dataframe(df_datos, use_container_width=True)

if __name__ == '__main__':
    main()