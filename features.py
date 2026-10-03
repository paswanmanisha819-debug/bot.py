import os
import random
from groq import Groq
import re
import asyncio
import logging
from youtube_transcript_api import YouTubeTranscriptApi
import time
from typing import List, Dict
from duckduckgo_search import DDGS

# Telemetry & Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EliteWebResearchEngine:
    """
    Ultra-Advanced Web Scraping Engine with In-Memory LRU Caching & Multi-Threading.
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

    def _fetch_results_sync(self, query: str) -> List[Dict[str, str]]:
        """
        Synchronous core engine that runs in an isolated background thread 
        to prevent blocking the main Telegram event loop.
        """
        extracted_data = []
        try:
            # Using the new DDGS architecture compliant with v8.1+
            with DDGS() as ddgs:
                results = ddgs.text(
                    keywords=query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=self.max_results
                )
                for result in results:
                    extracted_data.append({
                        "title": result.get("title", "Unknown Node"),
                        "snippet": result.get("body", "No description."),
                        "domain": result.get("href", "").split("/")[2] if "//" in result.get("href", "") else "web"
                    })
        except Exception as e:
            logger.error(f"Search Engine Sync Error: {str(e)}")
            
        return extracted_data

    async def execute_deep_search(self, query: str) -> List[Dict[str, str]]:
        self._clean_cache()
        
        normalized_query = query.lower().strip()
        if normalized_query in self._query_cache:
            logger.info(f"Cache Hit for query: {normalized_query}")
            return self._query_cache[normalized_query]['data']

        # ⚡ PRO LEVEL: Pushing the search task to a background CPU thread
        extracted_data = await asyncio.to_thread(self._fetch_results_sync, query)
            
        if extracted_data:
            self._query_cache[normalized_query] = {
                'data': extracted_data,
                'timestamp': time.time()
            }
            
        return extracted_data

    async def generate_stealth_context(self, query: str) -> tuple:
        """
        Compiles web data for the LLM without exposing raw URLs to the end-user.
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

logger = logging.getLogger(__name__)

class EliteYouTubeExtractor:
    """
    Ultra-Advanced YouTube Cognitive Extractor.
    Engineered to bypass download restrictions and extract raw transcripts 
    using background threading and Regex optimization.
    """
    
    @staticmethod
    def _extract_video_id(url: str) -> str:
        """Advanced Regex to extract Video ID from ANY YouTube URL format."""
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None

    @staticmethod
    def _fetch_transcript_sync(video_id: str) -> str:
        """
        Synchronous core to extract subtitles with timestamps.
        Prioritizes English, then Hindi, and formats it securely.
        """
        try:
            # Fetching transcript (fallback to hindi if english not found)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi', 'en-IN'])
            
            full_text = ""
            for index, item in enumerate(transcript_list):
                # Protection: Capping at 300 lines to prevent AI Token Overflow (approx 30 mins of video)
                if index > 300: 
                    full_text += "\n[SYSTEM ALERT: Transcript truncated to prevent memory overflow.]"
                    break
                    
                minutes = int(item['start'] // 60)
                seconds = int(item['start'] % 60)
                full_text += f"[{minutes:02d}:{seconds:02d}] {item['text']}\n"
                
            return full_text
        except Exception as e:
            logger.error(f"Transcript Error for {video_id}: {str(e)}")
            return "ERROR: Transcript disabled by the creator or video is unavailable."

    async def analyze_video(self, url: str) -> str:
        """Asynchronous wrapper to prevent main thread blocking."""
        video_id = self._extract_video_id(url)
        if not video_id:
            return "ERROR: Invalid YouTube URL structure."
        
        # ⚡ PRO LEVEL: Pushing extraction to a background CPU thread
        transcript = await asyncio.to_thread(self._fetch_transcript_sync, video_id)
        return transcript

# Global Singleton Instance
yt_extractor = EliteYouTubeExtractor()

