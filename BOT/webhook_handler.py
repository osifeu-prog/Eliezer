from fastapi import FastAPI, HTTPException, Request
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

app = FastAPI(title="CRM Webhook Handler")

class WebhookHandler:
    """מחלקה לטיפול בבקשות webhook מהאתר"""
    
    def __init__(self, crm_manager):
        self.crm_manager = crm_manager
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', 'webhook-123')
    
    async def handle_lead(self, request: Request):
        """טיפול בליד חדש מהאתר"""
        try:
            data = await request.json()
            
            # וידוא שהנתונים הנדרשים קיימים
            if not data or 'name' not in data or 'phone' not in data:
                raise HTTPException(status_code=400, detail="Missing required fields: name, phone")
            
            # הוספת הליד ל-CRM
            lead = self.crm_manager.add_lead(
                name=data['name'],
                phone=data['phone'],
                email=data.get('email'),
                source=data.get('source', 'website'),
                notes=data.get('notes')
            )
            
            logger.info(f"New lead added: {lead.name} ({lead.phone})")
            
            # שליחת התראה למנהלים
            self.crm_manager.notify_new_lead(lead)
            
            return {
                'success': True,
                'lead_id': lead.id,
                'message': 'Lead added successfully'
            }
            
        except Exception as e:
            logger.error(f"Error handling lead: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def check_status(self):
        """בדיקת סטטוס ה-webhook"""
        return {
            'status': 'active',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Telegram CRM Bot'
        }
    
    async def health_check(self):
        """בדיקת בריאות המערכת"""
        return {'status': 'healthy'}

# יצירת handler גלובלי
from crm_manager import CRMManager
from database import DatabaseManager

db = DatabaseManager()
crm = CRMManager(db)
handler = WebhookHandler(crm)

@app.post("/{webhook_secret:path}")
async def webhook_endpoint(webhook_secret: str, request: Request):
    """Endpoint ראשי ל-webhook"""
    if webhook_secret != handler.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    return await handler.handle_lead(request)

@app.get("/{webhook_secret:path}/status")
async def status_endpoint(webhook_secret: str):
    """Endpoint לבדיקת סטטוס"""
    if webhook_secret != handler.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    return await handler.check_status()

@app.get("/health")
async def health_endpoint():
    """Endpoint לבדיקת בריאות"""
    return await handler.health_check()

@app.get("/")
async def root():
    """Endpoint ראשי"""
    return {
        "message": "CRM Webhook Handler is running",
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }
