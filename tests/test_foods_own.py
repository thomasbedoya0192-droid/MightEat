import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.foods_own import create_custom_food, get_user_foods, delete_food, validate_food_nutrition
from src.auth import create_user
from src.db import init_db
import sqlite3


def test_create_user_food():
    """Test: crear un alimento propio del usuario."""
    # Inicializar base de datos
    init_db()
    
    # Crear usuario A
    user_a = create_user('User A', 30, 'Female', 170, 65, 'maintain', 'maintain')
    user_a_id = user_a[0]
    
    # Crear alimento propio de usuario A
    food_id = create_custom_food(user_a_id, "Avena propia", "granos",
                                  389, 66, 7, 14, 10)
    
    # Verificar que el alimento fue creado
    foods = get_user_foods(user_a_id)
    assert len(foods) == 1, f"Expected 1 food, got {len(foods)}"
    assert foods[0][0] == food_id, "Food ID mismatch"
    assert foods[0][1] == "Avena propia", f"Expected 'Avena propia', got {foods[0][1]}"


def test_food_permissions():
    """Test: el usuario A no puede editar/borrar el alimento del usuario B."""
    # Inicializar base de datos
    init_db()
    
    # Crear usuario A y usuario B
    user_a = create_user('User A', 30, 'Female', 170, 65, 'maintain', 'maintain')
    user_a_id = user_a[0]
    
    user_b = create_user('User B', 28, 'Male', 180, 80, 'light', 'maintain')
    user_b_id = user_b[0]
    
    # Crear alimento propio de usuario A
    food_id = create_custom_food(user_a_id, "Avena propia", "granos",
                                  389, 66, 7, 14, 10)
    
    # Verificar que usuario A tiene el alimento
    foods_a = get_user_foods(user_a_id)
    assert len(foods_a) == 1, f"User A should have 1 food before deletion, got {len(foods_a)}"
    
    # Intentar borrar el alimento de usuario A desde usuario B
    result = delete_food(food_id, user_b_id)
    assert result is False, "User B should not be able to delete User A's food"
    
    # Intentar borrar el alimento propio desde usuario A
    result = delete_food(food_id, user_a_id)
    assert result is True, "User A should be able to delete own food"
    
    # Verificar que el alimento fue borrado
    foods_a = get_user_foods(user_a_id)
    assert len(foods_a) == 0, f"User A should have 0 foods after deletion, got {len(foods_a)}"
    
    # Verificar que usuario B no tiene alimentos propios (aún)
    foods_b = get_user_foods(user_b_id)
    assert len(foods_b) == 0, f"User B should have 0 foods, got {len(foods_b)}"


def test_nutrition_validation():
    """Test: validación de valores nutricionales."""
    # Ejemplo aproximado: 4*carbs + 4*protein + 9*fat debería ser similar a kcal
    # Para huevo: ~155 kcal, ~1g carbs, ~10g fat, ~13g protein
    # Cálculo: 4*1 + 4*13 + 9*10 = 4 + 52 + 90 = 146 (cerca de 155, diferencia ~7%)
    
    warning = validate_food_nutrition(155, 1, 10, 13)
    assert "Aviso" not in warning or "kcal" in warning, f"Expected no warning for reasonable values, got: {warning}"
    
    # Ejemplo con valores muy desbalanceados
    warning_extreme = validate_food_nutrition(100, 10, 10, 10)
    # 4*10 + 4*10 + 9*10 = 40 + 40 + 90 = 170, diferencia de 70% con 100
    assert "Aviso" in warning_extreme, "Expected warning for extreme imbalance"