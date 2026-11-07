"""Tablero de datos con Streamlit y Pandas.

Ejecutar con:  streamlit run tablero/dashboard.py
Se publica aparte de la app Flask, así que lee los datos de su JSON con un token personal.
Cada usuario ve solo sus propios gastos.
"""
import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Treasure Chest App · Tablero", layout="wide")
st.title("Treasure Chest App — Tablero de gastos")


@st.cache_data(ttl=30, show_spinner="Trayendo tus gastos...")
def cargar_datos(url_app, token):
    respuesta = requests.get(url_app.rstrip("/") + "/api/gastos",
                             headers={"Authorization": f"Bearer {token}"}, timeout=8)
    respuesta.raise_for_status()
    return respuesta.json()


st.sidebar.header("Conexión")
url_app = st.sidebar.text_input("Dirección de la aplicación", value=os.environ.get("URL_APP", ""))
token = st.sidebar.text_input("Token personal", type="password",
                              help="Lo generás en la página Tablero de la aplicación.")

if not url_app or not token:
    st.info("Escribí la dirección de la aplicación y tu token en el panel de la izquierda.")
    st.stop()

try:
    respuesta = cargar_datos(url_app, token)
except requests.HTTPError as error:
    if error.response.status_code == 401:
        st.error("El token no es válido. Generá uno nuevo en la aplicación.")
    else:
        st.error("La aplicación respondió con un error. Probá de nuevo en un rato.")
    st.stop()
except (requests.RequestException, ValueError):
    st.error("No se pudo conectar con la aplicación. Revisá la dirección o probá de nuevo en un rato.")
    st.stop()

df = pd.DataFrame(respuesta["gastos"])
if df.empty:
    st.info("Todavía no hay gastos cargados.")
    st.stop()
df["fecha"] = pd.to_datetime(df["fecha"])

# Filtros
st.sidebar.header("Filtros")
desde, hasta = df["fecha"].min().date(), df["fecha"].max().date()
rango = st.sidebar.date_input("Período", (desde, hasta), min_value=desde, max_value=hasta)
datos = df
if isinstance(rango, tuple) and len(rango) == 2:
    datos = df[(df["fecha"].dt.date >= rango[0]) & (df["fecha"].dt.date <= rango[1])]


def pesos(valor):
    return f"$ {valor:,.0f}".replace(",", ".")


# Indicadores
c1, c2, c3 = st.columns(3)
c1.metric("Total gastado", pesos(datos["monto"].sum()))
c2.metric("Cantidad de gastos", len(datos))
c3.metric("Gasto promedio", pesos(datos["monto"].mean()) if len(datos) else "—")

# Gráficos: negro en modo día y blanco en modo noche
COLOR = "#ffffff" if st.context.theme.type == "dark" else "#000000"
izq, der = st.columns(2)
with izq:
    st.subheader("Por categoría")
    por_cat = datos.groupby("categoria")["monto"].sum().sort_values(ascending=False)
    st.bar_chart(por_cat, color=COLOR, sort=False)
with der:
    st.subheader("Por mes")
    por_mes = datos.groupby(datos["fecha"].dt.to_period("M").astype(str))["monto"].sum()
    st.line_chart(por_mes, color=COLOR)

st.subheader("Detalle")
st.dataframe(datos.sort_values("fecha", ascending=False), width="stretch", hide_index=True)
