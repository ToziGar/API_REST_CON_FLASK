# API de Lista de Tareas

API REST construida con Flask, SQLite y autenticacion mediante tokens firmados. Gestiona tareas por usuario y cubre el ciclo CRUD completo con validaciones de negocio.

## Caracteristicas

- Registro y login con passwords hasheados y tokens Bearer.
- CRUD de tareas asociado al usuario autenticado, con control de duplicados y limite de longitud.
- Persistencia real en SQLite gracias a SQLAlchemy, lista para migrar a otras bases.
- Respuestas JSON uniformes con manejo centralizado de errores.
- Suite de pruebas automatizadas con pytest sobre una base temporal.

## Requisitos

- Python 3.10 o superior
- Entorno virtual recomendado (por ejemplo, `venv`)

Instala dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python app.py
```

La aplicacion arranca en `http://127.0.0.1:5000/` en modo debug y crea el archivo `tareas.db` con las tablas necesarias si aun no existe.

### Flujo rapido con `curl`

```bash
# 1. Registrar usuario
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "ana", "password": "supersecreto"}'

# 2. Obtener token
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"nombre": "ana", "password": "supersecreto"}' | jq -r '.token')

# 3. Crear tarea autenticada
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Comprar leche"}'

# 4. Listar tareas del usuario
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
```

### Escenario completo paso a paso

```bash
# 1. Registrar al usuario principal
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "admin", "password": "cambiame123"}'

# 2. Iniciar sesion y guardar token
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"nombre": "admin", "password": "cambiame123"}' | jq -r '.token')

# 3. Crear varias tareas
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Redactar informe mensual"}'

curl -X POST http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Enviar facturas", "completada": true}'

# 4. Consultar la lista
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
# Respuesta esperada:
# [
#   {"id":1,"descripcion":"Redactar informe mensual","completada":false},
#   {"id":2,"descripcion":"Enviar facturas","completada":true}
# ]

# 5. Actualizar la primera tarea
curl -X PUT http://127.0.0.1:5000/tareas/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completada": true}'

# 6. Eliminar la segunda tarea
curl -X DELETE http://127.0.0.1:5000/tareas/2 \
  -H "Authorization: Bearer $TOKEN"

# 7. Verificar el estado final
curl http://127.0.0.1:5000/tareas \
  -H "Authorization: Bearer $TOKEN"
# Respuesta esperada:
# [
#   {"id":1,"descripcion":"Redactar informe mensual","completada":true}
# ]
```

## Pruebas

```bash
pytest
```

Las pruebas levantan una base SQLite temporal, validan autenticacion y aseguran la logica de negocio de los endpoints.

## Endpoints

- `POST /registro`: crea un nuevo usuario. Requiere `nombre` y `password`.
- `POST /login`: devuelve un token Bearer para el usuario autenticado.
- `POST /tareas`: crea una tarea (requiere token). Cuerpo ejemplo:
  ```json
  {
    "descripcion": "Comprar leche",
    "completada": false
  }
  ```
- `GET /tareas`: lista las tareas del usuario autenticado.
- `GET /tareas/<id>`: devuelve la tarea indicada si pertenece al usuario.
- `PUT /tareas/<id>`: actualiza descripcion y/o estado de una tarea propia.
- `DELETE /tareas/<id>`: elimina una tarea del usuario.

## Notas

- El almacenamiento se maneja mediante una clase `TaskStore`, lo que facilita migrar a otra persistencia.
- Se valida la longitud maxima de la descripcion y se impiden duplicados (codigo 409).
- El almacenamiento es solo en memoria, por lo que se vacia al reiniciar la aplicacion.
- Las respuestas de error incluyen mensajes descriptivos en formato JSON.

## Futuras mejoras sugeridas

- Anadir autenticacion y separar tareas por usuario.
- Incorporar persistencia real con SQLite/PostgreSQL y SQLAlchemy.
- Documentar la API con OpenAPI/Swagger y exponer un playground interactivo.
- Desplegar con Docker y configurar un servidor WSGI (gunicorn o waitress) para produccion.
