import sqlite3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_connection


def test_tables_exist():
    # Usar una base temporal para el test
    tmp_db = "/tmp/test_app.db"
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    # Reemplazar temporalmente la ruta de la DB
    import src.db as db_mod
    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = tmp_db

    try:
        init_db()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        expected = {"users", "foods", "food_portions", "diary_entries", "weight_log"}
        assert expected.issubset(set(tables)), f"Faltan tablas. Tienes: {tables}"
        conn.close()
    finally:
        db_mod.DB_PATH = original_path
        if os.path.exists(tmp_db):
            os.remove(tmp_db)


if __name__ == "__main__":
    test_tables_exist()
    print("Test passed: all tables exist")