import streamlit as st

# Configuración de página
st.set_page_config(page_title="Nutri App 1.1", layout="wide")

import os
from datetime import datetime
from src.auth import create_user, login_with_token, update_user_profile, save_user_targets
from src.qr_utils import generate_qr_image, decode_qr_from_image
from src.foods import load_seed_foods, search_foods, calc_nutrition, create_custom_food
from src.diary import add_entry, delete_entry, get_entries_by_date, get_daily_totals
from src.db import init_db, get_connection
from src.ai_coach import set_ai_provider, get_recommendations
import io

# Session state initialization
if "user" not in st.session_state:
    st.session_state.user = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = "mock"

if "ai_recommendations" not in st.session_state:
    st.session_state.ai_recommendations = None


def login_screen():
    """Pantalla de login y registro."""
    st.title("Nutri App 1.1 - Acceso")
    
    option = st.radio("¿Qué deseas hacer?", ["Iniciar sesión", "Crear cuenta"])
    
    if option == "Crear cuenta":
        st.subheader("Crear nueva cuenta")
        with st.form("create_account"):
            name = st.text_input("Nombre")
            age = st.number_input("Edad", min_value=1, value=30)
            sex = st.selectbox("Sexo", ["Masculino", "Femenino"])
            height = st.number_input("Altura (cm)", min_value=1, value=180)
            weight = st.number_input("Peso (kg)", min_value=1, value=75)
            activity = st.selectbox("Nivel de actividad", ["sedentary", "light", "moderate", "active"])
            goal = st.selectbox("Objetivo", ["maintain", "lose_weight", "gain_weight"])
            
            submitted = st.form_submit_button("Crear cuenta y mostrar QR")
            if submitted:
                user_id, token = create_user(name, age, sex.lower().capitalize(), height, weight, activity, goal)
                st.session_state.user = {
                    "id": user_id,
                    "name": name,
                    "age": age,
                    "sex": sex.lower().capitalize(),
                    "height_cm": height,
                    "weight_kg": weight,
                    "activity_level": activity,
                    "goal": goal,
                }
                st.session_state.logged_in = True

        if submitted:
            # Generar y mostrar QR
            qr_img = generate_qr_image(token)
            st.success(f"Cuenta creada para {name}!")

            # Mostrar QR en pantalla
            st.image(qr_img, caption="Tu QR de acceso", width="stretch")

            # Opciones de respaldo
            st.info("Métodos alternativos de login:")

            # Opción 1: Subir imagen
            uploaded_file = st.file_uploader("Subir imagen del QR", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                bytes_data = uploaded_file.read()
                decoded = decode_qr_from_image(bytes_data)
                if decoded:
                    st.session_state.user = {
                        "id": user_id,
                        "name": name,
                        "age": age,
                        "sex": sex.lower().capitalize(),
                        "height_cm": height,
                        "weight_kg": weight,
                        "activity_level": activity,
                        "goal": goal,
                    }
                    st.session_state.logged_in = True
                    st.success("Login exitoso mediante imagen!")
                    st.rerun()
                else:
                    st.error("No se pudo decodificar el QR de la imagen")

            # Opción 2: Pegar token
            token_input = st.text_input("O pegar el token aquí", value=token[:10] + "...")
            if st.button("Login con token"):
                user = login_with_token(token_input)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.success("Login exitoso!")
                    st.rerun()
                else:
                    st.error("Token inválido")
        
        st.markdown("---")
        st.subheader("Iniciar sesión existente")
        with st.form("login_form"):
            token = st.text_input("Token de acceso")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                user = login_with_token(token)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.success(f"Bienvenido, {user['name']}!")
                    st.rerun()
                else:
                    st.error("Token inválido. Por favor, crea una cuenta o verifica el token.")
    
    else:  # Iniciar sesión
        st.subheader("Iniciar sesión")
        with st.form("login_form2"):
            token = st.text_input("Token de acceso")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                user = login_with_token(token)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    st.success(f"Bienvenido, {user['name']}!")
                    st.rerun()
                else:
                    st.error("Token inválido. Por favor, verifica el token o crea una cuenta.")


def load_food_database():
    """Inicializar la base de datos de alimentos."""
    init_db()
    load_seed_foods()


def food_selection_screen(user_id):
    """Pantalla para seleccionar o agregar alimentos."""
    st.subheader("Seleccionar alimento")
    
    # Buscar alimento
    query = st.text_input("Buscar alimento (ej: huevo, arroz, pollo, carne)")
    
    if query:
        results = search_foods(query, user_id)
        if results:
            st.write("Resultados encontrados:")
            for food in results[:10]:  # Máximo 10 resultados
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{food[1]}** ({food[2]})")
                    st.caption(f"{food[3]} kcal, {food[5]}g proteinas por 100g")
                with col2:
                    if st.button(f"Agregar", key=f"add_{food[0]}"):
                        st.session_state.selected_food_id = food[0]
                        st.session_state.selected_food_name = food[1]
                        st.session_state.selected_grams = 100  # Por defecto 100g
                        st.rerun()
        else:
            st.info("No encontrados. Puedes agregar uno nuevo abajo.")
    
    st.markdown("---")
    st.write("Agregar alimento nuevo:")
    with st.form("new_food_form"):
        new_food_name = st.text_input("Nombre del alimento")
        new_food_category = st.selectbox("Categoría", ["proteinas", "granos", "vegetales", "lacteos", "frutas", "panaderia"])
        new_kcal = st.number_input("Kcal por 100g", min_value=0, value=100)
        new_protein = st.number_input("Proteinas por 100g", min_value=0, value=20)
        new_fat = st.number_input("Grasas por 100g", min_value=0, value=5)
        new_carbs = st.number_input("Carbohidratos por 100g", min_value=0, value=20)
        new_fiber = st.number_input("Fibra por 100g", min_value=0, value=3)
        
        submitted = st.form_submit_button("Guardar alimento")
        if submitted:
            try:
                food_id = create_custom_food(
                    user_id=user_id,
                    name=new_food_name,
                    category=new_food_category,
                    kcal_100g=new_kcal,
                    carbs_100g=new_carbs,
                    fat_100g=new_fat,
                    protein_100g=new_protein,
                    fiber_100g=new_fiber
                )
                st.success(f"Alimento '{new_food_name}' guardado con ID {food_id}!")
                st.session_state.selected_food_id = food_id
                st.session_state.selected_food_name = new_food_name
                st.session_state.selected_grams = 100
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def main_app():
    """Aplicación principal después del login."""
    # Restaurar proveedor de IA guardado en sesión
    set_ai_provider(st.session_state.ai_provider)
    
    st.sidebar.title(f"Hola, {st.session_state.user['name']}")
    st.sidebar.success("Sesión activa")
    
    menu = st.sidebar.radio("Menú", [
        "Mi balance",
        "Diario de comidas", 
        "Mis alimentos",
        "Recomendaciones IA",
        "Configuración",
        "Cerrar sesión"
    ])
    
    # Inicializar bases de datos
    load_food_database()
    
    if menu == "Mi balance":
        st.title("Mi balance nutricional")
        
        # Fecha selector
        date_today = st.date_input("Fecha", value=datetime.now().date())
        date_str = date_today.strftime("%Y-%m-%d")
        
        # Obtener totales
        totals = get_daily_totals(st.session_state.user["id"], date_str)
        
        st.metric("Kcal del día", f"{totals['kcal']:.0f} kcal")
        st.metric("Proteinas", f"{totals['protein']:.1f} g")
        st.metric("Grasas", f"{totals['fat']:.1f} g")
        st.metric("Carbohidratos", f"{totals['carbs']:.1f} g")
        
        # Metas personales
        st.subheader("Tus metas diarias")

        # Inicializar valores de session_state desde el perfil del usuario
        if "balance_activity" not in st.session_state:
            st.session_state.balance_activity = st.session_state.user.get("activity_level", "moderate")
        if "balance_goal" not in st.session_state:
            st.session_state.balance_goal = st.session_state.user.get("goal", "maintain")

        activity = st.selectbox(
            "Nivel de actividad",
            ["sedentary", "light", "moderate", "active"],
            key="balance_activity",
        )
        goal = st.selectbox(
            "Objetivo",
            ["maintain", "lose_weight", "gain_weight"],
            key="balance_goal",
        )

        col_save, col_calc = st.columns(2)
        with col_save:
            if st.button("Guardar cambios"):
                update_user_profile(
                    st.session_state.user["id"],
                    st.session_state.balance_activity,
                    st.session_state.balance_goal,
                )
                st.session_state.user["activity_level"] = st.session_state.balance_activity
                st.session_state.user["goal"] = st.session_state.balance_goal
                st.success("Cambios guardados correctamente.")

        with col_calc:
            if st.button("Calcular metas"):
                from src.goals import calc_bmr, calc_tdee, calc_targets
                bmr = calc_bmr(
                    st.session_state.user.get('sex', 'Male').lower(),
                    st.session_state.user.get('weight_kg', 75),
                    st.session_state.user.get('height_cm', 180),
                    st.session_state.user.get('age', 30)
                )
                tdee = calc_tdee(bmr, st.session_state.balance_activity)
                targets = calc_targets({
                    "age": st.session_state.user.get('age', 30),
                    "sex": st.session_state.user.get('sex', 'Male').lower(),
                    "weight_kg": st.session_state.user.get('weight_kg', 75),
                    "height_cm": st.session_state.user.get('height_cm', 180),
                    "activity_level": st.session_state.balance_activity,
                    "goal": st.session_state.balance_goal
                })

                # Guardar metas calculadas en BD para que la IA las use sin regenerar
                save_user_targets(
                    st.session_state.user["id"],
                    targets["kcal_goal"],
                    targets["protein_grams"],
                    targets["carbs_grams"],
                    targets["fat_grams"],
                    targets.get("fiber_grams", 0),
                )

                st.info(f"Kcal objetivo: {targets['kcal_goal']:.0f} kcal")
                st.info(f"Proteinas objetivo: {targets['protein_grams']:.1f} g")
                st.info(f"Carbohidratos objetivo: {targets['carbs_grams']:.1f} g")
                st.info(f"Grasas objetivo: {targets['fat_grams']:.1f} g")
                st.success("Metas guardadas. La IA las usará en tus recomendaciones.")
    
    elif menu == "Diario de comidas":
        st.title("Diario de comidas")
        
        # Fecha selector
        date_today = st.date_input("Fecha", value=datetime.now().date())
        date_str = date_today.strftime("%Y-%m-%d")
        
        # Mostrar lo registrado hoy
        st.subheader("Comidas registradas hoy")
        entries = get_entries_by_date(st.session_state.user["id"], date_str)
        
        if entries:
            total_kcal = 0
            total_protein = 0
            total_carbs = 0
            total_fat = 0
            
            for entry in entries:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{entry['food_name']} - {entry['grams']} {entry['unit']}")
                with col2:
                    st.write(f"{entry['kcal']:.0f} kcal")
                with col3:
                    if st.button("Eliminar", key=f"del_{entry['id']}"):
                        delete_entry(entry["id"], st.session_state.user["id"])
                        st.rerun()
                
                total_kcal += entry["kcal"]
                total_protein += entry["protein"]
                total_carbs += entry["carbs"]
                total_fat += entry["fat"]
            
            st.markdown("---")
            st.write("**Totales del día:**")
            st.write(f"Kcal: {total_kcal:.0f} kcal")
            st.write(f"Proteinas: {total_protein:.1f} g")
            st.write(f"Carbohidratos: {total_carbs:.1f} g")
            st.write(f"Grasas: {total_fat:.1f} g")
        else:
            st.info("No hay comidas registradas para hoy. Agrega tu primera comida abajo.")
        
        st.markdown("---")
        st.subheader("Añadir nueva comida")
        
        # Opción 1: Seleccionar de la base de datos
        st.write("**Opción 1: Seleccionar de la base de datos**")
        query = st.text_input("Buscar alimento para añadir", key="diary_search")
        if query:
            results = search_foods(query, st.session_state.user["id"])
            if results:
                st.write("Resultados:")
                for food in results[:5]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        unit_label = food[8]
                        st.write(f"{food[1]} - {food[3]} kcal/100g ({unit_label})")
                    with col2:
                        if unit_label == "unidad":
                            amount = st.number_input("Cantidad", min_value=1, value=1, step=1, key=f"grams_{food[0]}")
                        else:
                            amount = st.number_input("Gramos", min_value=1, value=100, key=f"grams_{food[0]}")
                        if st.button("Añadir", key=f"add_meal_{food[0]}"):
                            add_entry(
                                user_id=st.session_state.user["id"],
                                food_id=food[0],
                                grams=amount,
                                meal_type="comida",
                                unit=unit_label,
                            )
                            st.success(f"Añadido {amount} {unit_label} de {food[1]}")
                            st.rerun()
        
        # Opción 2: Agregar alimento personalizado
        st.write("**Opción 2: Agregar alimento personalizado**")
        with st.form("personalized_food_form"):
            p_name = st.text_input("Nombre del alimento")
            p_grams = st.number_input("Gramos que comiste", min_value=1, value=100)
            p_kcal_100 = st.number_input("Kcal por 100g (opcional)", min_value=0, value=100)
            p_protein_100 = st.number_input("Proteinas por 100g (opcional)", min_value=0, value=20)
            p_fat_100 = st.number_input("Grasas por 100g (opcional)", min_value=0, value=5)
            p_carbs_100 = st.number_input("Carbohidratos por 100g (opcional)", min_value=0, value=20)
            
            submit_p = st.form_submit_button("Añadir comida personalizada")
            if submit_p:
                # Calcular nutrientes basados en los porcentajes
                factor = p_grams / 100.0
                kcal = round(p_kcal_100 * factor, 2) if p_kcal_100 > 0 else 0
                protein = round(p_protein_100 * factor, 2) if p_protein_100 > 0 else 0
                fat = round(p_fat_100 * factor, 2) if p_fat_100 > 0 else 0
                carbs = round(p_carbs_100 * factor, 2) if p_carbs_100 > 0 else 0
                
                # Crear el alimento personalizado del usuario en el catálogo
                food_id = create_custom_food(
                    user_id=st.session_state.user["id"],
                    name=p_name,
                    category="personalizado",
                    kcal_100g=p_kcal_100,
                    carbs_100g=p_carbs_100,
                    fat_100g=p_fat_100,
                    protein_100g=p_protein_100,
                    fiber_100g=0,
                    unit="g",
                )
                
                # Registrar la entrada en el diario usando add_entry (maneja cálculo y unidad)
                add_entry(
                    user_id=st.session_state.user["id"],
                    food_id=food_id,
                    grams=p_grams,
                    meal_type="comida",
                    unit="g",
                )
                
                st.success(f"Añadida comida personalizada: {kcal:.0f} kcal, {protein:.1f}g proteinas")
                st.rerun()
    
    elif menu == "Mis alimentos":
        st.title("Mis alimentos")
        
        # Ver alimentos propios del usuario
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g FROM foods WHERE owner_user_id = ?", (st.session_state.user["id"],))
        user_foods = cur.fetchall()
        conn.close()
        
        st.write(f"Tus alimentos registrados ({len(user_foods)}):")
        
        if user_foods:
            for food in user_foods:
                # food: (id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g)
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{food[1]}** ({food[2]})")
                with col2:
                    st.write(f"{food[3]} kcal/100g")
                with col3:
                    if st.button("Eliminar", key=f"del_user_{food[0]}"):
                        # Eliminar del usuario
                        del_conn = get_connection()
                        del_cur = del_conn.cursor()
                        del_cur.execute("DELETE FROM foods WHERE id = ? AND owner_user_id = ?", (food[0], st.session_state.user["id"]))
                        del_conn.commit()
                        del_conn.close()
                        st.rerun()
        else:
            st.info("No tienes alimentos registrados aún. Usa la opción 'Añadir alimento' en el menú de diario.")
        
        st.markdown("---")
        st.write("Estadísticas rápidas de tus alimentos:")
        if user_foods:
            total_kcal = sum(f[3] for f in user_foods)  # kcal_100g
            st.write(f"Total de kcal base (por 100g de cada): {total_kcal:.0f} kcal")
    
    elif menu == "Recomendaciones IA":
        st.title("Recomendaciones de Nutrición")
        
        st.subheader("Tu perfil y metas")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Nombre: {st.session_state.user.get('name', '')}")
            st.write(f"Peso: {st.session_state.user.get('weight_kg', 0)} kg")
            st.write(f"Altura: {st.session_state.user.get('height_cm', 0)} cm")
        with col2:
            st.write(f"Edad: {st.session_state.user.get('age', 0)}")
            st.write(f"Objetivo: {st.session_state.user.get('goal', 'maintain')}")
            st.write(f"Actividad: {st.session_state.user.get('activity_level', 'moderate')}")
        
        st.markdown("---")
        
        if st.button("Generar recomendaciones"):
            with st.spinner("Generando recomendaciones..."):
                recomendaciones = get_recommendations(st.session_state.user["id"])
            st.session_state.ai_recommendations = recomendaciones
        
        if st.session_state.ai_recommendations:
            st.markdown(st.session_state.ai_recommendations)
        
        st.markdown("---")
        st.info("Estas recomendaciones son generales y se basan en tus datos registrados. Para un plan personalizado, consulta a un nutricionista.")
    
    elif menu == "Configuración":
        st.title("Configuración")
        
        st.write("Configuración de la app Nutri App 1.1")
        
        # Perfil de usuario
        st.subheader("Tu perfil")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"Edad: {st.session_state.user.get('age', 30)}")
            st.write(f"Peso: {st.session_state.user.get('weight_kg', 75)} kg")
        with col2:
            st.write(f"Altura: {st.session_state.user.get('height_cm', 180)} cm")
            st.write(f"Objetivo: {st.session_state.user.get('goal', 'maintain')}")
        
        # Configuración de IA
        st.subheader("Configuración de IA")
        provider = st.selectbox("Proveedor de IA", ["mock", "claude", "openrouter", "gemini"])
        if st.button("Aplicar configuración de IA"):
            set_ai_provider(provider)
            st.session_state.ai_provider = provider
            st.success(f"Proveedor set a: {provider}")
        
        st.info("Los datos se guardan localmente en data/app.db")
        
    elif menu == "Cerrar sesión":
        if st.button("Cerrar sesión"):
            st.session_state.user = None
            st.session_state.logged_in = False
            st.session_state.ai_recommendations = None
            st.rerun()


# Flujo principal
if not st.session_state.logged_in:
    login_screen()
else:
    main_app()