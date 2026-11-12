import streamlit as st
import utilidades as util

st.set_page_config(
    page_title="Monitoreo Ambiental IoT",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

util.cargarCSS()
util.generarMenu()

import plotly.express as px
import pandas as pd

def main():
    st.title("🌱 Sistema de Monitoreo Ambiental ESP32")
    st.markdown("Visualización en tiempo real conectada mediante **MQTT (HiveMQ)** y almacenamiento en **Supabase**.")

    df_datos = util.obtener_segun(50)
    
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
        util.renderizar_tiempo_real()

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
        with st.popover("Elige una opción..."):
            opcion = st.pills(
                "Selecciona una opcion:",
                options=["Todos", "100", "300", "500"],
                selection_mode="single"
            )
            
        if opcion is not None:
            st.write(f"Has seleccionado: {opcion}")
            plot_container = st.empty()
            if opcion == "Todos":
                df_datos = util.obtener_todos()
            else:
                df_datos = util.obtener_segun(int(opcion))

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
