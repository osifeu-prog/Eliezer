from flask import Flask, request, jsonify
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookHandler:
    """מחלקה לטיפול בבקשות webhook מהאתר"""
    
    def __init__(self, crm_manager):
        self.crm_manager = crm_manager
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """הגדרת routes ל-webhook"""
        self.app.add_url_rule('/webhook/lead', 'handle_lead', self.handle_lead, methods=['POST'])
        self.app.add_url_rule('/webhook/status', 'check_status', self.check_status, methods=['GET'])
        self.app.add_url_rule('/health', 'health_check', self.health_check, methods=['GET'])
    
    def handle_lead(self):
        """טיפול בליד חדש מהאתר"""
        try:
            data = request.get_json()
            
            # וידוא שהנתונים הנדרשים קיימים
            if not data or 'name' not in data or 'phone' not in data:
                return jsonify({'error': 'Missing required fields: name, phone'}), 400
            
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
            
            return jsonify({
                'success': True,
                'lead_id': lead.id,
                'message': 'Lead added successfully'
            }), 201
            
        except Exception as e:
            logger.error(f"Error handling lead: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    def check_status(self):
        """בדיקת סטטוס ה-webhook"""
        return jsonify({
            'status': 'active',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Telegram CRM Bot'
        })
    
    def health_check(self):
        """בדיקת בריאות המערכת"""
        return jsonify({'status': 'healthy'})
    
    def is_active(self):
        """בדיקה אם ה-webhook פעיל"""
        return True
    
    def run(self, host='0.0.0.0', port=5000):
        """הרצת שרת ה-webhook"""
        self.app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    # לצורך בדיקה מקומית
    from crm_manager import CRMManager
    from database import DatabaseManager
    
    db = DatabaseManager()
    crm = CRMManager(db)
    handler = WebhookHandler(crm)
    handler.run()
