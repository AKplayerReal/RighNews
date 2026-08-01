from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI(title="Rayanews Core API")

class ArticleRequest(BaseModel):
    english_text: str

@app.get("/")
def read_root():
    return {"message": "Rayanews Core is alive!"}

@app.post("/translate-test")
async def translate_test(req: ArticleRequest):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing API Key")
    client = Groq(api_key=api_key)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Translate to Persian accurately."},
                {"role": "user", "content": req.english_text}
            ],
            model="llama3-8b-8192",
            temperature=0.2
        )
        return {"persian_translation": chat_completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
