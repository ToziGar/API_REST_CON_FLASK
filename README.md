# API de Lista de Tareas

API REST construida con Flask, SQLite y autenticacion basada en tokens Bearer. Gestiona tareas por usuario, aplica validaciones estrictas y ofrece una experiencia de desarrollo completa con pruebas automatizadas.

## Descripcion general

La aplicacion permite registrar usuarios, iniciar sesion y operar sobre una lista personal de tareas pendientes. Cada peticion valida formato JSON, controla duplicados y devuelve respuestas coherentes en castellano. El almacenamiento persiste en SQLite mediante SQLAlchemy y los tokens se firman con `itsdangerous` para impedir manipulaciones.

## Caracteristicas principales

- Registro y login con passwords hasheados (Werkzeug) y tokens con caducidad configurable.
- CRUD completo de tareas vinculado al usuario autenticado.
- Validacion de negocio (longitud, duplicados, tipos de datos) y manejo centralizado de errores.
- Persistencia en `tareas.db`, lista para escalar a otras bases de datos.
- Suite de pruebas con pytest que monta una base temporal por ejecucion.

## Componentes tecnicos

- **Framework:** Flask 3
- **ORM:** Flask-SQLAlchemy sobre SQLAlchemy 2
- **Tokenizacion:** URLSafeTimedSerializer (itsdangerous)
- **Seguridad:** Hash de contrasenas con Werkzeug
- **Pruebas:** pytest con fixtures reutilizables

## Requisitos previos

- Python 3.10 o superior
- `pip` disponible (incluido con Python moderno)
- Opcional: `jq` para extraer campos JSON en ejemplos de terminal

## Instalacion

```bash
# (Opcional) crear entorno virtual
python -m venv .venv
.\.venv\Scripts\activate   # Windows PowerShell
# source .venv/bin/activate  # macOS / Linux

# Instalar dependencias
pip install -r requirements.txt
```

## Configuracion

Puedes personalizar la aplicacion mediante variables de entorno antes de ejecutarla:

- `SECRET_KEY`: clave de firma para tokens. Cambiala en produccion.
- `SQLALCHEMY_DATABASE_URI`: URI de la base de datos. Por defecto `sqlite:///tareas.db`.
- `TOKEN_MAX_AGE`: segundos de validez del token (valor por defecto 86400, 24 h).

Ejemplo:

```bash
set SECRET_KEY=clave-super-secreta
set TOKEN_MAX_AGE=7200
python app.py
```

## Ejecucion

```bash
python app.py
```

Al arrancar:

1. Se crean las tablas si no existen.
2. El servidor corre en `http://127.0.0.1:5000/` en modo debug (hot reload).
3. Las respuestas se entregan en JSON y requieren cabecera `Content-Type: application/json`.

## Autenticacion y cabeceras

1. Registra un usuario via `POST /registro`.
2. Inicia sesion via `POST /login` para obtener el token.
3. Agrega la cabecera `Authorization: Bearer <token>` en cada peticion protegida.

Si el token vence (`TOKEN_MAX_AGE`) o falta la cabecera, la API responde `401 No autorizado`.

## Endpoints disponibles

| Metodo | Ruta             | Auth | Descripcion                                                                 |
|--------|------------------|------|------------------------------------------------------------------------------|
| POST   | /registro        | No   | Crea un usuario. Necesita `nombre` y `password` en JSON.                    |
| POST   | /login           | No   | Devuelve un token Bearer si las credenciales son validas.                   |
| POST   | /tareas          | Si   | Crea una tarea (`descripcion`, opcional `completada`).                      |
| GET    | /tareas          | Si   | Lista las tareas del usuario autenticado.                                   |
| GET    | /tareas/<id>     | Si   | Recupera una tarea propia por identificador.                                |
| PUT    | /tareas/<id>     | Si   | Actualiza campos presentes en el JSON (descripcion y/o completada).        |
| DELETE | /tareas/<id>     | Si   | Elimina la tarea indicada, siempre que pertenezca al usuario autenticado.  |

## Ejemplos practicos con `curl`

### Sesion rapida

```bash
# 1. Registro
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "ana", "password": "supersecreto"}'

# 2. Login y token
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"nombre": "ana", "password": "supersecreto"}' | jq -r '.token')

# 3. Creacion de tarea
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Comprar leche"}'

# 4. Listado
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
```

### Escenario ampliado

```bash
# Usuario administrador
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "admin", "password": "cambiame123"}'

TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"nombre": "admin", "password": "cambiame123"}' | jq -r '.token')

# Crear tareas
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Redactar informe mensual"}'

curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Enviar facturas", "completada": true}'

# Listado esperado
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
# [
#   {"id":1,"descripcion":"Redactar informe mensual","completada":false},
#   {"id":2,"descripcion":"Enviar facturas","completada":true}
# ]

# Actualizar y eliminar
curl -X PUT http://127.0.0.1:5000/tareas/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completada": true}'

curl -X DELETE http://127.0.0.1:5000/tareas/2 \
  -H "Authorization: Bearer $TOKEN"

# Resultado final
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
# [{"id":1,"descripcion":"Redactar informe mensual","completada":true}]
```

### Manejo de errores

```bash
# Token faltante -> 401
curl http://127.0.0.1:5000/tareas

# Descripcion vacia -> 400
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": ""}'

# Duplicado -> 409
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Redactar informe mensual"}'
```

## Pruebas automatizadas

```bash
pytest
```

La suite realiza:

- Creacion y autenticacion de usuarios ficticios.
- Verificacion de casos positivos/negativos en CRUD.
- Reseteo de la base temporal tras cada test.

## Desarrollo y mantenimiento

- El archivo `tareas.db` puede borrarse para limpiar el estado local.
- Si vas a desplegar, desactiva `debug=True` y usa un servidor WSGI (gunicorn, waitress).
- Las advertencias de SQLAlchemy sobre `Query.get` se deben a la API heredada; se mantienen para simplicidad en esta version.

---

Esta documentacion cubre todo lo necesario para ejecutar, probar y comprender la arquitectura del proyecto. Ajusta la configuracion y extiende la API segun tus necesidades.
