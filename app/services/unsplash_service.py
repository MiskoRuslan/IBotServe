import os
import aiohttp
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class UnsplashService:
    """Service for fetching photos from Unsplash API"""

    def __init__(self):
        self.access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.api_url = "https://api.unsplash.com/photos/random"
        self.enabled = bool(self.access_key)

        if not self.access_key:
            print("[UnsplashService] WARNING: UNSPLASH_ACCESS_KEY not set - photo sending disabled")
            print("[UnsplashService] Add UNSPLASH_ACCESS_KEY to .env or docker-compose.yml to enable")

    def extract_keywords(self, text: str) -> str:
        """
        Extract meaningful keywords from text for image search.
        Makes photos look more casual/funny/meme-like as if from user's gallery.
        """
        import random

        # Remove URLs, mentions, hashtags
        text = re.sub(r'http\S+|@\S+|#\S+', '', text)

        # Expanded keywords with car-specific terms
        # Ukrainian keywords
        ukr_keywords = {
            # Cars & auto
            'автомобіль': 'car', 'машина': 'car', 'авто': 'car',
            'мерседес': 'mercedes', 'мерс': 'mercedes', 'бмв': 'bmw',
            'w204': 'mercedes', 'w205': 'mercedes', 'w212': 'mercedes',
            'w213': 'mercedes', 'w221': 'mercedes', 'w222': 'mercedes',
            'двигун': 'car engine', 'мотор': 'engine',
            'тюнінг': 'car tuning', 'чіп': 'car tuning',
            'підвіска': 'car suspension', 'гальма': 'car brakes',
            'колеса': 'car wheels', 'шини': 'tires',
            'бампер': 'car bumper', 'фара': 'car lights',
            'салон': 'car interior', 'багажник': 'car trunk',
            'двері': 'car door', 'капот': 'car hood',
            'гбо': 'car lpg', 'газ': 'car gas',
            'акумулятор': 'car battery', 'стартер': 'car starter',
            # Nature & places
            'природа': 'nature', 'ліс': 'forest', 'дерево': 'tree',
            'місто': 'city street', 'будинок': 'building', 'вулиця': 'street',
            'море': 'sea', 'океан': 'ocean', 'пляж': 'beach',
            'гори': 'mountains', 'небо': 'sky', 'захід': 'sunset',
            # Food & drinks
            'їжа': 'food', 'кава': 'coffee', 'чай': 'tea',
            'піца': 'pizza', 'бургер': 'burger',
            # Animals
            'собака': 'dog', 'кіт': 'cat', 'тварина': 'animal',
            # Tech & work
            'технологія': 'technology', 'компьютер': 'computer',
            'телефон': 'phone', 'ноутбук': 'laptop',
            'робота': 'work', 'офіс': 'office',
            # Sports & leisure
            'спорт': 'sports', 'футбол': 'football',
            'мандрівка': 'travel', 'подорож': 'travel',
            'квіти': 'flowers', 'сад': 'garden',
        }

        # Russian keywords (similar expanded set)
        rus_keywords = {
            'автомобиль': 'car', 'машина': 'car', 'авто': 'car',
            'мерседес': 'mercedes', 'мерс': 'mercedes', 'бмв': 'bmw',
            'w204': 'mercedes', 'w205': 'mercedes', 'w212': 'mercedes',
            'w213': 'mercedes', 'w221': 'mercedes', 'w222': 'mercedes',
            'двигатель': 'car engine', 'мотор': 'engine',
            'тюнинг': 'car tuning', 'чип': 'car tuning',
            'подвеска': 'car suspension', 'тормоза': 'car brakes',
            'колеса': 'car wheels', 'шины': 'tires',
            'бампер': 'car bumper', 'фара': 'car lights',
            'салон': 'car interior', 'багажник': 'car trunk',
            'гбо': 'car lpg', 'газ': 'car gas',
            'аккумулятор': 'car battery',
            'природа': 'nature', 'лес': 'forest',
            'город': 'city street', 'улица': 'street',
            'море': 'sea', 'пляж': 'beach',
            'горы': 'mountains', 'закат': 'sunset',
            'еда': 'food', 'кофе': 'coffee',
            'собака': 'dog', 'кот': 'cat',
            'технология': 'technology', 'компьютер': 'computer',
            'спорт': 'sports', 'футбол': 'football',
            'путешествие': 'travel',
        }

        # Combine dictionaries
        all_keywords = {**ukr_keywords, **rus_keywords}

        # Convert to lowercase for matching
        text_lower = text.lower()

        # Find first matching keyword
        base_keyword = None
        for keyword, english in all_keywords.items():
            if keyword in text_lower:
                base_keyword = english
                break

        # If no keyword found, use random casual keyword
        if not base_keyword:
            casual_keywords = ['car', 'city street', 'coffee', 'sunset', 'nature']
            base_keyword = random.choice(casual_keywords)

        # Add variation to make photos more casual/meme-like
        # 50% chance to add "meme" or "funny" modifier
        if random.random() < 0.5:
            modifiers = ['meme', 'funny', 'humor']
            modifier = random.choice(modifiers)
            return f"{base_keyword} {modifier}"
        else:
            # Otherwise return base keyword
            return base_keyword

    async def get_random_photo(self, keyword: Optional[str] = None) -> Optional[dict]:
        """
        Fetch a random photo from Unsplash.

        Args:
            keyword: Search keyword (optional)

        Returns:
            Dict with photo info or None if failed
        """
        if not self.enabled:
            return None

        try:
            headers = {
                "Authorization": f"Client-ID {self.access_key}"
            }

            params = {
                "count": 1,
                "orientation": "landscape"
            }

            if keyword:
                params["query"] = keyword

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"[UnsplashService] API error: {response.status} - {error_text}")
                        return None

                    data = await response.json()

                    if not data or len(data) == 0:
                        print(f"[UnsplashService] No photos found for keyword: {keyword}")
                        return None

                    photo = data[0]

                    return {
                        "url": photo["urls"]["regular"],
                        "download_url": photo["links"]["download_location"],
                        "author": photo["user"]["name"],
                        "author_url": photo["user"]["links"]["html"],
                        "description": photo.get("description") or photo.get("alt_description") or ""
                    }

        except Exception as e:
            print(f"[UnsplashService] Error fetching photo: {e}")
            return None

    async def trigger_download(self, download_url: str):
        """
        Trigger download endpoint as required by Unsplash API guidelines.
        This is required to give proper attribution.
        """
        try:
            headers = {
                "Authorization": f"Client-ID {self.access_key}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, headers=headers) as response:
                    # We don't need the response, just trigger the endpoint
                    pass
        except Exception as e:
            print(f"[UnsplashService] Error triggering download: {e}")


# Global instance
unsplash_service = UnsplashService()
