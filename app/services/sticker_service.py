"""
Sticker Service - Manages local TGS sticker files
"""
from pathlib import Path
from typing import Optional, List, Dict
import random
import gzip
import json


class StickerService:
    """Service for managing global sticker files stored locally"""

    STICKERS_DIR = Path("static/stickers")
    VALID_EMOTIONS = [
        "laughter", "sad", "angry", "love", "surprised",
        "confused", "happy", "thinking", "crying", "cool"
    ]
    MAX_FILE_SIZE = 512 * 1024  # 512KB

    def __init__(self):
        """Initialize service and ensure stickers directory exists"""
        self.STICKERS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[StickerService] Initialized with directory: {self.STICKERS_DIR.absolute()}")

    def _validate_tgs_format(self, file_content: bytes) -> bool:
        """
        Validate that file is a valid TGS file
        TGS files are gzipped JSON (Lottie animations)
        """
        try:
            # Check gzip magic bytes
            if len(file_content) < 2 or file_content[:2] != b'\x1f\x8b':
                return False

            # Try to decompress
            decompressed = gzip.decompress(file_content)

            # Try to parse as JSON (TGS contains Lottie JSON)
            json.loads(decompressed.decode('utf-8'))

            return True
        except Exception as e:
            print(f"[StickerService] TGS validation failed: {e}")
            return False

    async def save_sticker(self, file_content: bytes, emotion: str) -> bool:
        """
        Save uploaded TGS file with emotion-based filename

        Args:
            file_content: Binary content of the TGS file
            emotion: Emotion name (must be in VALID_EMOTIONS)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate emotion
            if emotion not in self.VALID_EMOTIONS:
                print(f"[StickerService] Invalid emotion: {emotion}")
                return False

            # Validate file size
            if len(file_content) > self.MAX_FILE_SIZE:
                print(f"[StickerService] File too large: {len(file_content)} bytes")
                return False

            # Validate TGS format
            if not self._validate_tgs_format(file_content):
                print(f"[StickerService] Invalid TGS format")
                return False

            # Save file (overwrite if exists)
            file_path = self.STICKERS_DIR / f"{emotion}.tgs"
            file_path.write_bytes(file_content)

            print(f"[StickerService] Saved sticker: {file_path.name}")
            return True

        except Exception as e:
            print(f"[StickerService] Error saving sticker: {e}")
            return False

    def get_sticker_path(self, emotion: str) -> Optional[Path]:
        """
        Get path to sticker file for given emotion

        Args:
            emotion: Emotion name

        Returns:
            Path object if file exists, None otherwise
        """
        if emotion not in self.VALID_EMOTIONS:
            return None

        file_path = self.STICKERS_DIR / f"{emotion}.tgs"

        if file_path.exists() and file_path.is_file():
            return file_path

        return None

    def list_available_stickers(self) -> List[Dict[str, str]]:
        """
        List all available stickers

        Returns:
            List of dicts with emotion and filename
            Example: [{"emotion": "happy", "filename": "happy.tgs"}]
        """
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
        """
        Delete sticker file for given emotion

        Args:
            emotion: Emotion name

        Returns:
            True if deleted successfully, False otherwise
        """
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
        """
        Get random emotion that has an available sticker file

        Returns:
            Random emotion name, or None if no stickers available
        """
        available_emotions = []

        for emotion in self.VALID_EMOTIONS:
            file_path = self.STICKERS_DIR / f"{emotion}.tgs"
            if file_path.exists() and file_path.is_file():
                available_emotions.append(emotion)

        if available_emotions:
            return random.choice(available_emotions)

        return None
