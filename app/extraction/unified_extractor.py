import os
import json
from app.core.config import LOG_DIR, DEFAULT_INPUT_DIR
from app.core.paths import (
    get_log_path, get_output_path, get_model_path, get_web_dev_extensions_path
)
from app.extraction.files_extractor import extract_files
from app.extraction.docs_extractor import extract_documentation
from app.extraction.code_extractor import extract_code_entities
import logging
from rich.console import Console

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("unified_extractor.log")
debug_mode = os.environ.get("EXTRACT_DEBUG", "0") == "1"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

INPUT_DIR = DEFAULT_INPUT_DIR
EXT_PATH = get_web_dev_extensions_path()
FILES_JSON = get_output_path("extracted_files.json")
DOCS_JSON = get_output_path("extracted_docs.json")
CODE_JSON = get_output_path("extracted_code.json")

os.makedirs(os.path.dirname(FILES_JSON), exist_ok=True)

console = Console()

def main():
    console.print("[bold blue]Starting ingestion pipeline...[/bold blue]")
    logger.info("Starting ingestion pipeline.")
    try:
        file_records = extract_files(INPUT_DIR, EXT_PATH, FILES_JSON)
        logger.info(f"Unified extractor: File extraction complete. {len(file_records)} files detected.")
        console.print(f"[bold cyan]Unified extractor: File extraction complete.[/bold cyan]")
    except Exception as e:
        logger.error(f"Unified extractor: File extraction failed: {e}")
        console.print(f"[bold red]File extraction failed: {e}[/bold red]")
        return
    try:
        extract_documentation(file_records, INPUT_DIR, DOCS_JSON)
        logger.info("Unified extractor: Documentation extraction complete.")
        console.print("[bold cyan]Unified extractor: Documentation extraction complete.[/bold cyan]")
    except Exception as e:
        logger.error(f"Unified extractor: Documentation extraction failed: {e}")
        console.print(f"[bold red]Documentation extraction failed: {e}[/bold red]")
        return
    try:
        extract_code_entities(file_records, INPUT_DIR, None, CODE_JSON)
        logger.info("Unified extractor: Code extraction complete.")
        console.print("[bold cyan]Unified extractor: Code extraction complete.[/bold cyan]")
    except Exception as e:
        logger.error(f"Unified extractor: Code extraction failed: {e}")
        console.print(f"[bold red]Code extraction failed: {e}[/bold red]")
        return
    summary = "Ingestion pipeline completed successfully."
    console.print(f"[bold green]{summary}[/bold green]")
    logger.info(summary)

if __name__ == '__main__':
    main()
