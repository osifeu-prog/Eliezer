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
        if self.use_openai:
            try:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": user_text}]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI Error: {e}")
                return "מצטער, יש לי בעיה בתקשורת כרגע."
                
        elif self.use_hf:
            try:
                # דוגמה למודל פתוח ומהיר, ניתן להחליף
                output = self.hf_client.text_generation(
                    user_text, 
                    model="google/flan-t5-large", 
                    max_new_tokens=100
                )
                return output
            except Exception as e:
                logger.error(f"HuggingFace Error: {e}")
                return "מצטער, לא הצלחתי לעבד את הבקשה."
        
        return "מערכת ה-AI אינה מוגדרת כרגע."

ai_service = AIService()
