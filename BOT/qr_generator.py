import qrcode
import io
from config import logger

def generate_user_qr(bot_username, user_id, campaign_source=None):
    """יוצר תמונת QR עם לינק אישי להפניה (Referral)"""
    
    # ה-Payload שיירשם ב-?start=
    payload = str(user_id)
    if campaign_source:
         # מאפשר מעקב קמפיינים עם referral
        payload = f"{campaign_source}_{user_id}"

    link = f"https://t.me/{bot_username}?start={payload}"
    logger.info(f"Generating QR for link: {link}")
    
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(link)
    qr.make(fit=True)
    
    img = qr.make_image(fill='black', back_color='white')
    
    # המרת התמונה ל-Bytes בזיכרון
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio
