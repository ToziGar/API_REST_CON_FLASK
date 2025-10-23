from __future__ import annotations

import pytest

from app import MAX_DESCRIPTION_LENGTH, app, store


@pytest.fixture(autouse=True)
def reset_store():
    store.reset()
    app.config.update(TESTING=True)
    yield
    store.reset()


@pytest.fixture()
def client():
    return app.test_client()


def test_crear_tarea_exitoso(client):
    respuesta = client.post("/tareas", json={"descripcion": "Comprar leche"})
    assert respuesta.status_code == 201
    datos = respuesta.get_json()
    assert datos["descripcion"] == "Comprar leche"
    assert datos["completada"] is False
    assert datos["id"] == 1


def test_crear_tarea_conflicto_por_descripcion(client):
    payload = {"descripcion": "Pagar facturas"}
    assert client.post("/tareas", json=payload).status_code == 201
    respuesta = client.post("/tareas", json={"descripcion": "pagar facturas"})
    assert respuesta.status_code == 409
    datos = respuesta.get_json()
    assert datos["error"] == "Conflicto"


def test_crear_tarea_valida_longitud(client):
    descripcion = "x" * (MAX_DESCRIPTION_LENGTH + 1)
    respuesta = client.post("/tareas", json={"descripcion": descripcion})
    assert respuesta.status_code == 400
    datos = respuesta.get_json()
    assert "exceder" in datos["detalle"]


def test_actualizar_tarea(client):
    crear = client.post("/tareas", json={"descripcion": "Estudiar Flask"})
    task_id = crear.get_json()["id"]

    respuesta = client.put(
        f"/tareas/{task_id}",
        json={"completada": True, "descripcion": "Estudiar flask"},
    )
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["completada"] is True
    assert datos["descripcion"] == "Estudiar flask"


def test_actualizar_conflicto(client):
    primera = client.post("/tareas", json={"descripcion": "Hacer la compra"})
    segunda = client.post("/tareas", json={"descripcion": "Sacar al perro"})

    id_segunda = segunda.get_json()["id"]
    respuesta = client.put(f"/tareas/{id_segunda}", json={"descripcion": "Hacer la compra"})
    assert respuesta.status_code == 409


def test_eliminar_tarea(client):
    task_id = client.post("/tareas", json={"descripcion": "Prueba borrar"}).get_json()["id"]
    respuesta = client.delete(f"/tareas/{task_id}")
    assert respuesta.status_code == 204
    # Eliminar nuevamente debe fallar con 404
    respuesta_repetida = client.delete(f"/tareas/{task_id}")
    assert respuesta_repetida.status_code == 404
