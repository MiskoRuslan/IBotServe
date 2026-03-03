import os
import aiohttp
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class UnsplashService:
    def __init__(self):
        self.access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        self.api_url = "https://api.unsplash.com/photos/random"
        self.enabled = bool(self.access_key)

        if not self.access_key:
            print("[UnsplashService] WARNING: UNSPLASH_ACCESS_KEY not set - photo sending disabled")
            print("[UnsplashService] Add UNSPLASH_ACCESS_KEY to .env or docker-compose.yml to enable")

    def extract_keywords(self, text: str) -> str:
        import random

        text = re.sub(r'http\S+|@\S+|#\S+', '', text)

        ukr_keywords = {
            'автомобіль': 'car', 'машина': 'car', 'авто': 'car',
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

        all_keywords = {**ukr_keywords, **rus_keywords}

        text_lower = text.lower()

        base_keyword = None
        for keyword, english in all_keywords.items():
            if keyword in text_lower:
                base_keyword = english
                break

        if not base_keyword:
            casual_keywords = ['car', 'work', 'coffee', 'sunset', 'nature']
            base_keyword = random.choice(casual_keywords)

        if random.random() < 0.5:
            modifiers = ['meme', 'funny', 'humor']
            modifier = random.choice(modifiers)
            return f"{base_keyword} {modifier}"
        else:
            return base_keyword

    async def get_random_photo(self, keyword: Optional[str] = None) -> Optional[dict]:
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
        try:
            headers = {
                "Authorization": f"Client-ID {self.access_key}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, headers=headers) as response:
                    pass
        except Exception as e:
            print(f"[UnsplashService] Error triggering download: {e}")


# Global instance
unsplash_service = UnsplashService()
