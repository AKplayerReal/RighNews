"""
خط لوله اصلی پردازش مقالات
جمع‌آوری → ترجمه → راستی‌آزمایی → ذخیره‌سازی
"""
import arxiv
import re
import json
import os
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from openai import OpenAI
from database import engine, Article, ArticleEmbedding, SessionLocal
from sqlalchemy.orm import Session
from image_picker import pick_image
# ============================================
# ۱. ماژول جمع‌آوری (Collector)
# ============================================
class ArxivCollector:
    def __init__(self):
        self.client = arxiv.Client()
    
    def fetch_paper(self, arxiv_id: str) -> Optional[Dict]:
        """دریافت مقاله از arXiv"""
        try:
            # استخراج ID از URL اگر لازم بود
            if "arxiv.org" in arxiv_id:
                match = re.search(r'(\d{4}\.\d{4,5})', arxiv_id)
                if match:
                    arxiv_id = match.group(1)
            
            search = arxiv.Search(id_list=[arxiv_id])
            papers = list(self.client.results(search))
            
            if not papers:
                return None
            
            paper = papers[0]
            return {
                "source_url": paper.entry_id,
                "source_type": "arxiv",
                "title_english": paper.title,
                "content_english": paper.summary,
                "published_at": paper.published,
                "authors": [author.name for author in paper.authors[:5]],
                "categories": paper.categories,
            }
        except Exception as e:
            print(f"❌ Collector error: {e}")
            return None

# ============================================
# ۲. ماژول ترجمه (Translator)
# ============================================
class Translator:
    def __init__(self):
        api_key = os.getenv("GAPGPT_API_KEY")
        if not api_key:
            raise ValueError("GAPGPT_API_KEY not set!")
        self.client = OpenAI(
            base_url="https://api.gapgpt.app/v1",
            api_key=api_key
        )
        self.system_prompt = """You are a professional Persian (Farsi) tech journalist.

ABSOLUTE RULES:
1. Translate ONLY into Persian (Farsi) using the Persian script.
2. NEVER output Chinese, Japanese, Korean, or any non-Persian script.
3. Keep numbers, model names (GPT-3, BERT, M3), and proper nouns in English.
4. Use standard Persian technical terminology.
5. Output ONLY the translation — no explanations, no notes.

Correct examples:
- "Neural networks" → "شبکه‌های عصبی"
- "Attention mechanism" → "سازوکار توجه"

YOU MUST ALWAYS RESPOND IN PERSIAN."""

    @staticmethod
    def _has_chinese(text: str) -> bool:
        """تشخیص کاراکتر چینی در متن"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def translate_to_persian(self, text: str, context: str = "tech", max_retries: int = 2) -> str:
        """ترجمه با تلاش مجدد خودکار در صورت تشخیص چینی"""
        last = ""
        for attempt in range(max_retries + 1):
            try:
                user_msg = f"Translate the following English text into Persian:\n\n{text}"
                if attempt > 0:
                    user_msg = (
                        "IMPORTANT: Your previous output was in Chinese, which is WRONG. "
                        "Translate into PERSIAN (Farsi script) this time.\n\n" + user_msg
                    )
                completion = self.client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                )
                last = completion.choices[0].message.content
                if not self._has_chinese(last):
                    return last
                print(f"⚠️ Chinese detected (attempt {attempt + 1}), retrying...")
            except Exception as e:
                print(f"❌ Translation error: {e}")
                return f"[Translation Failed: {str(e)}]"
        return last

# ============================================
# ۳. ماژول راستی‌آزمایی (Fact-Checker)
# ============================================
class FactChecker:
    def __init__(self):
        # الگوهای regex برای استخراج اعداد و مشخصات فنی
        self.patterns = {
            "percentages": r'\b(\d+(?:\.\d+)?)\s*%',
            "numbers_with_units": r'\b(\d+(?:\.\d+)?)\s*(TB|GB|MB|KB|nm|mm|cm|kg|MHz|GHz|Hz|cores?|threads?)\b',
            "model_numbers": r'\b([A-Z]{2,}-?\d+[A-Z]?)\b',  # مثل RTX4090, M3, A100
            "dates": r'\b(20\d{2})\b',
        }
    
    def extract_facts(self, text: str) -> Dict[str, List[str]]:
        """استخراج اعداد و مشخصات فنی از متن"""
        facts = {}
        for category, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                facts[category] = list(set(matches))  # حذف تکراری‌ها
        return facts
    
    def verify_translation(self, 
                          english_text: str, 
                          persian_text: str) -> Tuple[bool, str]:
        """
        راستی‌آزمایی ترجمه: آیا اعداد و مشخصات فنی حفظ شده‌اند؟
        """
        english_facts = self.extract_facts(english_text)
        persian_facts = self.extract_facts(persian_text)
        
        issues = []
        
        # بررسی اینکه اعداد مهم انگلیسی در فارسی هم هستند
        for category, values in english_facts.items():
            for value in values:
                # تبدیل value به string برای جستجو
                value_str = str(value[0] if isinstance(value, tuple) else value)
                if value_str not in persian_text:
                    issues.append(f"{category}: '{value_str}' در ترجمه یافت نشد")
        
        if issues:
            return False, " | ".join(issues)
        return True, "✅ همه اعداد و مشخصات فنی حفظ شده‌اند"

# ============================================
# ۴. خط لوله اصلی (Pipeline)
# ============================================
class ArticleProcessor:
    def __init__(self):
        self.collector = ArxivCollector()
        self.translator = Translator()
        self.fact_checker = FactChecker()
    
    def process(self, arxiv_id: str) -> Dict:
        """پردازش کامل یک مقاله"""
        result = {
            "status": "processing",
            "steps": [],
            "article_id": None,
        }
        
        # مرحله ۱: جمع‌آوری
        paper = self.collector.fetch_paper(arxiv_id)
        if not paper:
            return {"status": "error", "error": "Paper not found"}
        
        result["steps"].append({"step": "collect", "status": "success"})
        result["collected"] = paper
        
        # مرحله ۲: ترجمه عنوان
        title_fa = self.translator.translate_to_persian(paper["title_english"])
        result["steps"].append({"step": "translate_title", "status": "success"})
        
        # مرحله ۳: ترجمه چکیده
        content_fa = self.translator.translate_to_persian(paper["content_english"])
        result["steps"].append({"step": "translate_content", "status": "success"})
        
        # مرحله ۴: راستی‌آزمایی چکیده
        verified, notes = self.fact_checker.verify_translation(
            paper["content_english"], 
            content_fa
        )
        result["steps"].append({
            "step": "fact_check", 
            "status": "success" if verified else "warning",
            "verified": verified,
            "notes": notes
        })
        # مرحله ۴.۵: انتخاب تصویر هوشمند
        image_url = pick_image(
            paper["title_english"],
            paper["content_english"],
            article_id=None  # چون هنوز ID نداریم
            )
        result["steps"].append({
            "step": "pick_image",
            "status": "success",
            "image_url": image_url,
        })
        # مرحله ۵: ذخیره در دیتابیس
        try:
            db = SessionLocal()
            
            # بررسی اینکه قبلاً ذخیره نشده
            existing = db.query(Article).filter(
                Article.source_url == paper["source_url"]
            ).first()
            
            if existing:
                article = existing
                result["steps"].append({
                    "step": "save", 
                    "status": "skipped",
                    "message": "Article already exists"
                })
            else:
                article = Article(
                    source_url=paper["source_url"],
                    source_type=paper["source_type"],
                    title_english=paper["title_english"],
                    title_persian=title_fa,
                    content_english=paper["content_english"],
                    content_persian=content_fa,
                    image_url=image_url,  # ← جدید
                    published_at=paper["published_at"],
                    verified=verified,
                    fact_check_notes=notes,
                    )
                
                db.add(article)
                db.commit()
                db.refresh(article)
                result["steps"].append({
                    "step": "save", 
                    "status": "success",
                    "message": "New article saved"
                })
            
            result["article_id"] = article.id
            db.close()
            
        except Exception as e:
            result["steps"].append({
                "step": "save", 
                "status": "error",
                "error": str(e)
            })
        
        # خروجی نهایی
        result["status"] = "success"
        result["output"] = {
            "id": result["article_id"],
            "title_english": paper["title_english"],
            "title_persian": title_fa,
            "content_english": paper["content_english"][:200] + "...",
            "content_persian": content_fa[:200] + "...",
            "verified": verified,
            "fact_check_notes": notes,
            "authors": paper["authors"],
            "published_at": str(paper["published_at"]),
        }
        
        return result

# تست سریع
if __name__ == "__main__":
    processor = ArticleProcessor()
    # تست با "Attention Is All You Need"
    result = processor.process("1706.03762")
    print(json.dumps(result, indent=2, ensure_ascii=False))
