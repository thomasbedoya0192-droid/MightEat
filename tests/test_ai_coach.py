import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_coach import build_user_context, ask_coach, set_ai_provider, get_recommendations
from src.db import init_db
from src.auth import create_user


def _setup_user():
    """Inicializa BD y crea un usuario de prueba, retorna user_id."""
    init_db()
    user = create_user('Test User', 30, 'Male', 180, 75, 'moderate', 'maintain')
    return user[0]


def test_build_user_context():
    """Test: build_user_context retorna estructura correcta."""
    user_id = _setup_user()
    context = build_user_context(user_id=user_id, days=3)
    
    assert "perfil" in context, "Context should have 'perfil' key"
    assert "metas_diarias" in context, "Context should have 'metas_diarias' key"
    assert "historico" in context, "Context should have 'historico' key"
    assert len(context["historico"]) == 3, f"Expected 3 days in historico, got {len(context['historico'])}"
    
    perfil = context["perfil"]
    assert "edad" in perfil, "Perfil should have 'edad'"
    assert "sexo" in perfil, "Perfil should have 'sexo'"
    assert "peso" in perfil, "Perfil should have 'peso'"
    assert "altura" in perfil, "Perfil should have 'altura'"
    assert "objetivo" in perfil, "Perfil should have 'objetivo'"


def test_ask_coach_mock():
    """Test: ask_coach en modo mock retorna respuesta."""
    set_ai_provider("mock")
    user_id = _setup_user()
    
    context = build_user_context(user_id=user_id, days=1)
    question = "¿Cómo voy hoy?"
    response = ask_coach(user_id=user_id, question=question, context=context)
    
    assert response is not None, "Response should not be None"
    assert len(response) > 0, "Response should not be empty"
    assert "nutrición" in response.lower() or "objetivo" in response.lower(), \
        f"Response should mention nutrition or goal, got: {response}"


def test_ask_coach_different_questions():
    """Test: ask_coach con diferentes tipos de preguntas."""
    set_ai_provider("mock")
    user_id = _setup_user()
    
    context = build_user_context(user_id=user_id, days=1)
    
    # Probar diferentes preguntas
    questions = [
        "¿Cómo voy hoy?",
        "¿Qué me falta de proteína?",
        "Sugiere una cena para completar mis metas",
    ]
    
    for question in questions:
        response = ask_coach(user_id=user_id, question=question, context=context)
        assert response is not None, f"Response should not be None for question: {question}"
        assert len(response) > 0, f"Response should not be empty for question: {question}"


def test_get_recommendations_mock():
    """Test: get_recommendations en modo mock retorna recomendaciones."""
    set_ai_provider("mock")
    user_id = _setup_user()
    
    recomendaciones = get_recommendations(user_id)
    assert recomendaciones is not None, "Recommendations should not be None"
    assert len(recomendaciones) > 0, "Recommendations should not be empty"
    assert "Recomendaciones" in recomendaciones, f"Expected header, got: {recomendaciones[:100]}"


def test_set_ai_provider():
    """Test: set_ai_provider configura el proveedor."""
    # Probar con mock
    set_ai_provider("mock")
    # No causamos error al configurar
    
    # Probar con otros proveedores (aunque no tengan claves, no deberían romper)
    set_ai_provider("claude", claude_key="test-key")
    set_ai_provider("openrouter", openrouter_key="test-key")