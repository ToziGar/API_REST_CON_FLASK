# API de Lista de Tareas

API sencilla construida con Flask para gestionar tareas pendientes en memoria. Permite demostrar el ciclo CRUD completo, validaciones de negocio basicas y la separacion de responsabilidades mediante un almacen dedicado.

## Caracteristicas

- CRUD completo de tareas con respuesta JSON consistente.
- Validacion de longitud maxima y deteccion de duplicados (respuesta `409 Conflict`).
- Almacenamiento en memoria encapsulado en la clase `TaskStore`.
- Manejo centralizado de errores con mensajes descriptivos.

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

La aplicacion se inicia en `http://127.0.0.1:5000/` en modo debug.

### Ejemplo rapido con `curl`

```bash
# Crear tarea
curl -X POST http://127.0.0.1:5000/tareas \
  -H "Content-Type: application/json" \
  -d '{"descripcion": "Comprar leche"}'

# Listar tareas
curl http://127.0.0.1:5000/tareas
```

## Pruebas

```bash
pytest
```

Las pruebas usan el cliente de testing de Flask y validan casos de uso basicos y errores comunes.

## Endpoints

- `POST /tareas`: crea una tarea. Ejemplo de cuerpo:
  ```json
  {
    "descripcion": "Comprar leche",
    "completada": false
  }
  ```
- `GET /tareas`: devuelve todas las tareas.
- `GET /tareas/<id>`: devuelve la tarea con el identificador indicado.
- `PUT /tareas/<id>`: actualiza campos existentes de una tarea.
- `DELETE /tareas/<id>`: elimina una tarea.

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
