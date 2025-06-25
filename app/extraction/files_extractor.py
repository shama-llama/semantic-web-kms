import os
import json
from app.core.config import LOG_DIR, DEFAULT_INPUT_DIR
from app.core.paths import (
    get_log_path, get_output_path, get_model_path, get_web_dev_extensions_path
)
from pathlib import Path
from typing import Dict, List
import logging
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("files_extractor.log")
debug_mode = os.environ.get("EXTRACT_DEBUG", "0") == "1"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def extract_files(root_dir: str, ext_path: Path, output_path: Path) -> List[Dict]:
    console = Console()
    logger.debug(f"extract_files called with root_dir={root_dir}, ext_path={ext_path}, output_path={output_path}")
    with open(ext_path, 'r') as f:
        EXTENSIONS = json.load(f)
    logger.debug(f"Loaded extensions: {EXTENSIONS}")
    def get_category(extension: str) -> str:
        logger.debug(f"Checking category for extension: {extension}")
        for category, exts in EXTENSIONS.items():
            if extension.lower() in exts:
                logger.debug(f"Extension {extension} matched category {category}")
                return category
        logger.debug(f"Extension {extension} did not match any category")
        return None
    file_records = []
    file_id = 1
    all_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            all_files.append((dirpath, fname))
    total_files = len(all_files)
    logger.info(f"Starting file extraction in {root_dir} with {total_files} files found.")
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Processing files...", total=total_files)
        for dirpath, fname in all_files:
            ext = os.path.splitext(fname)[1]
            category = get_category(ext)
            if not category:
                logger.debug(f"Skipping file {fname} (no category for extension {ext})")
                progress.advance(task)
                continue
            rel_path = os.path.relpath(os.path.join(dirpath, fname), root_dir)
            file_records.append({
                'id': file_id,
                'path': rel_path,
                'type': category,
                'extension': ext,
            })
            logger.info(f"Categorized file: {rel_path} as {category} ({ext})")
            logger.debug(f"File record: {{'id': {file_id}, 'path': '{rel_path}', 'type': '{category}', 'extension': '{ext}'}}")
            file_id += 1
            progress.advance(task)
    with open(output_path, 'w') as f:
        json.dump(file_records, f, indent=2)
    summary = f"Detected and categorized {len(file_records)} files. Output written to {output_path}"
    console.print(f"[bold green]{summary}")
    logger.info(summary)
    logger.debug(f"extract_files completed. Total records: {len(file_records)}")
    return file_records

if __name__ == '__main__':
    INPUT_DIR = DEFAULT_INPUT_DIR
    EXT_PATH = get_web_dev_extensions_path()
    FILES_JSON = get_output_path("extracted_files.json")
    os.makedirs(os.path.dirname(FILES_JSON), exist_ok=True)
    extract_files(INPUT_DIR, EXT_PATH, FILES_JSON)