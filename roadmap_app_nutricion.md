# Roadmap: App local de nutrición con login por QR

Stack: **Python + Streamlit + SQLite (módulo `sqlite3` estándar) + `qrcode` + `opencv-python-headless`**
Objetivo de la v1: crear cuenta, recibir un QR, iniciar sesión escaneándolo, anotar comidas por alimento y gramos, ver el balance nutricional del día. La IA se agrega al final.

---

## 0. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Interfaz | Web local con Streamlit |
| Base de datos | SQLite, un solo archivo `data/app.db` |
| Nutrientes | Calorías, carbohidratos, grasas, proteína, fibra (por cada 100 g) |
| Alimentos | Ingredientes sueltos, más unos pocos platos (hamburguesa, perro caliente) |
| Alimentos propios | El usuario puede crear los suyos |
| Login | QR que contiene un **token aleatorio** (nunca datos de salud ni el ID real) |
| Varios usuarios | Cada uno tiene su QR permanente: inicia sesión, la cierra, entra otro usuario, y al volver encuentra todo donde lo dejó |
| QR perdido | Modo administrador (clave en `ADMIN_KEY`) que emite un QR nuevo sin perder los datos |
| IA | Fase final, recibe un resumen estructurado del historial |

### Sobre el login por QR (mi opinión honesta)
Es viable y está bien para un proyecto local, con tres matices:
1. **El QR funciona como una contraseña.** Quien tenga la imagen entra al perfil. Por eso el QR lleva un token largo y aleatorio (`secrets.token_urlsafe(32)`), y en la base de datos se guarda solo su **hash**, no el token.
2. **En Streamlit la webcam en vivo es frágil.** Lo más estable es `st.camera_input` (el usuario muestra el QR, toma la foto y la app la decodifica con OpenCV). Además deja siempre dos respaldos: subir la imagen del QR, o pegar el token como texto. Así nunca te quedas sin poder entrar si la cámara falla.
3. **El QR es permanente y sirve para varios usuarios en la misma máquina.** El flujo esperado es: usuario1 crea su cuenta y recibe su QR; inicia sesión escaneándolo; cierra sesión (los datos quedan en `app.db`); entra usuario2 con su QR y ve solo lo suyo; y usuario1 vuelve con el mismo QR y retoma su diario, metas e historial. El token no cambia ni se consume al usarlo. Para que esto sea seguro hay que cuidar tres cosas:
   - **Aislamiento:** al cerrar sesión se limpia todo `st.session_state`, y cada consulta filtra por el `user_id` de la sesión activa.
   - **Cámara:** `st.camera_input` puede dejar la última foto en pantalla, así que al cerrar sesión se reinicia el widget (cambiando su `key`).
   - **QR perdido:** como solo guardamos el hash, el token no se puede recuperar. Por eso hay un modo administrador (clave en la variable de entorno `ADMIN_KEY`) que genera un QR nuevo, invalida el anterior y conserva los datos.

### Sobre los datos de alimentos (lo que más errores puede causar)
- **Crudo vs cocido cambia todo.** Arroz crudo ≈ 360 kcal/100 g, cocido ≈ 130 kcal/100 g. Cada alimento debe indicar su estado en el nombre ("Arroz blanco cocido", "Arroz blanco crudo").
- **No dejes que la IA invente los valores nutricionales.** Si le pides "genera 200 alimentos con sus calorías", mezcla datos correctos con inventados. Lo seguro es importar de una fuente real (**USDA FoodData Central**, descarga CSV gratuita, o **Open Food Facts**) y solo usar la IA para traducir nombres o escribir el script de importación.
- Para empezar rápido: un CSV semilla de ~100 alimentos comunes, que **tú revisas** contra una fuente real antes de usarlo.
- Los líquidos (agua, 350 ml) se manejan en gramos con densidad 1, o con una columna `unidad` ("g" o "ml").

---

## 1. Estructura del proyecto

```
nutri-app/
├── AGENTS.md            # reglas para opencode (ver sección 2)
├── ROADMAP.md           # este archivo
├── requirements.txt
├── app.py               # punto de entrada de Streamlit
├── data/
│   ├── foods_seed.csv   # alimentos iniciales
│   └── app.db           # se crea solo (no subir a git)
├── qr_codes/            # QR generados (no subir a git)
├── src/
│   ├── db.py            # conexión y creación de tablas
│   ├── auth.py          # crear usuario, token, login
│   ├── qr_utils.py      # generar y leer QR
│   ├── foods.py         # buscar y crear alimentos
│   ├── diary.py         # registro de comidas y totales
│   ├── goals.py         # TMB, TDEE y metas por objetivo
│   └── ai_coach.py      # fase final
├── pages/               # páginas de Streamlit
└── tests/
```

---

## 2. Cómo hablarle a la IA (opencode)

### Reglas de oro
1. **Una fase por sesión.** Sesiones largas hacen que el modelo se confunda y reescriba cosas que ya funcionaban.
2. **Pídele primero el plan.** "Antes de escribir código, dime qué archivos vas a crear/modificar." Lo revisas y luego dices "adelante".
3. **Dile qué NO hacer.** Los modelos tienden a agregar cosas extra (login con contraseña, Docker, APIs). Limítalo explícitamente.
4. **Exige un criterio de "terminado" verificable.** "Ejecuta los tests y muéstrame que pasan", "ejecuta la app y dime cómo probarla".
5. **Haz commit de git después de cada fase que funcione.** Si la siguiente fase rompe algo, vuelves atrás.
6. **Pega el error completo** cuando algo falle, y pide primero la causa y luego el arreglo.
7. **Con modelos pequeños o gratuitos**, usa instrucciones más cortas y concretas, y una tarea a la vez. Con modelos más fuertes, úsalos para las fases difíciles (3, 4 y 7) o para revisar el trabajo de los otros.

### Contenido para `AGENTS.md` (opencode lo lee en cada sesión)

```markdown
# Proyecto: App de nutrición local

## Stack (no cambiar sin preguntarme)
Python 3.11+, Streamlit, SQLite con el módulo estándar `sqlite3`,
`qrcode[pil]`, `opencv-python-headless`, `pytest`.

## Reglas
- Mantén todo simple. No agregues Docker, FastAPI, ORMs, ni librerías nuevas sin pedirme permiso.
- Toda la lógica va en `src/`. Las páginas de Streamlit solo llaman funciones de `src/`.
- Usa type hints y docstrings cortos. Nombres de variables en inglés, textos de la interfaz en español.
- Todas las consultas SQL deben usar parámetros (`?`), nunca f-strings.
- Los valores nutricionales se guardan por 100 g. Nunca los inventes: vienen de CSV o los escribe el usuario.
- El QR contiene SOLO un token aleatorio. En la base de datos se guarda el hash (SHA-256) del token, nunca el token.
- Varios usuarios comparten la máquina: toda función que lea o escriba datos de usuario recibe el `user_id` de la sesión activa y filtra por él. Al cerrar sesión se limpia todo `st.session_state`.
- Secretos (como `ADMIN_KEY` o claves de API) se leen de variables de entorno o `.env`, nunca van escritos en el código.
- Después de cada cambio importante, ejecuta `pytest` y dime el resultado.
- Si algo es ambiguo, pregúntame antes de decidir.

## Nutrientes que importan
calorías (kcal), carbohidratos (g), grasas (g), proteína (g), fibra (g).
```

---

## 3. Fases (cada una con su prompt)

### Fase 0: Preparación del entorno
**Tú haces:** crear la carpeta, `git init`, entorno virtual, copiar `AGENTS.md`.

**Prompt:**
```
Lee AGENTS.md. Crea la estructura de carpetas del proyecto (src/, pages/, data/, qr_codes/, tests/),
un requirements.txt con las dependencias del stack, un .gitignore (que ignore data/app.db, qr_codes/ y el
entorno virtual y .env), un archivo .env.example (con ADMIN_KEY=cambia-esta-clave) y un app.py mínimo de Streamlit que muestre el título "Nutri App".
No escribas nada más. Dime cómo instalar y ejecutar.
```
**Terminado cuando:** `streamlit run app.py` abre la página en el navegador.

---

### Fase 1: Base de datos
**Prompt:**
```
Crea src/db.py con una función get_connection() y una función init_db() que cree estas tablas en data/app.db
si no existen:

- users: id, name, token_hash (único), age, sex, height_cm, weight_kg, activity_level, goal
  (lose_weight / gain_weight / lose_fat / maintain), created_at
- foods: id, name, category, kcal_100g, carbs_100g, fat_100g, protein_100g, fiber_100g,
  unit ('g' o 'ml'), owner_user_id (NULL si es del catálogo general), created_at
- food_portions: id, food_id, label (ej. "1 huevo mediano"), grams
- diary_entries: id, user_id, food_id, grams, meal_type (breakfast/lunch/dinner/snack), eaten_at
- weight_log: id, user_id, weight_kg, logged_at

Activa foreign keys. Llama init_db() al arrancar app.py.
Escribe un test en tests/test_db.py que cree una base temporal y verifique que las tablas existen.
No agregues nada más.
```
**Terminado cuando:** el test pasa y se crea `data/app.db`.

---

### Fase 2: Catálogo de alimentos
**Antes del prompt, tú haces:** crear `data/foods_seed.csv` con columnas
`name,category,kcal_100g,carbs_100g,fat_100g,protein_100g,fiber_100g,unit`. Llénalo con ~100 alimentos
copiando de USDA/Open Food Facts o de las etiquetas, y revisa los valores. (Si quieres, pídele a otra IA
solo el *script* para convertir un CSV de USDA a este formato, no los valores.)

**Prompt:**
```
Crea src/foods.py con:
- load_seed_foods(csv_path): carga data/foods_seed.csv en la tabla foods solo si la tabla está vacía.
- search_foods(query, user_id): busca por nombre sin importar mayúsculas ni tildes, devuelve alimentos
  del catálogo general y los propios del usuario, máximo 20 resultados.
- create_custom_food(user_id, ...): crea un alimento propio con los 5 nutrientes por 100 g.
- calc_nutrition(food, grams): devuelve kcal, carbs, grasas, proteína y fibra para esa cantidad de gramos.
Escribe tests: calc_nutrition con 200 g de un alimento conocido, y búsqueda con tildes ("platano" encuentra "Plátano").
Llama load_seed_foods al iniciar la app. No hagas interfaz todavía.
```
**Terminado cuando:** los tests pasan y la tabla `foods` tiene datos.

---

### Fase 3: Cuentas y QR (la parte más importante de validar)
**Prompt:**
```
Crea src/qr_utils.py y src/auth.py.

qr_utils.py:
- generate_qr_image(token) -> imagen PIL del QR.
- decode_qr_from_image(image_bytes) -> str | None, usando cv2.QRCodeDetector (sin pyzbar).

auth.py:
- create_user(name, age, sex, height_cm, weight_kg, activity_level, goal) -> (user_id, token).
  El token se genera con secrets.token_urlsafe(32). En la base solo se guarda su SHA-256.
  El token en claro se devuelve UNA sola vez.
- login_with_token(token) -> user | None, comparando hashes.

Interfaz en Streamlit (pages/ o app.py, tú decides lo más simple):
- Pantalla de inicio con dos opciones: "Crear cuenta" e "Iniciar sesión".
- Crear cuenta: formulario, al enviarlo muestra el QR, un botón para descargarlo como PNG y un aviso:
  "Guarda este QR, es tu llave de acceso".
- Iniciar sesión: tres métodos: (1) st.camera_input para mostrar el QR, (2) subir imagen del QR,
  (3) pegar el token como texto. Si el token es válido, guarda el usuario en st.session_state.
- Botón "Cerrar sesión".

Tests: crear usuario, generar QR, decodificarlo y verificar que login_with_token funciona; y que un token
falso devuelve None.
Requisitos adicionales:
- Al cerrar sesión, limpia todo st.session_state y reinicia el widget de cámara (cambia su key) para que no quede
  la foto del QR anterior.
- Todas las funciones que lean o escriban datos de usuario reciben el user_id de la sesión activa y filtran por él.
- El QR es permanente: iniciar sesión no lo cambia ni lo consume.
- Test de cambio de usuarios: crear usuario A y B, registrar datos distintos, iniciar sesión como A, cerrar,
  iniciar como B, y verificar que B no ve nada de A; luego volver a A con su mismo QR y verificar que sus datos
  siguen intactos.
- Modo administrador: una página protegida por una clave definida en la variable de entorno ADMIN_KEY, que permita
  regenerar el QR de un usuario (token nuevo, hash anterior invalidado, datos intactos). Test: después de regenerar,
  el token viejo ya no inicia sesión y el nuevo sí, con los mismos datos.

No agregues contraseñas ni correo.
```
**Terminado cuando:** pruebas tu escenario completo a mano: usuario1 crea cuenta y descarga su QR, cierra sesión, usuario2 crea la suya y entra con su QR, cierra sesión, y usuario1 vuelve con el mismo QR y ve sus datos. Además el test de cambio de usuarios pasa.
**Esta fase responde si el proyecto es viable.** Si la cámara da problemas, el respaldo de subir imagen/pegar token ya cubre el flujo.

---

### Fase 4: Diario de comidas
**Prompt:**
```
Crea src/diary.py y la página del diario (solo accesible con sesión iniciada).

diary.py:
- add_entry(user_id, food_id, grams, meal_type, eaten_at)
- delete_entry(entry_id, user_id)
- get_entries_by_date(user_id, date) con el nombre del alimento y los nutrientes calculados
- get_daily_totals(user_id, date) -> kcal, carbs, grasas, proteína, fibra

Página "Diario":
- Selector de fecha (por defecto hoy).
- Formulario: tipo de comida (desayuno/almuerzo/cena/snack), buscador de alimento (st.selectbox con resultados
  de search_foods), campo de cantidad en gramos o ml (o porción si el alimento tiene food_portions), botón "Agregar".
- Tabla con lo registrado del día agrupado por tipo de comida, con botón para eliminar cada entrada.
- Fila de totales del día.

Tests: add_entry + get_daily_totals con valores calculados a mano (ej. 200 g de arroz + 140 g de carne).
```
**Terminado cuando:** registras tu almuerzo de ejemplo (arroz, carne, aguacate, agua) y los totales coinciden con tu cálculo manual.

---

### Fase 5: Metas y balance nutricional
**Prompt:**
```
Crea src/goals.py:
- calc_bmr(sex, weight_kg, height_cm, age) con la fórmula Mifflin-St Jeor.
- calc_tdee(bmr, activity_level) con factores estándar (sedentary 1.2, light 1.375, moderate 1.55, active 1.725).
- calc_targets(user): devuelve kcal objetivo y gramos de proteína, carbos, grasas y fibra según el objetivo:
  lose_weight: déficit moderado (~15%), lose_fat: déficit moderado (~15-20%) con proteína alta (~2 g/kg),
  gain_weight: superávit moderado (~10-15%), maintain: TDEE.
  Incluye un piso mínimo de seguridad para las calorías (no recomendar por debajo de un mínimo razonable).
- Deja los porcentajes como constantes al inicio del archivo para poder ajustarlos fácil.

Página "Mi balance":
- Para el día elegido: barras de progreso de cada nutriente (consumido vs meta).
- Gráfico de calorías de los últimos 7 días.
- Un aviso fijo: "Orientación general, no reemplaza a un profesional de la salud."

Tests con un usuario de ejemplo y resultados calculados a mano.
```
**Terminado cuando:** los números del TDEE coinciden con una calculadora online conocida.

---

### Fase 6: Alimentos propios y porciones
**Prompt:**
```
Agrega en la interfaz:
- Página "Mis alimentos": formulario para crear un alimento propio (nombre, categoría, los 5 nutrientes por 100 g,
  unidad g o ml, y opcionalmente porciones como "1 unidad = 50 g"), y lista de los que ya creó con opción de editar/eliminar.
- En el Diario, si el buscador no encuentra el alimento, muestra un enlace "Crear alimento propio".
- Validaciones: valores numéricos >= 0, nombre obligatorio, y avisar si kcal no coincide aproximadamente
  con 4*carbos + 4*proteína + 9*grasas (solo advertencia, sin bloquear).
Un usuario solo puede ver y editar sus propios alimentos.
Tests de permisos: el usuario A no puede editar el alimento del usuario B.
```

---

### Fase 7: Módulo de IA
(Cuando todo lo anterior funcione y esté en git.)

**Prompt:**
```
Crea src/ai_coach.py.
- build_user_context(user_id, days=7): devuelve un diccionario con perfil (edad, sexo, peso, altura, objetivo),
  metas diarias, y por cada día los totales consumidos y los alimentos registrados.
- ask_coach(user_id, question): envía ese contexto + la pregunta del usuario a un LLM por API
  (la clave se lee de una variable de entorno, nunca en el código) y devuelve la respuesta.
- El prompt de sistema debe decir: eres un asistente de nutrición, usa SOLO los datos del contexto,
  no inventes valores nutricionales, no des diagnósticos médicos, no recomiendes dietas extremas
  ni por debajo del mínimo calórico, y sugiere consultar a un profesional ante condiciones médicas
  o señales de trastornos alimentarios.
Página "Asistente": cuadro de pregunta, respuesta, y botones rápidos ("¿Cómo voy hoy?", "¿Qué me falta de proteína?",
"Sugiere una cena para completar mis metas").
Haz que el proveedor del modelo sea configurable (Claude API u OpenRouter) en un solo lugar.
```

---

### Fase 8: Pulido
- Respaldo de la base de datos (botón "exportar copia" o script).
- Permitir que el propio usuario regenere su QR estando con sesión iniciada (el modo administrador de la Fase 3 ya cubre el caso del QR perdido).
- Registro de peso y gráfico de evolución.
- Revisión final de errores: pedirle a un modelo fuerte que revise `src/` buscando bugs y problemas de seguridad.

---

## 4. Lista de verificación rápida por fase
- [ ] La app arranca sin errores
- [ ] `pytest` pasa
- [ ] Probé el flujo a mano en el navegador
- [ ] `git commit` hecho
- [ ] Nueva sesión de opencode para la siguiente fase
