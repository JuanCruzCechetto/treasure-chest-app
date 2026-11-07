"""Acceso a la base SQLite: conexión y creación de tablas."""
import os
import sqlite3

from flask import g

RUTA_DB = os.environ.get("BASE_DE_DATOS",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "gastos.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL UNIQUE,
    hash_clave    TEXT    NOT NULL,
    token_hash    TEXT,
    creado        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gastos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    descripcion   TEXT    NOT NULL,
    monto         REAL    NOT NULL CHECK (monto > 0),
    categoria     TEXT    NOT NULL,
    fecha         TEXT    NOT NULL
);
"""


def obtener_db():
    """Devuelve una conexión por pedido (se guarda en g)."""
    if "db" not in g:
        g.db = sqlite3.connect(RUTA_DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def cerrar_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def inicializar_db():
    """Crea las tablas si no existen. Los datos persisten entre reinicios."""
    con = sqlite3.connect(RUTA_DB)
    try:
        con.executescript(ESQUEMA)
        # Bases creadas antes de que existiera el tablero publicado
        columnas = [fila[1] for fila in con.execute("PRAGMA table_info(usuarios)")]
        if "token_hash" not in columnas:
            con.execute("ALTER TABLE usuarios ADD COLUMN token_hash TEXT")
            con.commit()
    finally:
        con.close()
