import cv2
import numpy as np
from PIL import Image
import secrets


def generate_qr_image(token: str) -> Image:
    """Genera una imagen PIL del QR que contiene el token."""
    import qrcode
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")
    return img


def decode_qr_from_image(image_bytes) -> str | None:
    """Decodifica un QR desde bytes de imagen usando OpenCV.
    Retorna el token si se encuentra, None en caso contrario."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None
    
    detector = cv2.QRCodeDetector()
    data, bbox, straight_qr = detector.detectAndDecode(img)
    
    if data:
        return data
    return None