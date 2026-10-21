import sqlite3
import os

from src.db import get_connection, DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_custom_food(user_id, name, category, kcal_100g, carbs_100g, fat_100g,
                       protein_100g, fiber_100g, unit="g") -> int:
    """Crea un alimento propio del usuario.
    
    Solo el usuario dueño puede ver y editar este alimento.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Insertar alimento propio del usuario
    cur.execute(
        "INSERT INTO foods (name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit, owner_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit, user_id),
    )
    
    food_id = cur.lastrowid
    conn.commit()
    conn.close()
    return food_id


def get_user_foods(user_id) -> list:
    """Obtener todos los alimentos propios de un usuario.
    
    Returns list of food dicts/tuples with food information.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(
        "SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit FROM foods WHERE owner_user_id = ?",
        (user_id,),
    )
    
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_food(food_id, user_id) -> bool:
    """Eliminar un alimento propio del usuario.
    
    Returns True if deleted, False if the food doesn't belong to the user.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Verificar que el alimento pertenece al usuario
    cur.execute("SELECT owner_user_id FROM foods WHERE id = ?", (food_id,))
    row = cur.fetchone()
    
    if row is None or row[0] != user_id:
        conn.close()
        return False
    
    # Eliminar también las porciones asociadas
    cur.execute("DELETE FROM food_portions WHERE food_id = ?", (food_id,))
    
    # Eliminar el alimento
    cur.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    
    conn.commit()
    conn.close()
    return True


def validate_food_nutrition(kcal_100g, carbs_100g, fat_100g, protein_100g) -> str:
    """Validar valores nutricionales.
    
    Returns warning message if kcal doesn't match approx 4*carbs + 4*protein + 9*fat,
    or empty string if OK.
    """
    calculated_kcal = 4 * carbs_100g + 4 * protein_100g + 9 * fat_100g
    difference = abs(kcal_100g - calculated_kcal)
    
    # Si la diferencia es mayor al 20%, es una advertencia
    if difference > calculated_kcal * 0.2 and calculated_kcal > 0:
        return f"Aviso: Los kcal ({kcal_100g}) no coinciden aproximadamente con el cálculo 4*carbos + 4*proteína + 9*grasas ({round(calculated_kcal, 1)}). Esto es solo una advertencia."
    
    return ""