import os
from typing import Dict, Any, Optional


# Configuración del proveedor de IA - lectura de variables de entorno
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")  # "mock", "claude", "openrouter"
AI_CLAUDE_KEY = os.getenv("AI_CLAUDE_KEY", "")
AI_OPENROUTER_KEY = os.getenv("AI_OPENROUTER_KEY", "")


def build_user_context(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Contexto del usuario para el coach de IA.
    
    Returns un diccionario con:
    - perfil: edad, sexo, peso, altura, objetivo
    - metas diarias: kcal, carbs, fat, protein, fiber por día
    - historico: totales y alimentos por cada uno de los últimos 'days' días
    """
    # En una implementación real, esto consultaría la base de datos
    # Por ahora, retornamos una estructura básica
    return {
        "perfil": {
            "edad": 0,
            "sexo": "",
            "peso": 0,
            "altura": 0,
            "objetivo": "maintain",
        },
        "metas_diarias": {
            "kcal": 0,
            "carbs": 0,
            "fat": 0,
            "protein": 0,
            "fiber": 0,
        },
        "historico": [
            {
                "fecha": "",
                "kcal": 0,
                "carbs": 0,
                "fat": 0,
                "protein": 0,
                "fiber": 0,
                "alimentos": [],
            }
            for _ in range(days)
        ],
    }


def ask_coach(user_id: int, question: str, context: Optional[Dict] = None) -> str:
    """Enviar pregunta al coach de IA.
    
    Args:
        user_id: ID del usuario
        question: pregunta del usuario
        context: contexto opcional (si es None, se usa build_user_context)
    
    Returns:
        respuesta del coach de IA
    """
    if context is None:
        context = build_user_context(user_id)
    
    provider = AI_PROVIDER
    
    # En modo mock, retornar una respuesta educada
    if provider == "mock":
        return _mock_coach_response(question, context)
    
    # En implementación real, enviarían al proveedor de IA correspondiente
    # usando las claves de API de las variables de entorno
    return f"[IA {provider}]: Recepción de pregunta. En implementación real, esta pregunta sería enviada a {provider} con el contexto proporcionado."


def _mock_coach_response(question: str, context: Dict) -> str:
    """Respuesta de ejemplo en modo mock."""
    perfil = context.get("perfil", {})
    objetivo = perfil.get("objetivo", "maintain")
    
    respuestas = {
        "¿Cómo voy hoy?": f"Basado en tu perfil (objetivo: {objetivo}), tu consumo diario actual está dentro de los parámetros normales. Recuerda mantenerte hidratado.",
        "¿Qué me falta de proteína?": f"Tu objetivo es {perfil.get('objetivo', 'maintain')}. Asegúrate de incluir fuentes de proteína como carnes, legumbres o lácteos en cada comida.",
        "Sugiere una cena para completar mis metas": "Una opción balanceada: pollo a la parrilla con quinoa y verduras al vapor, seguida de una pieza de fruta fresca.",
    }
    
    # Buscar pregunta exacta o devolver una respuesta genérica
    for key, value in respuestas.items():
        if key.lower() in question.lower():
            return value
    
    return f"Entiendo tu pregunta sobre nutrición con el objetivo de {objetivo}. Como coach de nutrición, puedo ayudarte a analizar tus hábitos alimenticios y sugerir ajustes para alcanzar tus metas, siempre basándonos en los datos de tu registro y recomendando consultar a un profesional de la salud para orientación personalizada."


def set_ai_provider(provider: str, claude_key: str = "", openrouter_key: str = "") -> None:
    """Configurar el proveedor de IA.
    
    Args:
        provider: "mock", "claude", "openrouter"
        claude_key: clave API de Claude
        openrouter_key: clave API de OpenRouter
    """
    global AI_PROVIDER, AI_CLAUDE_KEY, AI_OPENROUTER_KEY
    AI_PROVIDER = provider
    AI_CLAUDE_KEY = claude_key
    AI_OPENROUTER_KEY = openrouter_key