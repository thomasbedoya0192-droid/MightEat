import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import create_user, login_with_token
from src.qr_utils import generate_qr_image, decode_qr_from_image
import io
from src.db import init_db


def test_create_user_and_login():
    """Test: crear usuario, generar QR, decodificarlo y verificar login."""
    # Crear usuario
    user_id, token = create_user('Test User', 30, 'Male', 180, 75, 'maintain', 'maintain')
    assert user_id is not None
    assert token is not None
    assert isinstance(token, str)
    
    # Probar login con token correcto
    user = login_with_token(token)
    assert user is not None
    assert user['name'] == 'Test User'
    
    # Probar login con token falso
    user_false = login_with_token('token_que_no_existe_para_prueba')
    assert user_false is None


def test_qr_generate_and_decode():
    """Test: generar QR y decodificarlo debería devolver el token original."""
    from src.auth import create_user
    
    # Inicializar base de datos
    init_db()
    
    # Crear usuario para obtener un token
    user_id, token = create_user('QR Test', 25, 'Female', 165, 60, 'light', 'maintain')
    
    # Generar QR
    qr_img = generate_qr_image(token)
    
    # Convertir a bytes
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    image_bytes = buffer.read()
    
    # Decodificar QR
    decoded = decode_qr_from_image(image_bytes)
    assert decoded == token, f"Expected {token}, got {decoded}"


def test_qr_decode_returns_none_on_invalid():
    """Test: decodificar una imagen sin QR debería retornar None."""
    import numpy as np
    
    # Crear una imagen en blanco
    nparr = np.zeros((100, 100, 3), dtype=np.uint8)
    from PIL import Image
    img = Image.fromarray(nparr)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    decoded = decode_qr_from_image(buffer.read())
    assert decoded is None