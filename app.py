from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import count
from typing import Dict, List, Optional

from flask import Flask, abort, jsonify, request

app = Flask(__name__)

MAX_DESCRIPTION_LENGTH = 255


@dataclass
class Task:
    id: int
    descripcion: str
    completada: bool = False


class TaskStore:
    """Gestiona las tareas en memoria y entrega un interfaz claro."""

    def __init__(self) -> None:
        self._tasks: Dict[int, Task] = {}
        self._id_sequence = count(start=1)

    def create(self, descripcion: str, completada: bool = False) -> Task:
        task_id = next(self._id_sequence)
        task = Task(id=task_id, descripcion=descripcion, completada=completada)
        self._tasks[task_id] = task
        return task

    def list(self) -> List[Task]:
        return list(self._tasks.values())

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update(
        self,
        task_id: int,
        *,
        descripcion: Optional[str] = None,
        completada: Optional[bool] = None,
    ) -> Task:
        task = self._tasks[task_id]
        if descripcion is not None:
            task.descripcion = descripcion
        if completada is not None:
            task.completada = completada
        return task

    def delete(self, task_id: int) -> None:
        del self._tasks[task_id]

    def exists_description(self, descripcion: str, *, exclude_id: Optional[int] = None) -> bool:
        """Comprueba duplicados por descripcion ignorando mayusculas."""
        needle = descripcion.casefold()
        for task_id, task in self._tasks.items():
            if exclude_id is not None and task_id == exclude_id:
                continue
            if task.descripcion.casefold() == needle:
                return True
        return False

    def reset(self) -> None:
        """Reinicia el almacen. Pensado para pruebas automatizadas."""
        self._tasks.clear()
        self._id_sequence = count(start=1)


store = TaskStore()


def _task_to_dict(task: Task) -> Dict[str, object]:
    return asdict(task)


def _get_task_or_404(task_id: int) -> Task:
    """Devuelve la tarea si existe; aborta con 404 en caso contrario."""
    task = store.get(task_id)
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
        if len(descripcion.strip()) > MAX_DESCRIPTION_LENGTH:
            abort(
                400,
                description=f"La descripcion no puede exceder {MAX_DESCRIPTION_LENGTH} caracteres.",
            )
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
    if store.exists_description(payload["descripcion"]):
        abort(409, description="Ya existe una tarea con la misma descripcion.")
    task = store.create(
        descripcion=payload["descripcion"],
        completada=payload.get("completada", False),
    )
    response = jsonify(_task_to_dict(task))
    response.status_code = 201
    response.headers["Location"] = f"/tareas/{task.id}"
    return response


@app.get("/tareas")
def listar_tareas():
    tasks = [_task_to_dict(task) for task in store.list()]
    return jsonify(tasks)


@app.get("/tareas/<int:task_id>")
def obtener_tarea(task_id: int):
    task = _get_task_or_404(task_id)
    return jsonify(_task_to_dict(task))


@app.put("/tareas/<int:task_id>")
def actualizar_tarea(task_id: int):
    _get_task_or_404(task_id)
    payload = _parse_task_payload(partial=True)

    # Solo actualizamos los campos presentes en la peticion.
    updated_descripcion: Optional[str] = None
    updated_completada: Optional[bool] = None

    if "descripcion" in payload:
        if store.exists_description(payload["descripcion"], exclude_id=task_id):
            abort(409, description="Ya existe una tarea con la misma descripcion.")
        updated_descripcion = payload["descripcion"]
    if "completada" in payload:
        updated_completada = payload["completada"]
    updated = store.update(
        task_id,
        descripcion=updated_descripcion,
        completada=updated_completada,
    )
    return jsonify(_task_to_dict(updated))


@app.delete("/tareas/<int:task_id>")
def eliminar_tarea(task_id: int):
    _get_task_or_404(task_id)
    store.delete(task_id)
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


@app.errorhandler(409)
def handle_conflict(error):
    return jsonify({"error": "Conflicto", "detalle": error.description}), 409


@app.errorhandler(500)
def handle_internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    # Modo debug facilita el desarrollo mostrando recargas automaticas.
    app.run(debug=True)
