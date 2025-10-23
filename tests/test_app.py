from __future__ import annotations

import pytest

from app import create_app, db


@pytest.fixture()
def app(tmp_path):
    # Crea una instancia de la aplicacion apuntando a una base SQLite temporal.
    test_db = tmp_path / "test.sqlite"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db}",
            "TOKEN_MAX_AGE": 3600,
        }
    )
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token_header(client):
    # Registra un usuario y devuelve un encabezado Authorization listo para usar.
    def _crear(nombre: str = "usuario", password: str = "secreto"):
        registro = client.post("/registro", json={"nombre": nombre, "password": password})
        assert registro.status_code == 201
        login = client.post("/login", json={"nombre": nombre, "password": password})
        assert login.status_code == 200
        token = login.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _crear


def test_registro_rechaza_nombres_repetidos(client):
    payload = {"nombre": "ana", "password": "supersecreto"}
    assert client.post("/registro", json=payload).status_code == 201
    respuesta = client.post("/registro", json=payload)
    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == "Conflicto"


def test_login_requiere_credenciales_validas(client):
    # Usuario inexistente.
    respuesta = client.post("/login", json={"nombre": "nadie", "password": "cualquiera"})
    assert respuesta.status_code == 401

    # Usuario correcto pero password incorrecto.
    client.post("/registro", json={"nombre": "ana", "password": "password"})
    respuesta = client.post("/login", json={"nombre": "ana", "password": "fallo"})
    assert respuesta.status_code == 401


def test_crear_tarea_exitoso(client, token_header):
    headers = token_header()
    respuesta = client.post("/tareas", json={"descripcion": "Comprar leche"}, headers=headers)
    assert respuesta.status_code == 201
    datos = respuesta.get_json()
    assert datos["descripcion"] == "Comprar leche"
    assert datos["completada"] is False


def test_crear_tarea_previene_duplicados(client, token_header):
    headers = token_header()
    primer = client.post("/tareas", json={"descripcion": "Pagar facturas"}, headers=headers)
    assert primer.status_code == 201
    repetido = client.post("/tareas", json={"descripcion": "pagar facturas"}, headers=headers)
    assert repetido.status_code == 409


def test_listar_tareas_filtra_por_usuario(client, token_header):
    headers_1 = token_header("ana", "password")
    headers_2 = token_header("raul", "password")

    client.post("/tareas", json={"descripcion": "Tarea de Ana"}, headers=headers_1)
    client.post("/tareas", json={"descripcion": "Tarea de Raul"}, headers=headers_2)

    lista_ana = client.get("/tareas", headers=headers_1).get_json()
    lista_raul = client.get("/tareas", headers=headers_2).get_json()

    assert len(lista_ana) == 1
    assert lista_ana[0]["descripcion"] == "Tarea de Ana"
    assert len(lista_raul) == 1
    assert lista_raul[0]["descripcion"] == "Tarea de Raul"


def test_actualizar_y_eliminar(client, token_header):
    headers = token_header()
    crear = client.post("/tareas", json={"descripcion": "Aprender Flask"}, headers=headers)
    tarea_id = crear.get_json()["id"]

    actualizar = client.put(
        f"/tareas/{tarea_id}",
        json={"descripcion": "Aprender Flask a fondo", "completada": True},
        headers=headers,
    )
    assert actualizar.status_code == 200
    datos = actualizar.get_json()
    assert datos["completada"] is True
    assert datos["descripcion"] == "Aprender Flask a fondo"

    borrar = client.delete(f"/tareas/{tarea_id}", headers=headers)
    assert borrar.status_code == 204
    inexistente = client.get(f"/tareas/{tarea_id}", headers=headers)
    assert inexistente.status_code == 404


def test_rechaza_peticion_sin_token(client):
    respuesta = client.get("/tareas")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"] == "No autorizado"
