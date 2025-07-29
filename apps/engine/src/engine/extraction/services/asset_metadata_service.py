"""Asset metadata extraction service for content analysis."""

import logging
from pathlib import Path
from typing import Any

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger("AssetMetadataService")


class AssetMetadataService:
    """
    Service for extracting metadata from various asset types (images, videos, audio, fonts).
    """

    def extract_image_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract metadata from image files using PIL."""
        metadata = {}
        if not PIL_AVAILABLE:
            return metadata

        try:
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                try:
                    exif = img.getexif() if hasattr(img, "getexif") else None
                    if exif:
                        exif_tags = {
                            36867: "DateTimeOriginal",
                            271: "Make",
                            272: "Model",
                            37377: "FNumber",
                            37378: "ExposureTime",
                            37383: "ISOSpeedRatings",
                        }
                        for tag_id, tag_name in exif_tags.items():
                            if tag_id in exif:
                                metadata[tag_name] = str(exif[tag_id])
                except (AttributeError, TypeError):
                    pass
        except Exception as e:
            logger.warning(f"Could not extract image metadata from {file_path}: {e}")

        return metadata

    def extract_media_metadata(self, file_path: str, file_type: str) -> dict[str, Any]:
        """Extract basic metadata from media files."""
        metadata = {}
        try:
            file_size = Path(file_path).stat().st_size
            metadata["file_size"] = file_size
            ext = Path(file_path).suffix.lower()
            if ext:
                metadata["format"] = ext[1:]
            if file_type in ["VideoDescription", "VideoFile"]:
                metadata["media_type"] = "video"
            elif file_type in ["AudioDescription", "AudioFile"]:
                metadata["media_type"] = "audio"
            elif file_type in ["FontDescription", "FontFile"]:
                metadata["media_type"] = "font"
        except Exception as e:
            logger.warning(f"Could not extract media metadata from {file_path}: {e}")

        return metadata
