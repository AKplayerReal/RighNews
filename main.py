from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI(title="RighNews Core API")

class ArticleRequest(BaseModel):
    english_text: str

@app.get("/")
def read_root():
    return {"message": "RighNews Core is alive! 🚀"}

@app.post("/translate-test")
async def translate_test(req: ArticleRequest):
    api_key = os.getenv("GAPGPT_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GAPGPT_API_KEY is missing in Gerdoo!")
    
    # اتصال به API اختصاصی GapGPT
    client = OpenAI(
        base_url="https://api.gapgpt.app/v1",
        api_key=api_key
    )
    
    try:
        chat_completion = client.chat.completions.create(
            model="gemma-3-27b-it",
            messages=[
                {
                    "role": "system", 
                    "content": "تو یک روزنامه‌نگار حرفه‌ای فناوری هستی. متن انگلیسی زیر را به فارسی روان و دقیق ترجمه کن. از اصطلاحات استاندارد فناوری فارسی استفاده کن. هیچ توضیح اضافی یا احوال‌پرسی اضافه نکن."
                },
                {"role": "user", "content": req.english_text}
            ],
            temperature=0.2
        )
        return {"persian_translation": chat_completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GapGPT API Error: {str(e)}")
