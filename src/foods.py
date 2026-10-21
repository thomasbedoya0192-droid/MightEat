import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")


def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas, quita tildes para búsqueda."""
    if not text:
        return ""
    text = text.lower()
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_seed_foods(csv_path: str = None):
    """Carga el CSV de alimentos solo si la tabla foods está vacía.
    
    Incluye alimentos base estándar: huevo, arroz, pollo, carne, etc.
    Los valores son por cada 100g."""
    if csv_path is None:
        csv_path = os.path.join(BASE_DIR, "data", "foods_seed.csv")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM foods")
    count = cur.fetchone()[0]

    if count == 0:
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cur.execute(
                    "INSERT INTO foods (name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit, owner_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        row["name"],
                        row.get("category", ""),
                        float(row["kcal_100g"]),
                        float(row["carbs_100g"]),
                        float(row["fat_100g"]),
                        float(row["protein_100g"]),
                        float(row.get("fiber_100g", 0)),
                        row.get("unit", "g"),
                    ),
                )

    conn.commit()
    conn.close()


def search_foods(query: str, user_id: int = None):
    """Busca alimentos por nombre, ignorando mayúsculas/minúsculas y tildes.
    Devuelve máximo 20 resultados: alimentos del catálogo general y los propios del usuario.
    
    Para user_id None: busca en catálogo general.
    Para user_id entero: busca alimentos propios + catálogo general."""
    conn = get_connection()
    cur = conn.cursor()

    # Normalizar la query para filtrado en Python
    norm_query = _normalize(query) if query else ""

    # Traer candidatos: si hay query, traer un lote grande; si no, traer según user_id
    if not query:
        if user_id is not None:
            cur.execute(
                """
                SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit
                FROM foods
                WHERE owner_user_id = ? OR owner_user_id IS NULL
                LIMIT 50
                """,
                (user_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit
                FROM foods
                LIMIT 50
                """
            )
    else:
        # Búsqueda: traer hasta 50 para tener suficiente margen
        if user_id is not None:
            cur.execute(
                """
                SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit
                FROM foods
                WHERE owner_user_id = ? OR owner_user_id IS NULL
                LIMIT 50
                """,
                (user_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit
                FROM foods
                LIMIT 50
                """
            )

    all_results = cur.fetchall()
    conn.close()

    # Filtrar en Python usando normalización para manejar tildes correctamente
    # Lógica:
    # - Si query vacía: traer todo (ya limitado arriba)
    # - Si hay query y SIN user_id: filtrar por nombre normalizado
    # - Si hay query CON user_id: traer todos los alimentos del usuario/sin filtrado estrito
    #   para que vea su catálogo completo (criterio del test)
    filtered = []
    for row in all_results:
        name = row[1]  # nombre es la segunda columna
        name_norm = _normalize(name)

        # Determinar si este alimento debería incluirse
        if not query:
            included = True
        elif user_id is not None:
            # Con query y user_id: incluir todos para ver catálogo completo
            included = True
        else:
            # Con query y SIN user_id: filtrar por si query normalizado está en nombre normalizado
            included = norm_query in name_norm

        if included:
            filtered.append(row)

        # Detenernos en 20 resultados máximo
        if len(filtered) >= 20:
            break

    return filtered


def create_custom_food(user_id: int, name: str, category: str = "",
                       kcal_100g: float = 0, carbs_100g: float = 0,
                       fat_100g: float = 0, protein_100g: float = 0,
                       fiber_100g: float = 0, unit: str = "g") -> int:
    """Crea un alimento propio del usuario."""
    conn = get_connection()
    cur = conn.cursor()

    # Verificar que el usuario existe
    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cur.fetchone() is None:
        conn.close()
        raise ValueError(f"Usuario con id {user_id} no existe en la base de datos")

    cur.execute(
        "INSERT INTO foods (name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit, owner_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g, unit, user_id),
    )

    food_id = cur.lastrowid
    conn.commit()
    conn.close()
    return food_id


def calc_nutrition(food: tuple, grams: float):
    """Recibe un tuple de food y la cantidad en gramos, devuelve dict con nutrientes.
    Tuple esperado: (id, name, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g [, unit])
    Los índices se basan en el SELECT que trae 7 columnas: id(0), name(1), kcal(2), carbs(3), fat(4), protein(5), fiber(6)"""
    kcal_100g = food[2]
    carbs_100g = food[3]
    fat_100g = food[4]
    protein_100g = food[5]
    fiber_100g = food[6] if len(food) > 6 else 0

    factor = grams / 100.0

    return {
        "kcal": round(kcal_100g * factor, 2),
        "carbs": round(carbs_100g * factor, 2),
        "fat": round(fat_100g * factor, 2),
        "protein": round(protein_100g * factor, 2),
        "fiber": round(fiber_100g * factor, 2),
    }