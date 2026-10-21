import sqlite3
import os
from datetime import datetime

from src.foods import calc_nutrition, search_foods, load_seed_foods
from src.db import get_connection, DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def add_entry(user_id, food_id, grams, meal_type, eaten_at=None):
    """Registrar una entrada de comida en el diario."""
    if eaten_at is None:
        eaten_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Verificar que el food_id existe y a quién pertenece
    cur.execute("SELECT owner_user_id FROM foods WHERE id = ?", (food_id,))
    row = cur.fetchone()
    
    if row is None:
        conn.close()
        raise ValueError(f"Food with id {food_id} not found")
    
    food_owner_user_id = row[0]  # owner_user_id es la primera columna
    
    # Allow if food is from catalog (owner_user_id is None) or belongs to user
    if food_owner_user_id is not None and food_owner_user_id != user_id:
        conn.close()
        raise PermissionError("You don't have permission to add this food")
    
    # Obtener los datos nutricionales del alimento completo
    # Usamos solo los campos que necesita calc_nutrition: id, name, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g
    # En ese orden específico (índices 0-6: id(0), name(1), kcal(2), carbs(3), fat(4), protein(5), fiber(6))
    cur.execute("SELECT id, name, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g FROM foods WHERE id = ?", (food_id,))
    food_nutrition_row = cur.fetchone()
    
    nutrition = calc_nutrition(food_nutrition_row, grams)
    nutrition = calc_nutrition(food_nutrition_row, grams)
    
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


def search_foods_for_user(query: str, user_id: int) -> list:
    """Buscar alimentos que el usuario pueda agregar.
    
    Devuelve alimentos del catálogo general disponibles para este usuario.
    """
    # Cargar alimentos si la tabla está vacía
    load_seed_foods()
    
    # Buscar en catálogo general (sin restricción de user_id para ver todos los alimentos base)
    results = search_foods(query, user_id=None)
    
    # Formatear resultados para la UI
    formatted = []
    for row in results:
        # row: (id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit)
        formatted.append({
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "kcal_100g": row[3],
            "carbs_100g": row[4],
            "fat_100g": row[5],
            "protein_100g": row[6],
            "fiber_100g": row[7],
            "unit": row[8],
        })
    
    return formatted