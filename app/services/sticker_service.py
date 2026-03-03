from pathlib import Path
from typing import Optional, List, Dict
import random
import gzip
import json


class StickerService:

    STICKERS_DIR = Path("static/stickers")
    VALID_EMOTIONS = [
        "laughter", "sad", "angry", "love", "surprised",
        "confused", "happy", "thinking", "crying", "cool"
    ]
    MAX_FILE_SIZE = 512 * 1024  # 512KB

    def __init__(self):
        self.STICKERS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[StickerService] Initialized with directory: {self.STICKERS_DIR.absolute()}")

    def _validate_tgs_format(self, file_content: bytes) -> bool:
        try:
            if len(file_content) < 2 or file_content[:2] != b'\x1f\x8b':
                return False

            decompressed = gzip.decompress(file_content)

            json.loads(decompressed.decode('utf-8'))

            return True
        except Exception as e:
            print(f"[StickerService] TGS validation failed: {e}")
            return False

    async def save_sticker(self, file_content: bytes, emotion: str) -> bool:
        try:
            if emotion not in self.VALID_EMOTIONS:
                print(f"[StickerService] Invalid emotion: {emotion}")
                return False

            if len(file_content) > self.MAX_FILE_SIZE:
                print(f"[StickerService] File too large: {len(file_content)} bytes")
                return False

            if not self._validate_tgs_format(file_content):
                print(f"[StickerService] Invalid TGS format")
                return False

            file_path = self.STICKERS_DIR / f"{emotion}.tgs"
            file_path.write_bytes(file_content)

            print(f"[StickerService] Saved sticker: {file_path.name}")
            return True

        except Exception as e:
            print(f"[StickerService] Error saving sticker: {e}")
            return False

    def get_sticker_path(self, emotion: str) -> Optional[Path]:
        if emotion not in self.VALID_EMOTIONS:
            return None

        file_path = self.STICKERS_DIR / f"{emotion}.tgs"

        if file_path.exists() and file_path.is_file():
            return file_path

        return None

    def list_available_stickers(self) -> List[Dict[str, str]]:
        stickers = []

        for emotion in self.VALID_EMOTIONS:
            file_path = self.STICKERS_DIR / f"{emotion}.tgs"
            if file_path.exists() and file_path.is_file():
                stickers.append({
                    "emotion": emotion,
                    "filename": file_path.name
                })

        return stickers

    async def delete_sticker(self, emotion: str) -> bool:
        try:
            if emotion not in self.VALID_EMOTIONS:
                return False

            file_path = self.STICKERS_DIR / f"{emotion}.tgs"

            if file_path.exists():
                file_path.unlink()
                print(f"[StickerService] Deleted sticker: {file_path.name}")
                return True

            return False

        except Exception as e:
            print(f"[StickerService] Error deleting sticker: {e}")
            return False

    def get_random_available_emotion(self) -> Optional[str]:
        available_emotions = []

        for emotion in self.VALID_EMOTIONS:
            file_path = self.STICKERS_DIR / f"{emotion}.tgs"
            if file_path.exists() and file_path.is_file():
                available_emotions.append(emotion)

        if available_emotions:
            return random.choice(available_emotions)

        return None
