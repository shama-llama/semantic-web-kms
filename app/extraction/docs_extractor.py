import re
import json
import os
from app.core.config import LOG_DIR, DEFAULT_INPUT_DIR
from app.core.paths import get_log_path, get_output_path
from pathlib import Path
from typing import Dict, List
from pdfminer.high_level import extract_text as pdf_extract_text
from bs4 import BeautifulSoup
import logging
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("docs_extractor.log")
debug_mode = os.environ.get("EXTRACT_DEBUG", "0") == "1"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

SUPPORTED_DOCS = {'.md', '.markdown', '.rst', '.txt', '.pdf', '.html', '.htm'}


def extract_markdown_segments(text: str):
    segments = []
    for line in text.splitlines():
        m = re.match(r'^(#{1,3})\s+(.*)', line)
        if m:
            segments.append(
                {'segment_type': f'heading{len(m.group(1))}', 'content': m.group(2)})
    code_blocks = re.findall(r'```[\w\-]*\n([\s\S]*?)```', text)
    for block in code_blocks:
        segments.append({'segment_type': 'code_block',
                        'content': block.strip()})
    return segments


def extract_html_segments(text: str):
    soup = BeautifulSoup(text, 'html.parser')
    segments = []
    for level in range(1, 4):
        for tag in soup.find_all(f'h{level}'):
            segments.append({'segment_type': f'heading{level}',
                            'content': tag.get_text(strip=True)})
    for pre in soup.find_all('pre'):
        segments.append({'segment_type': 'code_block',
                        'content': pre.get_text()})
    return segments


def extract_pdf_segments(filepath: Path):
    try:
        text = pdf_extract_text(str(filepath))
        pages = text.split('\f')
        segments = []
        for i, page in enumerate(pages):
            if page.strip():
                segments.append(
                    {'segment_type': 'page', 'content': page.strip(), 'page': i+1})
        return segments
    except Exception as e:
        return [{'segment_type': 'error', 'content': str(e)}]


def extract_documentation(file_records: List[Dict], root_dir: str, output_path: Path):
    console = Console()
    logger.info(f"Starting documentation extraction for {len(file_records)} files in {root_dir}")
    doc_segments = []
    doc_id = 1
    doc_files = [file for file in file_records if file['type'] == 'docs' and file['extension'] in SUPPORTED_DOCS]
    total_docs = len(doc_files)
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Extracting docs...", total=total_docs)
        for file in doc_files:
            abs_path = Path(root_dir) / file['path']
            logger.debug(f"Processing file: {abs_path} (id={file['id']}, ext={file['extension']})")
            try:
                if file['extension'] in {'.md', '.markdown', '.rst', '.txt'}:
                    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    segments = extract_markdown_segments(text)
                elif file['extension'] in {'.html', '.htm'}:
                    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    segments = extract_html_segments(text)
                elif file['extension'] == '.pdf':
                    segments = extract_pdf_segments(abs_path)
                else:
                    logger.debug(f"Skipping unsupported doc file: {abs_path}")
                    progress.advance(task)
                    continue
                for seg in segments:
                    doc_segments.append({
                        'id': doc_id,
                        'file_id': file['id'],
                        'segment_type': seg.get('segment_type'),
                        'content': seg.get('content'),
                        'page': seg.get('page') if 'page' in seg else None
                    })
                logger.debug(f"Added segment: {{'id': {doc_id}, 'file_id': {file['id']}, 'segment_type': {seg.get('segment_type')}, 'page': {seg.get('page', None)}}}")
                doc_id += 1
                logger.info(f"Extracted {len(segments)} segments from {abs_path}")
            except Exception as e:
                doc_segments.append({
                    'id': doc_id,
                    'file_id': file['id'],
                    'segment_type': 'error',
                    'content': str(e),
                    'page': None
                })
                logger.error(f"Error processing {abs_path}: {e}")
                doc_id += 1
            progress.advance(task)
    with open(output_path, 'w') as f:
        json.dump(doc_segments, f, indent=2)
    summary = f"Extracted {len(doc_segments)} documentation segments. Output written to {output_path}"
    console.print(f"[bold green]{summary}")
    logger.info(summary)
    logger.debug(f"extract_documentation completed. Total segments: {len(doc_segments)}")


if __name__ == '__main__':
    INPUT_DIR = DEFAULT_INPUT_DIR
    FILES_JSON = Path(get_output_path("extracted_files.json"))
    DOCS_JSON = Path(get_output_path("extracted_docs.json"))
    os.makedirs(os.path.dirname(FILES_JSON), exist_ok=True)
    with open(FILES_JSON, 'r') as f:
        file_records = json.load(f)
    extract_documentation(file_records, INPUT_DIR, DOCS_JSON)
