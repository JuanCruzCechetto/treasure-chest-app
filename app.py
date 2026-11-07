"""Treasure Chest App: gastos personales."""
import hashlib
import os
import re
import secrets
from datetime import date
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from db import cerrar_db, inicializar_db, obtener_db

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
CSRFProtect(app)
app.teardown_appcontext(cerrar_db)
inicializar_db()

CATEGORIAS = ["Comida", "Transporte", "Servicios", "Salud", "Ocio", "Educación", "Otros"]
URL_DOLAR = os.getenv("URL_DOLAR", "https://dolarapi.com/v1/dolares/oficial")


# utilidades
def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Tenés que iniciar sesión.", "error")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def validar_gasto(form):
    """Devuelve (datos, errores)."""
    errores = {}
    descripcion = form.get("descripcion", "").strip()
    monto_txt = form.get("monto", "").strip().replace(",", ".")
    categoria = form.get("categoria", "")
    fecha_txt = form.get("fecha", "").strip()

    if not 1 <= len(descripcion) <= 100:
        errores["descripcion"] = "La descripción es obligatoria (máx. 100 caracteres)."

    monto = None
    try:
        monto = round(float(monto_txt), 2)
        if not monto > 0 or monto > 100_000_000:  # not > tambien descarta NaN
            errores["monto"] = "El monto tiene que ser mayor a 0."
    except ValueError:
        errores["monto"] = "El monto tiene que ser un número."

    if categoria not in CATEGORIAS:
        errores["categoria"] = "Elegí una categoría válida."

    try:
        fecha = date.fromisoformat(fecha_txt)
        if fecha > date.today():
            errores["fecha"] = "La fecha no puede ser futura."
    except ValueError:
        errores["fecha"] = "Fecha inválida."

    datos = {"descripcion": descripcion, "monto": monto,
             "categoria": categoria, "fecha": fecha_txt}
    return datos, errores


def cotizacion_dolar():
    """Cotizacion oficial (venta). None si la API falla o no responde."""
    try:
        r = requests.get(URL_DOLAR, timeout=3)
        r.raise_for_status()
        venta = float(r.json()["venta"])
        return venta if venta > 0 else None
    except (requests.exceptions.RequestException, KeyError, ValueError, TypeError):
        return None


# rutas
@app.route("/")
def inicio():
    return render_template("inicio.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    errores, nombre = {}, ""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        clave = request.form.get("clave", "")
        confirmar = request.form.get("confirmar", "")

        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", nombre):
            errores["nombre"] = "Entre 3 y 20 caracteres: letras, números o guion bajo."
        if len(clave) < 8:
            errores["clave"] = "La contraseña debe tener al menos 8 caracteres."
        if clave != confirmar:
            errores["confirmar"] = "Las contraseñas no coinciden."

        db = obtener_db()
        if not errores and db.execute("SELECT 1 FROM usuarios WHERE nombre = ?", (nombre,)).fetchone():
            errores["nombre"] = "Ese nombre de usuario ya existe."

        if not errores:
            db.execute("INSERT INTO usuarios (nombre, hash_clave) VALUES (?, ?)",
                       (nombre, generate_password_hash(clave)))
            db.commit()
            flash("Cuenta creada. Ya podés iniciar sesión.", "ok")
            return redirect(url_for("login"))
    return render_template("registro.html", errores=errores, nombre=nombre), (400 if errores else 200)


@app.route("/login", methods=["GET", "POST"])
def login():
    error, nombre = None, ""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        clave = request.form.get("clave", "")
        usuario = obtener_db().execute(
            "SELECT * FROM usuarios WHERE nombre = ?", (nombre,)).fetchone()
        if usuario and check_password_hash(usuario["hash_clave"], clave):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["nombre"] = usuario["nombre"]
            return redirect(url_for("gastos"))
        error = "Usuario o contraseña incorrectos."
    return render_template("login.html", error=error, nombre=nombre), (401 if error else 200)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("inicio"))


@app.route("/gastos", methods=["GET", "POST"])
@login_requerido
def gastos():
    db = obtener_db()
    uid = session["usuario_id"]
    errores, datos = {}, {"fecha": date.today().isoformat()}

    if request.method == "POST":
        datos, errores = validar_gasto(request.form)
        if not errores:
            db.execute("INSERT INTO gastos (usuario_id, descripcion, monto, categoria, fecha) "
                       "VALUES (?, ?, ?, ?, ?)",
                       (uid, datos["descripcion"], datos["monto"], datos["categoria"], datos["fecha"]))
            db.commit()
            flash("Gasto agregado.", "ok")
            return redirect(url_for("gastos"))

    filas = db.execute("SELECT * FROM gastos WHERE usuario_id = ? ORDER BY fecha DESC, id DESC",
                       (uid,)).fetchall()
    total = sum(f["monto"] for f in filas)
    dolar = cotizacion_dolar()
    return render_template("gastos.html", gastos=filas, total=total, dolar=dolar,
                           categorias=CATEGORIAS, errores=errores, datos=datos), (400 if errores else 200)


@app.route("/gastos/<int:gasto_id>/editar", methods=["GET", "POST"])
@login_requerido
def editar_gasto(gasto_id):
    db = obtener_db()
    gasto = db.execute("SELECT * FROM gastos WHERE id = ? AND usuario_id = ?",
                       (gasto_id, session["usuario_id"])).fetchone()
    if gasto is None:
        return render_template("error.html", codigo=404, mensaje="Ese gasto no existe."), 404

    errores, datos = {}, dict(gasto)
    if request.method == "POST":
        datos, errores = validar_gasto(request.form)
        if not errores:
            db.execute("UPDATE gastos SET descripcion=?, monto=?, categoria=?, fecha=? WHERE id=?",
                       (datos["descripcion"], datos["monto"], datos["categoria"], datos["fecha"], gasto_id))
            db.commit()
            flash("Gasto actualizado.", "ok")
            return redirect(url_for("gastos"))
    return render_template("editar.html", gasto_id=gasto_id, datos=datos,
                           categorias=CATEGORIAS, errores=errores), (400 if errores else 200)


@app.route("/gastos/<int:gasto_id>/borrar", methods=["POST"])
@login_requerido
def borrar_gasto(gasto_id):
    db = obtener_db()
    db.execute("DELETE FROM gastos WHERE id = ? AND usuario_id = ?", (gasto_id, session["usuario_id"]))
    db.commit()
    flash("Gasto eliminado.", "ok")
    return redirect(url_for("gastos"))


# tablero
def resumen_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


@app.route("/tablero", methods=["GET", "POST"])
@login_requerido
def tablero():
    """Genera un token nuevo para el tablero. Se guarda solo el hash."""
    token = None
    if request.method == "POST":
        token = secrets.token_urlsafe(32)
        db = obtener_db()
        db.execute("UPDATE usuarios SET token_hash = ? WHERE id = ?",
                   (resumen_token(token), session["usuario_id"]))
        db.commit()
    return render_template("tablero.html", token=token, url_tablero=os.getenv("URL_TABLERO", ""),
                           url_app=request.host_url.rstrip("/"))


# api
def usuario_por_token():
    """id del usuario segun el header Authorization, o None."""
    encabezado = request.headers.get("Authorization", "")
    if not encabezado.startswith("Bearer "):
        return None
    fila = obtener_db().execute("SELECT id FROM usuarios WHERE token_hash = ?",
                                (resumen_token(encabezado[len("Bearer "):]),)).fetchone()
    return fila["id"] if fila else None


@app.route("/api/gastos")
def api_gastos():
    """Gastos del usuario (token o sesion). La usa el tablero."""
    uid = usuario_por_token() or session.get("usuario_id")
    if uid is None:
        return jsonify({"error": "No autorizado"}), 401
    filas = obtener_db().execute(
        "SELECT descripcion, monto, categoria, fecha FROM gastos WHERE usuario_id = ? ORDER BY fecha",
        (uid,)).fetchall()
    return jsonify({"gastos": [dict(f) for f in filas], "dolar": cotizacion_dolar()})


@app.route("/api/resumen")
@login_requerido
def api_resumen():
    """Total y gasto por categoria."""
    filas = obtener_db().execute(
        "SELECT categoria, ROUND(SUM(monto), 2) AS total, COUNT(*) AS cantidad "
        "FROM gastos WHERE usuario_id = ? GROUP BY categoria ORDER BY total DESC",
        (session["usuario_id"],)).fetchall()
    total = round(sum(f["total"] for f in filas), 2)
    dolar = cotizacion_dolar()
    return jsonify({
        "usuario": session["nombre"],
        "total_ars": total,
        "total_usd": round(total / dolar, 2) if dolar else None,
        "cotizacion_disponible": dolar is not None,
        "por_categoria": [dict(f) for f in filas],
    })


# errores
@app.errorhandler(CSRFError)
def error_csrf(_e):
    return render_template("error.html", codigo=400,
                           mensaje="El formulario venció. Volvé atrás, recargá la página e intentá de nuevo."), 400


@app.errorhandler(404)
def no_encontrado(_e):
    return render_template("error.html", codigo=404, mensaje="La página no existe."), 404


@app.errorhandler(500)
def error_servidor(_e):
    return render_template("error.html", codigo=500, mensaje="Error interno del servidor."), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
