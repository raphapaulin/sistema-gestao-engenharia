import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import SECRET_KEY, SESSION_MAX_AGE_SECONDS


PBKDF2_ITERATIONS = 260_000
VALID_PROFILES = {"Administrador", "Colaborador", "Visualizador"}


def _clean(value: str | None) -> str:
    return (value or "").strip()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(calculated_hash, expected_hash)


def get_user_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id_usuario, nome, email, senha_hash, perfil, ativo
            FROM Usuario
            WHERE LOWER(email) = LOWER(:email)
            LIMIT 1
            """
        ),
        {"email": _clean(email)},
    ).mappings().first()
    return dict(row) if row else None


def get_user_by_id(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id_usuario, nome, email, perfil, ativo
            FROM Usuario
            WHERE id_usuario = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()
    return dict(row) if row and row["ativo"] else None


def create_user(
    db: Session,
    nome: str,
    email: str,
    password: str,
    perfil: str = "Administrador",
) -> int:
    nome = _clean(nome)
    email = _clean(email).lower()
    perfil = _clean(perfil) or "Administrador"

    if not nome:
        raise ValueError("Informe o nome do usuário.")
    if not email:
        raise ValueError("Informe o e-mail do usuário.")
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if perfil not in VALID_PROFILES:
        raise ValueError("Perfil inválido.")

    try:
        result = db.execute(
            text(
                """
                INSERT INTO Usuario (nome, email, senha_hash, perfil)
                VALUES (:nome, :email, :senha_hash, :perfil)
                """
            ),
            {
                "nome": nome,
                "email": email,
                "senha_hash": hash_password(password),
                "perfil": perfil,
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Já existe um usuário com este e-mail.")

    return int(result.lastrowid)


def authenticate_user(db: Session, email: str, password: str) -> dict | None:
    user = get_user_by_email(db, email)
    if not user or not user["ativo"]:
        return None
    if not verify_password(password, user["senha_hash"]):
        return None

    db.execute(
        text(
            """
            UPDATE Usuario
            SET ultimo_login = :ultimo_login
            WHERE id_usuario = :user_id
            """
        ),
        {
            "ultimo_login": datetime.now().isoformat(timespec="seconds"),
            "user_id": user["id_usuario"],
        },
    )
    db.commit()
    user.pop("senha_hash", None)
    return user


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_session_token(user: dict) -> str:
    payload = {
        "sub": int(user["id_usuario"]),
        "email": user["email"],
        "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
    }
    payload_encoded = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_encoded}.{_b64encode(signature)}"


def read_session_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None

    payload_encoded, signature_encoded = token.split(".", 1)
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        received_signature = _b64decode(signature_encoded)
    except Exception:
        return None

    if not hmac.compare_digest(expected_signature, received_signature):
        return None

    try:
        payload = json.loads(_b64decode(payload_encoded))
    except Exception:
        return None

    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None

    if expires_at < int(time.time()):
        return None

    return payload
