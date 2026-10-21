import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.goals import calc_bmr, calc_tdee, calc_targets


def test_calc_bmr():
    """Test: BMR con fórmula Mifflin-St Jeor.
    
    Ejemplo: Hombre de 30 años, 75 kg, 180 cm.
    BMR esperado aproximadamente: 10*75 + 6.25*180 - 5*30 + 5 = 735 + 1125 - 150 + 5 = 1715"""
    # Hombre, 30 años, 75kg, 180cm
    bmr = calc_bmr("male", 75, 180, 30)
    # Cálculo manual: 10*75 + 6.25*180 - 5*30 + 5 = 750 + 1125 - 150 + 5 = 1730
    assert 1700 < bmr < 1800, f"Expected BMR around 1730, got {bmr}"


def test_calc_tdee():
    """Test: TDEE con multiplicadores de actividad.
    
    Ejemplo: Hombre con BMR 1750 y actividad moderada.
    TDEE esperado: 1750 * 1.55 = 2712.5"""
    bmr = 1750
    tdee = calc_tdee(bmr, "moderate")
    expected = 1750 * 1.55
    assert 2700 < tdee < 2800, f"Expected TDEE around {expected}, got {tdee}"


def test_calc_targets_lose_weight():
    """Test: objetivos para perder peso."""
    user = {
        "age": 30,
        "sex": "male",
        "weight_kg": 75,
        "height_cm": 180,
        "activity_level": "moderate",
        "goal": "lose_weight",
    }
    targets = calc_targets(user)
    assert targets["kcal_goal"] < 2500, f"Expected caloric deficit for weight loss, got {targets['kcal_goal']}"
    assert targets["protein_grams"] > 0, f"Expected positive protein goal, got {targets['protein_grams']}"


def test_calc_targets_gain_weight():
    """Test: objetivos para ganar peso."""
    user = {
        "age": 30,
        "sex": "male",
        "weight_kg": 75,
        "height_cm": 180,
        "activity_level": "moderate",
        "goal": "gain_weight",
    }
    targets = calc_targets(user)
    assert targets["kcal_goal"] > 2500, f"Expected caloric surplus for weight gain, got {targets['kcal_goal']}"


def test_calc_targets_maintain():
    """Test: objetivos de mantenimiento."""
    user = {
        "age": 30,
        "sex": "male",
        "weight_kg": 75,
        "height_cm": 180,
        "activity_level": "moderate",
        "goal": "maintain",
    }
    targets = calc_targets(user)
    # Maintenance should be around TDEE
    assert 2000 < targets["kcal_goal"] < 3000, f"Expected maintenance calories around TDEE, got {targets['kcal_goal']}"