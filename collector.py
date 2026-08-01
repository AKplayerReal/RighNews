"""
ماژول جمع‌آوری مقالات از arXiv
"""
import arxiv
import re
from typing import Dict, Optional, List
from datetime import datetime

class ArxivCollector:
    """جمع‌آوری مقالات از arXiv"""
    
    def __init__(self):
        self.client = arxiv.Client()
    
    def fetch_paper(self, arxiv_id: str) -> Optional[Dict]:
        """
        دریافت یک مقاله با شناسه یا URL arXiv
        مثال: "1706.03762" یا "https://arxiv.org/abs/1706.03762"
        """
        try:
            # استخراج شناسه از URL
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
                "pdf_url": paper.pdf_url,
                "doi": paper.doi
            }
            
        except Exception as e:
            print(f"❌ Error fetching paper: {e}")
            return None

# تست سریع
if __name__ == "__main__":
    collector = ArxivCollector()
    paper = collector.fetch_paper("1706.03762")  # Attention Is All You Need
    if paper:
        print(f"✅ Found: {paper['title_english'][:100]}...")
