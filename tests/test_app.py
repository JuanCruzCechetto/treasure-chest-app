"""python -m pytest"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta

import pytest
import requests

os.environ["SECRET_KEY"] = "clave-solo-para-pruebas"
os.environ["BASE_DE_DATOS"] = os.path.join(tempfile.mkdtemp(), "prueba.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as modulo  # noqa: E402
import db as modulo_db  # noqa: E402

HOY = date.today().isoformat()
CLAVE = "secreta123"


@pytest.fixture
def cliente():
    modulo.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    modulo_db.inicializar_db()
    con = sqlite3.connect(modulo_db.RUTA_DB)
    con.executescript("DELETE FROM gastos; DELETE FROM usuarios; DELETE FROM sqlite_sequence;")
    con.close()
    return modulo.app.test_client()


def registrar(cliente, nombre="ana"):
    cliente.post("/registro", data={"nombre": nombre, "clave": CLAVE, "confirmar": CLAVE})
    return cliente.post("/login", data={"nombre": nombre, "clave": CLAVE})


def cargar(cliente, **campos):
    datos = {"descripcion": "Pan", "monto": "1500.50", "categoria": "Comida", "fecha": HOY}
    datos.update(campos)
    return cliente.post("/gastos", data=datos)


def token_de(cliente):
    html = cliente.post("/tablero").get_data(as_text=True)
    return html.split('<code class="token">')[1].split("</code>")[0]


def test_sin_sesion_redirige_al_login(cliente):
    respuesta = cliente.get("/gastos")
    assert respuesta.status_code == 302 and "/login" in respuesta.location


def test_contrasena_guardada_como_resumen(cliente):
    registrar(cliente)
    with modulo.app.app_context():
        fila = modulo.obtener_db().execute("SELECT hash_clave FROM usuarios").fetchone()
    assert CLAVE not in fila["hash_clave"]


@pytest.mark.parametrize("campos", [
    {"descripcion": "  "},
    {"monto": "-5"},
    {"monto": "0"},
    {"monto": "abc"},
    {"monto": "nan"},
    {"monto": "inf"},
    {"categoria": "Inventada"},
    {"fecha": "no-es-fecha"},
    {"fecha": (date.today() + timedelta(days=1)).isoformat()},
])
def test_el_servidor_rechaza_datos_invalidos(cliente, campos):
    registrar(cliente)
    assert cargar(cliente, **campos).status_code == 400
    with modulo.app.app_context():
        assert modulo.obtener_db().execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 0


def test_no_se_puede_tocar_un_gasto_ajeno(cliente):
    registrar(cliente)
    cargar(cliente)
    cliente.post("/logout")
    registrar(cliente, nombre="beto")
    assert cliente.get("/gastos/1/editar").status_code == 404
    cliente.post("/gastos/1/borrar")
    assert cliente.get("/api/gastos").get_json()["gastos"] == []
    cliente.post("/logout")
    registrar(cliente)
    assert len(cliente.get("/api/gastos").get_json()["gastos"]) == 1


def test_api_exige_autenticacion_y_el_token_ve_solo_lo_suyo(cliente, monkeypatch):
    monkeypatch.setattr(modulo, "cotizacion_dolar", lambda: None)
    assert cliente.get("/api/gastos").status_code == 401
    assert cliente.get("/api/gastos", headers={"Authorization": "Bearer inventado"}).status_code == 401
    registrar(cliente)
    cargar(cliente)
    token = token_de(cliente)
    cliente.post("/logout")
    registrar(cliente, nombre="beto")
    cargar(cliente, descripcion="De Beto")
    cliente.post("/logout")
    datos = cliente.get("/api/gastos", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert [g["descripcion"] for g in datos["gastos"]] == ["Pan"]


def test_token_nuevo_anula_el_anterior(cliente, monkeypatch):
    monkeypatch.setattr(modulo, "cotizacion_dolar", lambda: None)
    registrar(cliente)
    viejo = token_de(cliente)
    nuevo = token_de(cliente)
    cliente.post("/logout")
    assert cliente.get("/api/gastos", headers={"Authorization": f"Bearer {viejo}"}).status_code == 401
    assert cliente.get("/api/gastos", headers={"Authorization": f"Bearer {nuevo}"}).status_code == 200


def test_logout_no_funciona_por_get(cliente):
    registrar(cliente)
    assert cliente.get("/logout").status_code == 405
    assert cliente.get("/gastos").status_code == 200


def test_csrf_rechaza_formularios_sin_token(cliente):
    modulo.app.config.update(WTF_CSRF_ENABLED=True)
    try:
        assert cliente.post("/login", data={"nombre": "ana", "clave": CLAVE}).status_code == 400
    finally:
        modulo.app.config.update(WTF_CSRF_ENABLED=False)


def test_si_el_dolar_falla_la_pagina_funciona_igual(cliente, monkeypatch):
    def falla(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr(modulo.requests, "get", falla)
    registrar(cliente)
    cargar(cliente)
    respuesta = cliente.get("/gastos")
    assert respuesta.status_code == 200
    assert "Cotización no disponible" in respuesta.get_data(as_text=True)
