import os
import random
from groq import Groq
import asyncio
import logging
import time
from typing import List, Dict
from duckduckgo_search import AsyncDDGS

# Telemetry & Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EliteWebResearchEngine:
    """
    Ultra-Advanced Asynchronous Web Scraping Engine with In-Memory LRU Caching.
    Engineered for zero-latency repetitive queries and stealth data extraction.
    """
    
    def __init__(self, timeout: int = 15, max_results: int = 6):
        self.timeout = timeout
        self.max_results = max_results
        self.region = "wt-wt"
        self.safesearch = "moderate"
        self._query_cache: Dict[str, Dict] = {}
        self._cache_ttl = 3600  # Cache retention: 1 Hour

    def _clean_cache(self):
        """Internal Garbage Collection to prevent memory overflow."""
        current_time = time.time()
        expired_keys = [k for k, v in self._query_cache.items() if current_time - v['timestamp'] > self._cache_ttl]
        for k in expired_keys:
            del self._query_cache[k]

    async def execute_deep_search(self, query: str) -> List[Dict[str, str]]:
        self._clean_cache()
        
        normalized_query = query.lower().strip()
        if normalized_query in self._query_cache:
            logger.info(f"Cache Hit for query: {normalized_query}")
            return self._query_cache[normalized_query]['data']

        extracted_data: List[Dict[str, str]] = []
        
        try:
            async with AsyncDDGS() as ddgs:
                search_routine = ddgs.text(
                    keywords=query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=self.max_results
                )
                
                async for result in search_routine:
                    extracted_data.append({
                        "title": result.get("title", "Unknown Node"),
                        "snippet": result.get("body", "No description."),
                        "domain": result.get("href", "").split("/")[2] if "//" in result.get("href", "") else "web"
                    })
            
            if extracted_data:
                self._query_cache[normalized_query] = {
                    'data': extracted_data,
                    'timestamp': time.time()
                }
                    
        except asyncio.TimeoutError:
            logger.error(f"Search Engine Timeout: {query}")
        except Exception as e:
            logger.error(f"Critical Subsystem Failure: {str(e)}")
            
        return extracted_data

    async def generate_stealth_context(self, query: str) -> tuple:
        """
        Compiles web data for the LLM without exposing raw URLs to the end-user.
        Returns (Context String, Number of Sources Scanned).
        """
        raw_results = await self.execute_deep_search(query)
        
        if not raw_results:
            return "SYSTEM WARNING: Real-time data unavailable. Rely on internal knowledge.", 0
            
        context_string = "[REAL-TIME WEB DATA CONTEXT]\n"
        
        for index, item in enumerate(raw_results, start=1):
            context_string += f"Data Node [{index}] ({item['domain']}): {item['title']} - {item['snippet']}\n"
            
        return context_string, len(raw_results)

# Global Singleton Instance
research_engine = EliteWebResearchEngine()

# अपनी API Key यहाँ रखना मत भूलना
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_ai_generated_quiz(student_class):
    # AI को एकदम सख्त निर्देश कि फॉर्मेट कैसा होना चाहिए
    prompt = (f"Generate an objective multiple-choice question for a {student_class} CBSE student.\n"
              f"Format it EXACTLY like this:\n\n"
              f"Question Text Here?\n"
              f"A) Option 1\nB) Option 2\nC) Option 3\nD) Option 4\n\n"
              f"||Correct Answer: [Write Answer Here]||")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            CHAT_MODEL = "openai/gpt-oss-120b",
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return "⚠️ Server is busy taking a nap! Please try again."
        
def get_ai_generated_quiz_from_image(base64_image):
    prompt = (
        "Analyze this educational image/diagram and generate exactly ONE high-quality multiple-choice question (MCQ) based on it. "
        "The question should test the student's understanding of the diagram. Include 4 options (A, B, C, D).\n"
        "IMPORTANT: You MUST format the correct answer at the very end exactly like this on a new line: \n\nANSWER: (Correct Option)"
    )
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            CHAT_MODEL = "openai/gpt-oss-120b",
        )
        text = chat_completion.choices[0].message.content.strip()
        
        # पाइथन मैजिक: ANSWER: वाले हिस्से को ढूंढकर छुपाना (Spoiler पट्टी)
        if "ANSWER:" in text:
            question_part, answer_part = text.split("ANSWER:", 1)
            return f"{question_part.strip()}\n\n||ANSWER: {answer_part.strip()}||"
        else:
            lines = [line for line in text.split("\n") if line.strip() != ""]
            if len(lines) > 0:
                lines[-1] = f"||{lines[-1]}||"
            return "\n".join(lines)
            
    except Exception as e:
        return f"⚠️ Quiz Generation Error: {str(e)}"
            
        

