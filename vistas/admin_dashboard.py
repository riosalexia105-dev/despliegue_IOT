import streamlit as st
import utilidades as util

util.cargarCSS()

microcontroladores = [
    "ESP32_preceptoria",
    "ESP32_sucucho",
    "ESP32_s9",
    "ESP32_s8",
    "ESP32_rosadita",
]

def verificar_admin(user_id: str) -> bool:
    try:
        res = (
            util.client_supabase.table("profiles")
            .select("is_admin")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return res.data.get("is_admin", False) if res.data else False
    except Exception:
        return False

if "user" not in st.session_state:
    st.title("Acceso Restringido - Panel Admin")
    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        try:
            auth_res = util.client_supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user = auth_res.user

            if user and verificar_admin(user.id):
                st.session_state["user"] = user
                st.rerun()
            else:
                util.client_supabase.auth.sign_out()
                st.error("Acceso denegado. No tienes permisos de administrador.")
        except Exception as e:
            st.error(f"Credenciales incorrectas. {e}")
else:
    st.sidebar.success(f"Admin: {st.session_state['user'].email}")
    if st.sidebar.button("Cerrar sesión"):
        util.client_supabase.auth.sign_out()
        del st.session_state["user"]
        st.rerun()

    st.title("Panel de Control")
    st.write("Bienvenido al área de administración.")

    st.write(f"Valores de sala: {microcontroladores[1]}")
    df_ultimo_vivo = util.obtener_ultimo()
    penultimo = util.obtener_penultimo()

    if not df_ultimo_vivo.empty:
        temp_vivo = df_ultimo_vivo["Temperatura"].iloc[0]
        hum_vivo = df_ultimo_vivo["Humedad"].iloc[0]
        presion_vivo = df_ultimo_vivo["Presion"].iloc[0]
        fecha_iso_raw = df_ultimo_vivo["Fecha"].iloc[0]
        gas_vivo = df_ultimo_vivo["Gas-Ppm"].iloc[0]

        deltaTemp = temp_vivo - penultimo["Temperatura"]
        deltaHum = hum_vivo - penultimo["Humedad"]
        deltaPres = presion_vivo - penultimo["Presion"]
        deltaGas = gas_vivo - penultimo["Gas-Ppm"]

        df_rios = util.obtener_datos_hidro()

        caudal_actual = df_rios["Caudal (m³/s)"].iloc[-1]
        caudal_previo = df_rios["Caudal (m³/s)"].iloc[-2]
        variacion = caudal_actual - caudal_previo

        altura_estimada = round(caudal_actual / 3500, 2)

        st.markdown(
            """
            <style>
                div[data-testid="stMetric"] {
                    padding: 12px; 
                    border-radius: 8px;
                    border: 1px solid #00CC96;
                }
                div[data-testid="stMetricValue"] {
                    text-align: center;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric(label="Temperatura", value=f"{penultimo['Temperatura']} C°", delta=deltaTemp)
        with col2:
            st.metric(label="Humedad", value=f"{penultimo['Humedad']} %",delta=int(deltaHum))
        with col3:
            st.metric(label="Presion", value=f"{penultimo['Presion']} hPa", delta=deltaPres)
        with col4:
            st.metric(label="Gas-Ppm", value=f"{penultimo['Gas-Ppm']} PPM", delta=int(deltaGas))
        with col5:
            estado = (
                "NORMAL"
                if altura_estimada < 4.3
                else ("ALERTA" if altura_estimada < 5.3 else "EVACUACIÓN")
            )
            st.metric(label="⚠️ Estado Hidrométrico", value=estado, delta=f"{round(variacion / 3500, 2):+} m")
    else:
        st.warning("No hay lecturas en tiempo real disponibles.")

    st.subheader("Controladores: ")
    st.markdown(
        """
        <style>
            /* Bloquea el cursor en los selectbox*/
            div[data-baseweb="select"] input {
                caret-color: transparent !important;
                pointer-events: none !important;
            }
            /* Agranda los st.toggle */
            div[data-testid="stCheckbox"] label > div:first-child {
                transform: scale(1.3);
                margin-right: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    opcion = st.selectbox("Selecciona un microcontrolador", microcontroladores)

    st.write("Elegiste:", opcion)
    with st.container():
        col1, col2 = st.columns([2, 5], vertical_alignment="center")
        with col1:
            opcionLuz = st.toggle(f"Encender Luz en {opcion}", key=f"luz_{opcion}")
        with col2:
            if opcionLuz:
                st.write("La Luz está encendida.")
            else:
                st.write("La Luz está apagada.")

        col1, col2 = st.columns([2, 5], vertical_alignment="center")
        with col1:
            opcionVentilador = st.toggle(f"Encender ventilador en {opcion}", key=f"ven_{opcion}")
        with col2:
            if opcionVentilador:
                st.write("El ventilador está encendido.")
            else:
                st.write("El ventilador está apagado.")

        col1, col2 = st.columns([2, 5], vertical_alignment="center")
        with col1:
            opcionAire = st.toggle(f"Encender Aire Acondicionado en {opcion}", key=f"aire_{opcion}")
        with col2:
            if opcionAire:
                st.write("El Aire Acondicionado está encendido.")
            else:
                st.write("El Aire Acondicionado está apagado.")
