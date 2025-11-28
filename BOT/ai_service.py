import openai
from huggingface_hub import InferenceClient
from config import OPENAI_API_KEY, HF_API_TOKEN, logger

class AIService:
    def __init__(self):
        self.use_openai = False
        self.use_hf = False
        
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
            self.use_openai = True
        elif HF_API_TOKEN:
            self.hf_client = InferenceClient(token=HF_API_TOKEN)
            self.use_hf = True
            
    async def get_response(self, user_text):
        """שולף תגובה מ-AI (נותן עדיפות ל-OpenAI)"""
        
        # תגובה פשוטה אם אף מפתח לא מוגדר
        if not self.use_openai and not self.use_hf:
            return "מערכת ה-AI אינה מוגדרת כרגע. אנא פנה לתמיכה."

        # שימוש ב-OpenAI
        if self.use_openai:
            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": user_text}]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI Error: {e}")
                
        # שימוש ב-HuggingFace כחלופה/גיבוי
        if self.use_hf:
            try:
                # מומלץ להשתמש במודל פתוח ומהיר, לדוגמה:
                output = self.hf_client.text_generation(
                    user_text, 
                    model="google/flan-t5-large", # ניתן להחליף למודל בעברית טוב יותר
                    max_new_tokens=100
                )
                return output
            except Exception as e:
                logger.error(f"HuggingFace Error: {e}")
        
        return "מצטער, חווינו שגיאה בכל המערכות החכמות."

ai_service = AIService()
