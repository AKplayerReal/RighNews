"""
سیستم انتخاب تصویر هوشمند بر اساس محتوای مقاله
از تصاویر پایدار Unsplash با URL مستقیم استفاده می‌کند
"""
import re
import hashlib
from typing import Optional

# کلمات کلیدی → دسته‌بندی موضوعی
KEYWORD_CATEGORIES = {
    # هوش مصنوعی عمومی
    "ai": ["artificial intelligence", "machine learning", "deep learning", "ai", "ml"],
    # مدل‌های زبانی
    "llm": ["gpt", "bert", "llm", "language model", "transformer", "attention", "few-shot", "prompt"],
    # بینایی کامپیوتر
    "vision": ["computer vision", "image", "vision", "object detection", "segmentation", "gan"],
    # شبکه‌های عصبی
    "neural": ["neural network", "cnn", "rnn", "lstm", "convolutional"],
    # داده و آموزش
    "data": ["dataset", "training data", "corpus", "benchmark", "evaluation"],
    # رباتیک
    "robot": ["robot", "robotics", "autonomous", "control"],
    # پردازش زبان طبیعی
    "nlp": ["nlp", "natural language", "text", "sentiment", "translation"],
    # ریاضی/الگوریتم
    "math": ["optimization", "algorithm", "gradient", "loss function", "bayesian"],
}

# تصاویر پایدار از Unsplash (هر دسته چند تصویر دارد)
IMAGES_BY_CATEGORY = {
    "ai": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1600&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1600&q=80",
        "https://images.unsplash.com/photo-1555255707-c07966088b7b?w=1600&q=80",
    ],
    "llm": [
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1600&q=80",
        "https://images.unsplash.com/photo-1509228627152-72ae9ae6848d?w=1600&q=80",
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1600&q=80",
    ],
    "vision": [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1600&q=80",
        "https://images.unsplash.com/photo-1561736778-92e52a7769ef?w=1600&q=80",
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=1600&q=80",
    ],
    "neural": [
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1600&q=80",
        "https://images.unsplash.com/photo-1545987796-200677ee1011?w=1600&q=80",
        "https://images.unsplash.com/photo-1558346490-a72e53ae2d4f?w=1600&q=80",
    ],
    "data": [
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1600&q=80",
        "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?w=1600&q=80",
    ],
    "robot": [
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1600&q=80",
        "https://images.unsplash.com/photo-1531747118685-8b983dcf3c82?w=1600&q=80",
    ],
    "nlp": [
        "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=1600&q=80",
        "https://images.unsplash.com/photo-1455390582262-044cdead277a?w=1600&q=80",
    ],
    "math": [
        "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1600&q=80",
        "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=1600&q=80",
    ],
    # پیش‌فرض
    "default": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1600&q=80",
        "https://images.unsplash.com/photo-1526374870839-e155464bb9f2?w=1600&q=80",
        "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?w=1600&q=80",
    ],
}


def detect_category(text: str) -> str:
    """تشخیص دسته‌بندی موضوعی از متن"""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in KEYWORD_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    
    if not scores:
        return "default"
    
    # دسته با بالاترین امتیاز
    return max(scores.items(), key=lambda x: x[1])[0]


def pick_image(title: str, content: str, article_id: Optional[int] = None) -> str:
    """
    انتخاب تصویر هوشمند برای یک مقاله.
    از article_id به عنوان seed استفاده می‌کند تا هر مقاله همیشه یک تصویر ثابت داشته باشد.
    """
    combined_text = f"{title} {content}"
    category = detect_category(combined_text)
    images = IMAGES_BY_CATEGORY.get(category, IMAGES_BY_CATEGORY["default"])
    
    # انتخاب deterministic بر اساس ID یا hash
    if article_id is not None:
        index = article_id % len(images)
    else:
        h = hashlib.md5(combined_text.encode()).hexdigest()
        index = int(h[:8], 16) % len(images)
    
    return images[index]


# تست سریع
if __name__ == "__main__":
    test_articles = [
        ("Attention Is All You Need", "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms"),
        ("Language Models are Few-Shot Learners", "GPT-3 achieves strong performance on many NLP datasets"),
        ("An Image is Worth 16x16 Words", "Vision Transformer for image recognition"),
    ]
    for title, content in test_articles:
        cat = detect_category(f"{title} {content}")
        img = pick_image(title, content, article_id=1)
        print(f"[{cat}] {title[:40]}... → {img[:60]}...")
