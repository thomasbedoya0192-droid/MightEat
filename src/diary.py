import sqlite3
import os
from datetime import datetime

from src.foods import calc_nutrition, search_foods
from src.db import get_connection, DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def add_entry(user_id, food_id, grams, meal_type, eaten_at=None):
    """Registrar una entrada de comida en el diario."""
    if eaten_at is None:
        eaten_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Verificar que el usuario es dueño de este food_id o es del catálogo
    # (Simplified: we assume food_id belongs to this user or is general)
    # We need to check ownership
    cur.execute("SELECT owner_user_id FROM foods WHERE id = ?", (food_id,))
    row = cur.fetchone()
    
    if row is None:
        conn.close()
        raise ValueError(f"Food with id {food_id} not found")
    
    food_owner_user_id = row[0]
    
    # Allow if food is from catalog (owner_user_id is None) or belongs to user
    if food_owner_user_id is not None and food_owner_user_id != user_id:
        conn.close()
        raise PermissionError("You don't have permission to add this food")
    
    # Calcular nutrientes para la cantidad en gramos
    # We need to get food details first
    cur.execute("SELECT name, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g FROM foods WHERE id = ?", (food_id,))
    food_row = cur.fetchone()
    
    if food_row is None:
        conn.close()
        raise ValueError(f"Food with id {food_id} not found")
    
    name = food_row[0]
    nutrition = calc_nutrition(food_row, grams)
    
    # Insertar entrada en el diario
    cur.execute(
        "INSERT INTO diary_entries (user_id, food_id, grams, meal_type, eaten_at, kcal, carbs, fat, protein, fiber) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, food_id, grams, meal_type, eaten_at, 
         nutrition["kcal"], nutrition["carbs"], nutrition["fat"], 
         nutrition["protein"], nutrition["fiber"]),
    )
    
    conn.commit()
    conn.close()
    return eaten_at


def delete_entry(entry_id, user_id):
    """Eliminar una entrada del diario."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Verificar que la entrada pertenece al usuario
    cur.execute("SELECT user_id FROM diary_entries WHERE id = ?", (entry_id,))
    row = cur.fetchone()
    
    if row is None:
        conn.close()
        raise ValueError(f"Entry with id {entry_id} not found")
    
    if row[0] != user_id:
        conn.close()
        raise PermissionError("You don't have permission to delete this entry")
    
    cur.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def get_entries_by_date(user_id, date):
    """Obtener entradas del diario para una fecha específica.
    
    date: string in format YYYY-MM-DD
    Returns list of dicts with entry details and nutrient calculations.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Queries desde midnight hasta midnight del día siguiente
    date_start = f"{date} 00:00:00"
    date_end = f"{date} 23:59:59"
    
    cur.execute(
        """
        SELECT id, food_id, grams, meal_type, eaten_at, kcal, carbs, fat, protein, fiber
        FROM diary_entries
        WHERE user_id = ? AND eaten_at >= ? AND eaten_at <= ?
        ORDER BY meal_type, eaten_at
        """,
        (user_id, date_start, date_end),
    )
    
    rows = cur.fetchall()
    conn.close()
    
    # Formatear resultados
    entries = []
    for row in rows:
        entries.append({
            "id": row[0],
            "food_id": row[1],
            "grams": row[2],
            "meal_type": row[3],
            "eaten_at": row[4],
            "kcal": row[5],
            "carbs": row[6],
            "fat": row[7],
            "protein": row[8],
            "fiber": row[9],
        })
    
    return entries


def get_daily_totals(user_id, date):
    """Obtener totales nutricionales para un día específico.
    
    Returns dict with kcal, carbs, fat, protein, fiber.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    date_start = f"{date} 00:00:00"
    date_end = f"{date} 23:59:59"
    
    cur.execute(
        """
        SELECT SUM(kcal), SUM(carbs), SUM(fat), SUM(protein), SUM(fiber)
        FROM diary_entries
        WHERE user_id = ? AND eaten_at >= ? AND eaten_at <= ?
        """,
        (user_id, date_start, date_end),
    )
    
    row = cur.fetchone()
    conn.close()
    
    # Handle None results (no entries for the day)
    totals = {
        "kcal": row[0] if row[0] is not None else 0.0,
        "carbs": row[1] if row[1] is not None else 0.0,
        "fat": row[2] if row[2] is not None else 0.0,
        "protein": row[3] if row[3] is not None else 0.0,
        "fiber": row[4] if row[4] is not None else 0.0,
    }
    
    return totals