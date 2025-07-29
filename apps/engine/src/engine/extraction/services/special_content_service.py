"""Special content analysis service for content analysis."""

import logging
import re

logger = logging.getLogger("SpecialContentService")


class SpecialContentService:
    """
    Service for analyzing special content types like Dockerfiles and licenses.
    """

    def extract_dockerfile_base_image(self, file_path: str) -> str:
        """Extract the base image from a Dockerfile."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.upper().startswith("FROM "):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
        except Exception as e:
            logger.warning(
                f"Could not extract Dockerfile base image from {file_path}: {e}"
            )
        return ""

    def extract_license_identifier(self, file_path: str) -> str:
        """Extract SPDX license identifier from a license file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(2048)
            match = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9\.-]+)", content)
            if match:
                return match.group(1)
            for spdx in [
                "MIT",
                "Apache-2.0",
                "GPL-3.0",
                "BSD-3-Clause",
                "BSD-2-Clause",
                "LGPL-3.0",
                "MPL-2.0",
                "EPL-2.0",
                "Unlicense",
            ]:
                if spdx in content:
                    return spdx
        except Exception as e:
            logger.warning(
                f"Could not extract license identifier from {file_path}: {e}"
            )
        return ""

    def get_line_count(self, file_path: str) -> int:
        """Return the number of lines in a file."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
