import streamlit as st

def generarMenu():
    with st.sidebar:
        st.page_link("pages/informe_rios.py", label="Informes de Ríos", icon="🌊")
