# Proyecto: App de nutrición local

## Stack (no cambiar sin pedirme)
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