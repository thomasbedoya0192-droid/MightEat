import os
import json
import urllib.request
from datetime import date, timedelta
from typing import Dict, Any, Optional, List

from src.db import get_connection
from src.diary import get_entries_by_date, get_daily_totals
from src.goals import calc_targets


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env_file() -> None:
    """Carga variables de entorno desde .env si existen (sin dependencias externas)."""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


# Cargar variables de entorno al importar el módulo
_load_env_file()

# Configuración del proveedor de IA - lectura de variables de entorno
AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")  # "mock", "claude", "openrouter", "gemini"
AI_CLAUDE_KEY = os.getenv("AI_CLAUDE_KEY", "")
AI_OPENROUTER_KEY = os.getenv("AI_OPENROUTER_KEY", "")
AI_GEMINI_KEY = os.getenv("AI_GEMINI_KEY", "")
GEMINI_MODEL = os.getenv("MODEL", "gemini-1.5-flash")


def build_user_context(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Contexto del usuario para el coach de IA.
    
    Returns un diccionario con:
    - perfil: edad, sexo, peso, altura, objetivo, actividad
    - metas_diarias: kcal, carbs, fat, protein, fiber objetivo por día
    - historico: totales y alimentos por cada uno de los últimos 'days' días
    """
    conn = get_connection()
    cur = conn.cursor()

    # Obtener datos del usuario
    cur.execute(
        "SELECT name, age, sex, height_cm, weight_kg, activity_level, goal FROM users WHERE id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        # Usuario no encontrado, retornar estructura vacía
        return {
            "perfil": {
                "edad": 0,
                "sexo": "",
                "peso": 0,
                "altura": 0,
                "actividad": "",
                "objetivo": "maintain",
                "nombre": "",
            },
            "metas_diarias": {
                "kcal": 0,
                "carbs": 0,
                "fat": 0,
                "protein": 0,
                "fiber": 0,
            },
            "consumo_promedio": {
                "kcal": 0,
                "carbs": 0,
                "fat": 0,
                "protein": 0,
                "fiber": 0,
            },
            "historico": [],
        }

    nombre, edad, sexo, altura, peso, actividad, objetivo = row

    # Calcular metas diarias usando el módulo de goals
    user_dict = {
        "sex": sexo,
        "weight_kg": peso,
        "height_cm": altura,
        "age": edad,
        "activity_level": actividad,
        "goal": objetivo,
    }
    metas = calc_targets(user_dict)

    # Construir histórico de los últimos 'days' días
    historico = []
    totales_semana = {"kcal": 0, "carbs": 0, "fat": 0, "protein": 0, "fiber": 0}
    dias_con_datos = 0

    for i in range(days):
        fecha_objetivo = (date.today() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        totals = get_daily_totals(user_id, fecha_objetivo)
        entries = get_entries_by_date(user_id, fecha_objetivo)

        alimentos = [e["food_name"] for e in entries] if entries else []

        dia = {
            "fecha": fecha_objetivo,
            "kcal": totals["kcal"],
            "carbs": totals["carbs"],
            "fat": totals["fat"],
            "protein": totals["protein"],
            "fiber": totals["fiber"],
            "alimentos": alimentos,
        }
        historico.append(dia)

        # Acumular promedios solo de días con registro
        if entries:
            dias_con_datos += 1
            for clave in totales_semana:
                totales_semana[clave] += totals[clave]

    # Calcular consumo promedio de días con registro
    if dias_con_datos > 0:
        consumo_promedio = {k: round(v / dias_con_datos, 1) for k, v in totales_semana.items()}
    else:
        consumo_promedio = {"kcal": 0, "carbs": 0, "fat": 0, "protein": 0, "fiber": 0}

    return {
        "perfil": {
            "edad": edad,
            "sexo": sexo,
            "peso": peso,
            "altura": altura,
            "actividad": actividad,
            "objetivo": objetivo,
            "nombre": nombre,
        },
        "metas_diarias": metas,
        "consumo_promedio": consumo_promedio,
        "historico": historico,
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


def get_recommendations(user_id: int) -> str:
    """Generar recomendaciones nutricionales basadas en el perfil y consumo del usuario.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        recomendaciones en español
    """
    context = build_user_context(user_id)
    provider = AI_PROVIDER

    if provider == "mock":
        return _mock_recommendations(context)

    if provider == "gemini":
        if not AI_GEMINI_KEY:
            return "No se encontró AI_GEMINI_KEY en las variables de entorno. Configura tu .env o usa el proveedor 'mock'."
        perfil = context.get("perfil", {})
        metas = context.get("metas_diarias", {})
        consumo = context.get("consumo_promedio", {})
        historico = context.get("historico", [])

        prompt = (
            "Eres un coach de nutrición experto. Responde en español de forma clara, práctica y amable.\n"
            "Basándote ÚNICAMENTE en los datos del usuario a continuación, genera recomendaciones nutricionales "
            "personalizadas para ayudarle a alcanzar su objetivo (mantener, bajar o subir de peso). "
            "No inventes un peso meta específico; da recomendaciones de dirección (qué comer, qué ajustar, hábitos).\n\n"
            f"Perfil: {json.dumps(perfil, ensure_ascii=False)}\n"
            f"Metas diarias: {json.dumps(metas, ensure_ascii=False)}\n"
            f"Consumo promedio reciente: {json.dumps(consumo, ensure_ascii=False)}\n"
            f"Histórico (últimos días): {json.dumps(historico, ensure_ascii=False)}\n\n"
            "Recomendaciones:"
        )
        return _call_gemini(prompt, AI_GEMINI_KEY, GEMINI_MODEL)

    # Placeholder para proveedores reales (futuro)
    return f"[IA {provider}]: Recomendaciones en implementación real usarían el contexto del usuario con {provider}."


def _mock_coach_response(question: str, context: Dict) -> str:
    """Respuesta de ejemplo en modo mock."""
    perfil = context.get("perfil", {})
    objetivo = perfil.get("objetivo", "maintain")

    respuestas = {
        "¿cómo voy hoy?": f"Basado en tu perfil (objetivo: {objetivo}), tu consumo diario actual está dentro de los parámetros normales. Recuerda mantenerte hidratado.",
        "¿qué me falta de proteína?": f"Tu objetivo es {objetivo}. Asegúrate de incluir fuentes de proteína como carnes, legumbres o lácteos en cada comida.",
        "sugiere una cena para completar mis metas": "Una opción balanceada: pollo a la parrilla con quinoa y verduras al vapor, seguida de una pieza de fruta fresca.",
    }

    # Buscar pregunta exacta o devolver una respuesta genérica
    for key, value in respuestas.items():
        if key in question.lower():
            return value

    return f"Entiendo tu pregunta sobre nutrición con el objetivo de {objetivo}. Como coach de nutrición, puedo ayudarte a analizar tus hábitos alimenticios y sugerir ajustes para alcanzar tus metas, siempre basándonos en los datos de tu registro y recomendando consultar a un profesional de la salud para orientación personalizada."


def _mock_recommendations(context: Dict) -> str:
    """Generar recomendaciones nutricionales en modo mock, basadas en el contexto real."""
    perfil = context.get("perfil", {})
    metas = context.get("metas_diarias", {})
    consumo = context.get("consumo_promedio", {})
    historico = context.get("historico", [])

    nombre = perfil.get("nombre", "Usuario")
    objetivo = perfil.get("objetivo", "maintain")
    peso = perfil.get("peso", 0)

    metas_kcal = metas.get("kcal", 0)
    metas_protein = metas.get("protein", 0)
    metas_carbs = metas.get("carbs", 0)
    metas_fat = metas.get("fat", 0)

    consumo_kcal = consumo.get("kcal", 0)
    consumo_protein = consumo.get("protein", 0)

    # Calcular diferencia promedio
    diff_kcal = consumo_kcal - metas_kcal
    diff_protein = consumo_protein - metas_protein

    lineas: List[str] = []

    lineas.append(f"--- Recomendaciones para {nombre} ---")
    lineas.append("")
    lineas.append(f"Tu objetivo actual: {objetivo}")
    lineas.append(f"Metas diarias sugeridas: {metas_kcal:.0f} kcal, {metas_protein:.1f}g proteína, {metas_carbs:.1f}g carbohidratos, {metas_fat:.1f}g grasas")
    lineas.append("")
    lineas.append("Tu consumo promedio reciente:")
    lineas.append(f"- {consumo_kcal:.0f} kcal (meta: {metas_kcal:.0f})")
    lineas.append(f"- {consumo_protein:.1f}g proteína (meta: {metas_protein:.1f}g)")
    lineas.append("")

    # Recomendaciones según objetivo
    if objetivo == "lose_weight":
        lineas.append("🎯 OBJETIVO: Bajar de peso")
        if diff_kcal > 0:
            lineas.append(f"- Estás consumiendo aproximadamente {diff_kcal:.0f} kcal por encima de tu meta diaria. Intenta reducir ligeramente las porciones, especialmente carbohidratos y grasas.")
        else:
            lineas.append("- Estás por debajo o cerca de tu meta de kcal, lo cual es bueno para bajar de peso. No bajes demasiado las calorías.")
        if diff_protein < 0:
            lineas.append(f"- Te faltan aproximadamente {abs(diff_protein):.1f}g de proteína al día. Añade más pechuga de pollo, pescado, huevos o legumbres para mantener masa muscular mientras bajas de peso.")
        lineas.append("- Prioriza alimentos altos en volumen y bajos en calorías: verduras, sopas, ensaladas.")
        lineas.append("- Bebe agua antes de cada comida para ayudar a la saciedad.")
    elif objetivo == "gain_weight":
        lineas.append("🎯 OBJETIVO: Subir de peso")
        if diff_kcal < 0:
            lineas.append(f"- Estás consumiendo aproximadamente {abs(diff_kcal):.0f} kcal por debajo de tu meta. Intenta añadir colaciones saludables entre comidas (frutos secos, aguacate, aceite de oliva).")
        else:
            lineas.append("- Estás alcanzando o superando tu meta de kcal. Mantén este excedente moderado.")
        if diff_protein < 0:
            lineas.append(f"- Considera aumentar la proteína para apoyar el aumento de masa muscular (huevos, carnes, lácteos).")
        lineas.append("- Come con más frecuencia: 5-6 comidas pequeñas al día en lugar de 3 grandes.")
    else:
        lineas.append("🎯 OBJETIVO: Mantener peso")
        if abs(diff_kcal) < 100:
            lineas.append("- Tu consumo está cerca de tu meta de mantenimiento. ¡Buen trabajo!")
        elif diff_kcal > 0:
            lineas.append(f"- Estás por encima de tu meta de mantenimiento ({diff_kcal:.0f} kcal). Considera reducir ligeramente porciones si notas aumento de peso.")
        else:
            lineas.append(f"- Estás por debajo de tu meta de mantenimiento ({abs(diff_kcal):.0f} kcal). Puedes aumentar ligeramente las porciones si lo deseas.")
        lineas.append("- Mantén una dieta variada con proteínas, carbohidratos complejos y grasas saludables.")

    lineas.append("")
    lineas.append("💡 Sugerencias de comidas:")
    if objetivo == "lose_weight":
        lineas.append("- Desayuno: Avena con fruta y claras de huevo.")
        lineas.append("- Almuerzo: Pechuga de pollo con arroz integral y verduras al vapor.")
        lineas.append("- Cena: Pescado al horno con ensalada grande.")
        lineas.append("- Colación: Yogur griego o una pieza de fruta.")
    elif objetivo == "gain_weight":
        lineas.append("- Desayuno: Avena con plátano, mantequilla de maní y huevos.")
        lineas.append("- Almuerzo: Arroz con carne molida y aguacate.")
        lineas.append("- Cena: Pasta con pollo y aceite de oliva.")
        lineas.append("- Colación: Batido de leche, plátano y avena.")
    else:
        lineas.append("- Desayuno: Huevos revueltos con pan integral y aguacate.")
        lineas.append("- Almuerzo: Arroz, pollo y ensalada.")
        lineas.append("- Cena: Pescado o tofu con puré de papas y verduras.")
        lineas.append("- Colación: Frutos secos o yogur.")

    lineas.append("")
    lineas.append("⚠️ Nota: Estas recomendaciones son generales. Para un plan personalizado, consulta a un nutricionista o profesional de la salud.")

    return "\n".join(lineas)


def _call_gemini(prompt: str, api_key: str, model: str = "gemini-1.5-flash") -> str:
    """Llama a la API de Google Gemini y retorna el texto generado."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Error al consultar Gemini: {e}. Verifica tu AI_GEMINI_KEY y conexión a internet."


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

    if provider == "gemini":
        if not AI_GEMINI_KEY:
            return "No se encontró AI_GEMINI_KEY en las variables de entorno. Configura tu .env o usa el proveedor 'mock'."
        prompt = (
            "Eres un coach de nutrición experto. Responde en español de forma clara, práctica y amable.\n"
            f"Contexto del usuario (perfil, metas y consumo reciente):\n{json.dumps(context, ensure_ascii=False)}\n\n"
            f"Pregunta del usuario: {question}\n\n"
            "Respuesta:"
        )
        return _call_gemini(prompt, AI_GEMINI_KEY, GEMINI_MODEL)

    # En implementación real, enviarían al proveedor de IA correspondiente
    # usando las claves de API de las variables de entorno
    return f"[IA {provider}]: Recepción de pregunta. En implementación real, esta pregunta sería enviada a {provider} con el contexto proporcionado."


def get_recommendations(user_id: int) -> str:
    """Generar recomendaciones nutricionales basadas en el perfil y consumo del usuario.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        recomendaciones en español
    """
    context = build_user_context(user_id)
    provider = AI_PROVIDER

    if provider == "mock":
        return _mock_recommendations(context)

    if provider == "gemini":
        if not AI_GEMINI_KEY:
            return "No se encontró AI_GEMINI_KEY en las variables de entorno. Configura tu .env o usa el proveedor 'mock'."
        perfil = context.get("perfil", {})
        metas = context.get("metas_diarias", {})
        consumo = context.get("consumo_promedio", {})
        historico = context.get("historico", [])

        prompt = (
            "Eres un coach de nutrición experto. Responde en español de forma clara, práctica y amable.\n"
            "Basándote ÚNICAMENTE en los datos del usuario a continuación, genera recomendaciones nutricionales "
            "personalizadas para ayudarle a alcanzar su objetivo (mantener, bajar o subir de peso). "
            "No inventes un peso meta específico; da recomendaciones de dirección (qué comer, qué ajustar, hábitos).\n\n"
            f"Perfil: {json.dumps(perfil, ensure_ascii=False)}\n"
            f"Metas diarias: {json.dumps(metas, ensure_ascii=False)}\n"
            f"Consumo promedio reciente: {json.dumps(consumo, ensure_ascii=False)}\n"
            f"Histórico (últimos días): {json.dumps(historico, ensure_ascii=False)}\n\n"
            "Recomendaciones:"
        )
        return _call_gemini(prompt, AI_GEMINI_KEY, GEMINI_MODEL)

    # Placeholder para proveedores reales (futuro)
    return f"[IA {provider}]: Recomendaciones en implementación real usarían el contexto del usuario con {provider}."


def set_ai_provider(provider: str, claude_key: str = "", openrouter_key: str = "", gemini_key: str = "") -> None:
    """Configurar el proveedor de IA.
    
    Args:
        provider: "mock", "claude", "openrouter", "gemini"
        claude_key: clave API de Claude
        openrouter_key: clave API de OpenRouter
        gemini_key: clave API de Gemini
    """
    global AI_PROVIDER, AI_CLAUDE_KEY, AI_OPENROUTER_KEY, AI_GEMINI_KEY
    AI_PROVIDER = provider
    AI_CLAUDE_KEY = claude_key
    AI_OPENROUTER_KEY = openrouter_key
    AI_GEMINI_KEY = gemini_key
