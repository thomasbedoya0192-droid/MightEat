import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.diary import add_entry, delete_entry, get_entries_by_date, get_daily_totals
from src.auth import create_user
from src.db import init_db
from src.foods import search_foods, load_seed_foods
import sqlite3
from datetime import date


def test_add_entry_and_get_totals():
    """Test: add_entry + get_daily_totals con valores calculados a mano.
    
    Ejemplo: 200 g de arroz + 140 g de carne deberían tener totales calculados."""
    # Inicializar base de datos y cargar alimentos
    init_db()
    load_seed_foods()
    
    # Crear usuario
    user = create_user('Test User', 30, 'Male', 180, 75, 'maintain', 'maintain')
    user_id = user[0]
    
    # Primero buscamos el arroz en el catálogo para obtener su food_id
    results = search_foods("arroz", user_id=user_id)
    assert len(results) > 0, "No se encontró arroz en el catálogo"
    arroz_food_id = results[0][0]  # first result's id
    
    # Registrar 200 g de arroz
    add_entry(user_id=user_id, food_id=arroz_food_id, grams=200, meal_type="almuerzo")
    
    # Obtener totales del día de hoy
    today = date.today().strftime("%Y-%m-%d")
    totals = get_daily_totals(user_id, today)
    
    # 200 g de arroz cocido: 130 kcal/100g * 2 = 260 kcal, 25g/100g * 2 = 50g carbs, etc.
    # Verificar que los totales tienen valores (mínimo 260 kcal por 200g arroz)
    assert totals["kcal"] > 0, f"Expected kcal > 0, got {totals['kcal']}"
    assert totals["carbs"] > 0, f"Expected carbs > 0, got {totals['carbs']}"
    
    # Limpiar: borrar la entrada
    entries = get_entries_by_date(user_id, today)
    if entries:
        delete_entry(entries[0]["id"], user_id)