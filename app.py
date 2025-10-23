from __future__ import annotations

from typing import Dict, Optional

from flask import Blueprint, Flask, abort, current_app, g, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
api_bp = Blueprint("api", __name__)

# Limite de caracteres permitido para la descripcion de cada tarea.
MAX_DESCRIPTION_LENGTH = 255


class User(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    tareas = db.relationship("Task", backref="usuario", cascade="all, delete-orphan", lazy=True)

    def establecer_password(self, password: str) -> None:
        # Almacena el hash del password para no guardar texto plano.
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password: str) -> bool:
        # Comprueba que el password proporcionado coincide con el almacenado.
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    __tablename__ = "tareas"

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(MAX_DESCRIPTION_LENGTH), nullable=False)
    completada = db.Column(db.Boolean, default=False, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)


def _get_serializer() -> URLSafeTimedSerializer:
    # Obtiene o crea el serializador utilizado para firmar tokens.
    if "token_serializer" not in current_app.extensions:
        current_app.extensions["token_serializer"] = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"]
        )
    return current_app.extensions["token_serializer"]


def _serializar_tarea(task: Task) -> Dict[str, object]:
    # Convierte el modelo Task en un diccionario listo para JSON.
    return {
        "id": task.id,
        "descripcion": task.descripcion,
        "completada": task.completada,
    }


def _generar_token(usuario: User) -> str:
    # Emite un token firmado que identifica al usuario.
    serializer = _get_serializer()
    return serializer.dumps({"user_id": usuario.id})


def _verificar_token(token: str) -> User:
    # Revisa que el token sea valido y recupera al usuario.
    serializer = _get_serializer()
    try:
        datos = serializer.loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except SignatureExpired:
        abort(401, description="El token ha expirado.")
    except BadSignature:
        abort(401, description="Token invalido.")

    user_id = datos.get("user_id")
    if user_id is None:
        abort(401, description="Token incompleto.")

    usuario = db.session.get(User, user_id)
    if usuario is None:
        abort(401, description="Usuario no encontrado.")
    return usuario


def _obtener_usuario_actual() -> User:
    # Extrae y valida la cabecera Authorization, cacheando el resultado por peticion.
    if hasattr(g, "usuario_actual"):
        return g.usuario_actual

    encabezado = request.headers.get("Authorization", "")
    prefijo = "Bearer "
    if not encabezado.startswith(prefijo):
        abort(401, description="Cabecera Authorization ausente o invalida.")

    token = encabezado[len(prefijo) :].strip()
    if not token:
        abort(401, description="Token no proporcionado.")

    usuario = _verificar_token(token)
    g.usuario_actual = usuario
    return usuario


def _obtener_tarea_o_404(usuario: User, task_id: int) -> Task:
    # Busca la tarea perteneciente al usuario; si no existe lanza 404.
    tarea = Task.query.filter_by(id=task_id, usuario_id=usuario.id).first()
    if tarea is None:
        abort(404, description="La tarea solicitada no existe.")
    return tarea


def _descripcion_duplicada(
    usuario: User, descripcion: str, excluir_id: Optional[int] = None
) -> bool:
    # Determina si el usuario ya posee una tarea con la misma descripcion.
    descripcion_normalizada = descripcion.casefold()
    consulta = Task.query.filter(
        Task.usuario_id == usuario.id,
        func.lower(Task.descripcion) == descripcion_normalizada,
    )
    if excluir_id is not None:
        consulta = consulta.filter(Task.id != excluir_id)
    return db.session.query(consulta.exists()).scalar()


def _parse_task_payload(partial: bool = False) -> Dict[str, object]:
    """Valida el cuerpo de la peticion para crear o actualizar una tarea."""
    if not request.is_json:
        # Solo aceptamos cuerpos JSON; cualquier otro formato se rechaza.
        abort(400, description="Se esperaba un cuerpo JSON.")
    data = request.get_json()
    if not isinstance(data, dict):
        # El cuerpo debe ser un objeto JSON, no listas ni valores primitivos.
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


def _parse_user_payload() -> Dict[str, str]:
    # Valida la carga util para registro o login.
    if not request.is_json:
        abort(400, description="Se esperaba un cuerpo JSON.")
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description="El cuerpo JSON debe ser un objeto.")

    nombre = data.get("nombre")
    password = data.get("password")

    if not isinstance(nombre, str) or not nombre.strip():
        abort(400, description="El campo 'nombre' es obligatorio.")
    if not isinstance(password, str) or len(password) < 6:
        abort(400, description="El 'password' debe tener al menos 6 caracteres.")

    return {"nombre": nombre.strip(), "password": password}


@api_bp.post("/registro")
def registrar_usuario():
    # Crea un nuevo usuario tras validar los datos.
    payload = _parse_user_payload()
    nombre_normalizado = payload["nombre"].casefold()

    existente = User.query.filter(func.lower(User.nombre) == nombre_normalizado).first()
    if existente:
        abort(409, description="El nombre de usuario ya esta en uso.")

    usuario = User(nombre=payload["nombre"])
    usuario.establecer_password(payload["password"])
    db.session.add(usuario)
    db.session.commit()

    return jsonify({"id": usuario.id, "nombre": usuario.nombre}), 201


@api_bp.post("/login")
def login():
    # Verifica las credenciales y devuelve un token firmado.
    payload = _parse_user_payload()
    nombre_normalizado = payload["nombre"].casefold()

    usuario = User.query.filter(func.lower(User.nombre) == nombre_normalizado).first()
    if usuario is None or not usuario.verificar_password(payload["password"]):
        abort(401, description="Credenciales invalidas.")

    token = _generar_token(usuario)
    return jsonify({"token": token, "usuario": {"id": usuario.id, "nombre": usuario.nombre}})


@api_bp.post("/tareas")
def crear_tarea():
    # Leemos y validamos el cuerpo de la peticion posterior.
    usuario = _obtener_usuario_actual()
    payload = _parse_task_payload()

    if _descripcion_duplicada(usuario, payload["descripcion"]):
        abort(409, description="Ya existe una tarea con la misma descripcion.")

    tarea = Task(
        descripcion=payload["descripcion"],
        completada=payload.get("completada", False),
        usuario=usuario,
    )
    db.session.add(tarea)
    db.session.commit()

    response = jsonify(_serializar_tarea(tarea))
    response.status_code = 201
    response.headers["Location"] = f"/tareas/{tarea.id}"
    return response


@api_bp.get("/tareas")
def listar_tareas():
    # Recopilamos y serializamos todas las tareas del usuario autenticado.
    usuario = _obtener_usuario_actual()
    tareas = Task.query.filter_by(usuario_id=usuario.id).order_by(Task.id.asc()).all()
    return jsonify([_serializar_tarea(task) for task in tareas])


@api_bp.get("/tareas/<int:task_id>")
def obtener_tarea(task_id: int):
    # Solo devolvemos la tarea si existe para el usuario actual.
    usuario = _obtener_usuario_actual()
    tarea = _obtener_tarea_o_404(usuario, task_id)
    return jsonify(_serializar_tarea(tarea))


@api_bp.put("/tareas/<int:task_id>")
def actualizar_tarea(task_id: int):
    # Verificamos que la tarea exista antes de aplicar cambios.
    usuario = _obtener_usuario_actual()
    tarea = _obtener_tarea_o_404(usuario, task_id)
    payload = _parse_task_payload(partial=True)

    updated_descripcion: Optional[str] = None
    updated_completada: Optional[bool] = None

    if "descripcion" in payload:
        if _descripcion_duplicada(usuario, payload["descripcion"], excluir_id=tarea.id):
            abort(409, description="Ya existe una tarea con la misma descripcion.")
        updated_descripcion = payload["descripcion"]
    if "completada" in payload:
        updated_completada = payload["completada"]

    if updated_descripcion is not None:
        tarea.descripcion = updated_descripcion
    if updated_completada is not None:
        tarea.completada = updated_completada

    db.session.commit()
    return jsonify(_serializar_tarea(tarea))


@api_bp.delete("/tareas/<int:task_id>")
def eliminar_tarea(task_id: int):
    # Confirmamos que la tarea exista antes de eliminarla.
    usuario = _obtener_usuario_actual()
    tarea = _obtener_tarea_o_404(usuario, task_id)
    db.session.delete(tarea)
    db.session.commit()
    return "", 204


def handle_bad_request(error):
    return jsonify({"error": "Solicitud invalida", "detalle": error.description}), 400


def handle_unauthorized(error):
    return jsonify({"error": "No autorizado", "detalle": error.description}), 401


def handle_not_found(error):
    return jsonify({"error": "Recurso no encontrado", "detalle": error.description}), 404


def handle_method_not_allowed(error):
    return jsonify({"error": "Metodo no permitido"}), 405


def handle_conflict(error):
    return jsonify({"error": "Conflicto", "detalle": error.description}), 409


def handle_internal_error(error):
    return jsonify({"error": "Error interno del servidor"}), 500


def create_app(config: Optional[Dict[str, object]] = None) -> Flask:
    # Crea y configura la aplicacion incluyendo base de datos y rutas.
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="cambia-esta-clave-en-produccion",
        SQLALCHEMY_DATABASE_URI="sqlite:///tareas.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TOKEN_MAX_AGE=3600 * 24,
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    app.register_blueprint(api_bp)

    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(401, handle_unauthorized)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(405, handle_method_not_allowed)
    app.register_error_handler(409, handle_conflict)
    app.register_error_handler(500, handle_internal_error)

    return app


app = create_app()


if __name__ == "__main__":
    # Crea las tablas si no existen y arranca el servidor de desarrollo.
    with app.app_context():
        db.create_all()
    app.run(debug=True)
