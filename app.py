from __future__ import annotations

from itertools import count
from typing import Dict

from flask import Flask, abort, jsonify, request

app = Flask(__name__)

# Almacen en memoria para las tareas. La clave es el ID y el valor el contenido de la tarea.
_tasks: Dict[int, Dict[str, object]] = {}
_id_sequence = count(start=1)


def _get_task_or_404(task_id: int) -> Dict[str, object]:
    """Devuelve la tarea si existe; aborta con 404 en caso contrario."""
    task = _tasks.get(task_id)
    if task is None:
        abort(404, description="La tarea solicitada no existe.")
    return task


def _parse_task_payload(partial: bool = False) -> Dict[str, object]:
    """Valida el cuerpo de la peticion para crear o actualizar una tarea."""
    if not request.is_json:
        abort(400, description="Se esperaba un cuerpo JSON.")
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description="El cuerpo JSON debe ser un objeto.")

    task: Dict[str, object] = {}

    if "descripcion" in data:
        descripcion = data["descripcion"]
        if not isinstance(descripcion, str) or not descripcion.strip():
            abort(400, description="El campo 'descripcion' debe ser una cadena no vacia.")
        task["descripcion"] = descripcion.strip()
    elif not partial:
        abort(400, description="El campo 'descripcion' es obligatorio.")

    if "completada" in data:
        completada = data["completada"]
        if not isinstance(completada, bool):
            abort(400, description="El campo 'completada' debe ser booleano.")
        task["completada"] = completada

    return task


@app.post("/tareas")
def crear_tarea():
    payload = _parse_task_payload()
    task_id = next(_id_sequence)
    task = {
        "id": task_id,
        "descripcion": payload["descripcion"],
        "completada": payload.get("completada", False),
    }
    _tasks[task_id] = task
    response = jsonify(task)
    response.status_code = 201
    response.headers["Location"] = f"/tareas/{task_id}"
    return response


@app.get("/tareas")
def listar_tareas():
    return jsonify(list(_tasks.values()))


@app.get("/tareas/<int:task_id>")
def obtener_tarea(task_id: int):
    task = _get_task_or_404(task_id)
    return jsonify(task)


@app.put("/tareas/<int:task_id>")
def actualizar_tarea(task_id: int):
    task = _get_task_or_404(task_id)
    payload = _parse_task_payload(partial=True)

    # Solo actualizamos los campos presentes en la peticion.
    if "descripcion" in payload:
        task["descripcion"] = payload["descripcion"]
    if "completada" in payload:
        task["completada"] = payload["completada"]
    return jsonify(task)


@app.delete("/tareas/<int:task_id>")
def eliminar_tarea(task_id: int):
    _get_task_or_404(task_id)
    del _tasks[task_id]
    return "", 204


@app.errorhandler(400)
def handle_bad_request(error):
    return jsonify({"error": "Solicitud invalida", "detalle": error.description}), 400


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"error": "Recurso no encontrado", "detalle": error.description}), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    return jsonify({"error": "Metodo no permitido"}), 405


@app.errorhandler(500)
def handle_internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    # Modo debug facilita el desarrollo mostrando recargas automaticas.
    app.run(debug=True)
