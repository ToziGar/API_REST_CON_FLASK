# API de Lista de Tareas

API sencilla construida con Flask para gestionar tareas pendientes en memoria. Permite demostrar el ciclo CRUD completo y el manejo del estado `completada`.

## Requisitos

- Python 3.10 o superior
- Entorno virtual recomendado

Instala dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python app.py
```

La aplicacion se inicia en `http://127.0.0.1:5000/` en modo debug.

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

- El almacenamiento es solo en memoria, por lo que se vacia al reiniciar la aplicacion.
- Las respuestas de error incluyen mensajes descriptivos en formato JSON.
