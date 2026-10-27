import hashlib
import secrets
import sqlite3
import os

from src.db import get_connection, DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_user(name, age, sex, height_cm, weight_kg, activity_level, goal) -> tuple:
    """Crea un nuevo usuario.
    
    Returns (user_id, token) where token is the plain token returned once.
    The token hash is saved in the database, not the plain token.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Generar token aleatorio
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Insertar usuario
    cur.execute(
        "INSERT INTO users (name, token_hash, age, sex, height_cm, weight_kg, activity_level, goal) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, token_hash, age, sex, height_cm, weight_kg, activity_level, goal),
    )
    
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    # Devolver el token en claro UNA sola vez
    return user_id, token


def login_with_token(token: str) -> dict | None:
    """Iniciar sesión con un token.
    
    Returns user data dict if login successful, None if token is invalid.
    """
    import hashlib
    
    # Calcular hash del token proporcionado
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Buscar usuario por hash (nunca por token plano)
    cur.execute(
        "SELECT id, name, token_hash, age, sex, height_cm, weight_kg, activity_level, goal FROM users WHERE token_hash = ?",
        (token_hash,),
    )
    
    row = cur.fetchone()
    conn.close()
    
    if row is None:
        return None

    # Devolver datos del usuario (como diccionario)
    return {
        "id": row[0],
        "name": row[1],
        "token_hash": row[2],
        "age": row[3],
        "sex": row[4],
        "height_cm": row[5],
        "weight_kg": row[6],
        "activity_level": row[7],
        "goal": row[8],
    }


def update_user_profile(user_id: int, activity_level: str, goal: str) -> None:
    """Actualiza el nivel de actividad y el objetivo del usuario en la base de datos."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET activity_level = ?, goal = ? WHERE id = ?",
        (activity_level, goal, user_id),
    )
    conn.commit()
    conn.close()


def save_user_targets(user_id: int, kcal_goal: float, protein_goal: float, carbs_goal: float, fat_goal: float, fiber_goal: float) -> None:
    """Guarda las metas nutricionales calculadas del usuario en la base de datos."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET kcal_goal = ?, protein_goal = ?, carbs_goal = ?, fat_goal = ?, fiber_goal = ? WHERE id = ?",
        (kcal_goal, protein_goal, carbs_goal, fat_goal, fiber_goal, user_id),
    )
    conn.commit()
    conn.close()