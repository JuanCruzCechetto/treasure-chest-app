# Treasure Chest App — gestor de gastos personales

App web en Flask (con modo día y modo noche) para registrar gastos, ver el total en pesos y en dólares (cotización oficial
de DolarAPI) y analizarlos en un tablero de Streamlit + Pandas.

## Cómo correrla en local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # en Windows: copy .env.example .env  (y editar SECRET_KEY)
python app.py               # http://127.0.0.1:5000

# Tablero, en otra terminal y con sus propias dependencias
pip install -r tablero/requirements.txt
streamlit run tablero/dashboard.py  # http://localhost:8501; el token se genera en /tablero
```

Para generar una SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`

## Cómo cumple la consigna

| Requisito | Dónde |
|---|---|
| Flask + entorno virtual + dependencias | `requirements.txt`, `.venv` (no se entrega) |
| Al menos 4 rutas | `/`, `/registro`, `/login`, `/logout`, `/gastos`, `/gastos/<id>/editar`, `/gastos/<id>/borrar`, `/tablero`, `/api/resumen`, `/api/gastos` |
| Plantillas Jinja2 que heredan de una base | `templates/base.html` + `{% extends %}` en todas |
| Validación en el servidor y en el cliente | `validar_gasto()` y `registro()` en `app.py`; `static/validacion.js` |
| SQLite persistente | `db.py` → `gastos.db` |
| Registro/login con contraseña hasheada | `generate_password_hash` / `check_password_hash` (scrypt, Werkzeug) |
| Endpoint propio que devuelve JSON | `GET /api/resumen` y `GET /api/gastos` |
| Servicio externo con `requests` + manejo de falla/demora | `cotizacion_dolar()`: `timeout=3`, captura errores y la app sigue andando |
| Opción elegida: tablero Streamlit + Pandas | `tablero/dashboard.py`, lee `/api/gastos` con un token personal |
| Claves fuera del código | `.env` (en `.gitignore`), plantilla en `.env.example` |

## Publicarla (PythonAnywhere, cuenta gratuita)

1. Subir el código (clonando el repo desde una consola Bash de PythonAnywhere).
2. `mkvirtualenv --python=python3.12 cc && pip install -r requirements.txt`
3. Web → Add a new web app → Manual configuration → misma versión de Python.
4. En *Virtualenv* poner la ruta del entorno; en el archivo WSGI:
   ```python
   import sys
   sys.path.insert(0, "/home/TU_USUARIO/cuentas-claras")
   from app import app as application
   ```
5. Crear el `.env` en la carpeta del proyecto con la SECRET_KEY y recargar.

La base SQLite queda en disco, así que los datos sobreviven a los reinicios.
Ojo: las cuentas gratuitas restringen los sitios externos a una lista permitida; si DolarAPI no
está en esa lista, la app igual funciona y muestra "Cotización no disponible" (es justamente
el manejo de falla que pide la consigna).

