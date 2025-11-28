import qrcode
import io

def generate_user_qr(bot_username, user_id):
    # הלינק לבוט עם פרמטר start שמכיל את ה-ID של הממליץ
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(link)
    qr.make(fit=True)
    
    img = qr.make_image(fill='black', back_color='white')
    
    # המרת התמונה ל-Bytes בזיכרון כדי לשלוח לטלגרם בלי לשמור קובץ
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio
