import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from src.foods import load_seed_foods, search_foods, create_custom_food, calc_nutrition
from src.db import init_db


def setup_module(module):
    # Borrar base de datos existente para empezar limpio
    db_path = "/home/thomas/uni/semestre-5/Imaginacion_Creatividad/proyect/MightEat/data/app.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    # Crear base de datos y tablas
    init_db()
    # Cargar alimentos semilla
    load_seed_foods()


def test_calc_nutrition():
    """Test: 200 g de arroz blanco cocido debería tener ~260 kcal, 50 g de carbs, etc."""
    conn = sqlite3.connect("/home/thomas/uni/semestre-5/Imaginacion_Creatividad/proyect/MightEat/data/app.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g FROM foods WHERE name = 'Arroz blanco cocido'")
    row = cur.fetchone()
    conn.close()

    assert row is not None, "Arroz blanco cocido no encontrado en la base de datos"
    result = calc_nutrition(row, 200)

    # 200 g de arroz cocido: 130 kcal/100g * 2 = 260 kcal
    assert result["kcal"] == 260.0, f"Expected 260.0 kcal, got {result['kcal']}"
    # 200 g: 28.2 g/100g * 2 = 56.4 g de carbs
    assert result["carbs"] == 56.4, f"Expected 56.4 carbs, got {result['carbs']}"
    # 0.3 g/100g * 2 = 0.6 g de grasa
    assert result["fat"] == 0.6, f"Expected 0.6 fat, got {result['fat']}"
    # 2.7 g/100g * 2 = 5.4 g de proteína
    assert result["protein"] == 5.4, f"Expected 5.4 protein, got {result['protein']}"
    # 0.4 g/100g * 2 = 0.8 g de fibra
    assert result["fiber"] == 0.8, f"Expected 0.8 fiber, got {result['fiber']}"


def test_search_foods_with_tildes():
    """Test: búsqueda con tildes ('platano' encuentra 'Plátano')."""
    results = search_foods("platano", user_id=None)
    names = [r[1] for r in results]
    assert any("Plátano" in n for n in names), f"Expected 'Plátano' in results, got {names}"


def test_search_foods_user_scope():
    """Test: search_foods devuelve alimentos del catálogo y los propios del usuario."""
    # Creamos un usuario primero para usar como owner
    conn = sqlite3.connect("/home/thomas/uni/semestre-5/Imaginacion_Creatividad/proyect/MightEat/data/app.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (name, token_hash, age, sex, height_cm, weight_kg, activity_level, goal) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Test User", "hash_test_scope", 30, "Male", 180, 75, "maintain", "maintain"))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Creamos un alimento propio para el usuario
    food_id = create_custom_food(user_id=user_id, name="Avena propia", category="granos",
                                  kcal_100g=389, carbs_100g=66, fat_100g=7,
                                  protein_100g=14, fiber_100g=10)

    # Buscar con user_id debería encontrar el alimento propio + los del catálogo
    results = search_foods("avena", user_id=user_id)
    names = [r[1] for r in results]
    assert any("Avena propia" in n for n in names), f"Expected 'Avena propia' in results, got {names}"
    # También debería encontrar un alimento del catálogo general (mezcla propio + catálogo)
    assert any("Avena en hojuelas" in n for n in names), f"Expected general food in results, got {names}"

    # Limpiar: borrar el alimento propio y el usuario
    conn = sqlite3.connect("/home/thomas/uni/semestre-5/Imaginacion_Creatividad/proyect/MightEat/data/app.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def test_search_foods_max20():
    """Test: búsqueda devuelve máximo 20 resultados."""
    results = search_foods("", user_id=None)
    assert len(results) <= 20, f"Expected max 20 results, got {len(results)}"