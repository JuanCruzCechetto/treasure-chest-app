"""Tablero de datos con Streamlit y Pandas.

Ejecutar con:  streamlit run dashboard.py
Lee la misma base SQLite que usa la app Flask.
"""
import sqlite3

import pandas as pd
import streamlit as st

from db import RUTA_DB

st.set_page_config(page_title="Treasure Chest App · Tablero", page_icon="static/favicon.svg", layout="wide")
st.title("Treasure Chest App — Tablero de gastos")


@st.cache_data(ttl=30)
def cargar_datos():
    with sqlite3.connect(RUTA_DB) as con:
        return pd.read_sql_query(
            "SELECT g.id, u.nombre AS usuario, g.descripcion, g.monto, g.categoria, g.fecha "
            "FROM gastos g JOIN usuarios u ON u.id = g.usuario_id",
            con, parse_dates=["fecha"])


df = cargar_datos()
if df.empty:
    st.info("Todavía no hay gastos cargados.")
    st.stop()

# Filtros
usuarios = sorted(df["usuario"].unique())
usuario = st.sidebar.selectbox("Usuario", usuarios)
datos = df[df["usuario"] == usuario]

desde, hasta = datos["fecha"].min().date(), datos["fecha"].max().date()
rango = st.sidebar.date_input("Período", (desde, hasta), min_value=desde, max_value=hasta)
if isinstance(rango, tuple) and len(rango) == 2:
    datos = datos[(datos["fecha"].dt.date >= rango[0]) & (datos["fecha"].dt.date <= rango[1])]

# Indicadores
c1, c2, c3 = st.columns(3)
c1.metric("Total gastado", f"$ {datos['monto'].sum():,.2f}")
c2.metric("Cantidad de gastos", len(datos))
c3.metric("Gasto promedio", f"$ {datos['monto'].mean():,.2f}" if len(datos) else "—")

# Gráficos
izq, der = st.columns(2)
with izq:
    st.subheader("Por categoría")
    por_cat = datos.groupby("categoria")["monto"].sum().sort_values(ascending=False)
    st.bar_chart(por_cat)
with der:
    st.subheader("Por mes")
    por_mes = datos.groupby(datos["fecha"].dt.to_period("M").astype(str))["monto"].sum()
    st.line_chart(por_mes)

st.subheader("Detalle")
st.dataframe(datos.drop(columns=["id", "usuario"]).sort_values("fecha", ascending=False),
             width="stretch", hide_index=True)
