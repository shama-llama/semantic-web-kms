# extract_code.py
import os
import json
from app.core.config import LOG_DIR, DEFAULT_INPUT_DIR
from app.core.paths import (
    get_log_path, get_output_path, get_excluded_dirs_path, get_language_mapping_path, get_code_queries_path
)
from tree_sitter_languages import get_language, get_parser
import warnings
import sys
import logging
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console

warnings.filterwarnings("ignore", category=FutureWarning, module='tree_sitter')

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("code_extractor.log")
debug_mode = os.environ.get("EXTRACT_DEBUG", "0") == "1"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Load excluded directories from external JSON file
EXCLUDED_DIRS_PATH = get_excluded_dirs_path()
try:
    with open(EXCLUDED_DIRS_PATH, 'r', encoding='utf-8') as ed_f:
        DEFAULT_EXCLUDED_DIRS = set(json.load(ed_f))
except Exception as e:
    logger.error(f"Error loading excluded directories from {EXCLUDED_DIRS_PATH}: {e}")
    DEFAULT_EXCLUDED_DIRS = set()

# Load language mapping from external JSON file
LANGUAGE_MAPPING_PATH = get_language_mapping_path()
try:
    with open(LANGUAGE_MAPPING_PATH, 'r', encoding='utf-8') as lm_f:
        LANGUAGE_MAPPING = json.load(lm_f)
except Exception as e:
    logger.error(f"Error loading language mapping from {LANGUAGE_MAPPING_PATH}: {e}")
    LANGUAGE_MAPPING = {}

# Load queries from external JSON file
QUERIES_PATH = get_code_queries_path()
try:
    with open(QUERIES_PATH, 'r', encoding='utf-8') as qf:
        QUERIES = json.load(qf)
except Exception as e:
    logger.error(f"Error loading code queries from {QUERIES_PATH}: {e}")
    QUERIES = {}

INPUT_DIR = DEFAULT_INPUT_DIR
FILES_JSON = get_output_path("extracted_files.json")
CODE_JSON = get_output_path("extracted_code.json")

os.makedirs(os.path.dirname(FILES_JSON), exist_ok=True)

console = Console()

def analyze_and_write(file_path, language_name, language_queries, temp_file_handle, base_dir):
    """
    Analyzes a single file and writes its result directly to the temporary file.
    """
    file_results = {}
    try:
        language = get_language(language_name)
        parser = get_parser(language_name)
    except Exception as e:
        logger.error(f"Failed to get language/parser for {language_name}: {e}")
        return

    try:
        with open(file_path, 'rb') as f:
            code = f.read()
            tree = parser.parse(code)
            root_node = tree.root_node
    except Exception as e:
        logger.error(f"Failed to parse file {file_path}: {e}")
        return

    for construct, query_str_or_list in language_queries.items():
        query_list = query_str_or_list if isinstance(
            query_str_or_list, list) else [query_str_or_list]
        all_captures = []
        for query_str in query_list:
            try:
                query = language.query(query_str)
                captures = query.captures(root_node)
                for node, _ in captures:
                    capture_info = {"text": node.text.decode(
                        'utf-8', errors='ignore').strip(), "line": node.start_point[0] + 1}
                    if capture_info not in all_captures:
                        all_captures.append(capture_info)
            except Exception as e:
                logger.debug(f"Query failed for {construct} in {file_path}: {e}")
                continue
        if all_captures:
            all_captures.sort(key=lambda c: c['line'])
            file_results[construct] = all_captures

    if file_results:
        relative_path = os.path.relpath(file_path, base_dir)
        output_obj = {
            relative_path: {
                "language": language_name,
                "constructs": file_results
            }
        }
        json.dump(output_obj, temp_file_handle)
        temp_file_handle.write('\n')
        logger.info(f"Analyzed and wrote results for {relative_path}")
        logger.debug(f"Results: {output_obj}")

def parse_directory(directory_path, temp_file_handle, excluded_dirs):
    """
    Walks a directory, skipping excluded directories, and analyzes supported files.
    """
    logger.info(f"Starting analysis of directory: {directory_path}")
    logger.info(f"Excluding directories: {', '.join(sorted(list(excluded_dirs)))}")

    for root, dirs, files in os.walk(directory_path):
        # Modify dirs in-place to prevent os.walk from descending into them.
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1]
            if file_extension in LANGUAGE_MAPPING:
                language_name = LANGUAGE_MAPPING[file_extension]
                language_queries = QUERIES.get(language_name)
                if language_queries:
                    logger.debug(f"Analyzing: {file_path}")
                    analyze_and_write(
                        file_path, language_name, language_queries, temp_file_handle, directory_path)

def compile_final_json(temp_path, final_path):
    """
    Reads the temporary JSON Lines file and creates the final, formatted JSON file.
    """
    logger.info(f"\nCompiling final JSON file from temporary data...")
    final_results = {}
    try:
        with open(temp_path, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                if line.strip():
                    final_results.update(json.loads(line))

        with open(final_path, 'w', encoding='utf-8') as f_out:
            json.dump(final_results, f_out, indent=2, ensure_ascii=False)
        logger.info(f"Compilation complete. Final results saved to {final_path}")

    except FileNotFoundError:
        logger.warning("No data was analyzed, so no output file was created.")
    except Exception as e:
        logger.error(f"An error occurred during final JSON compilation: {e}")

def extract_code_entities(file_records, root_dir, tso_path, output_path):
    """
    Extracts code entities from files listed in file_records and writes to output_path.
    Only processes files with supported extensions and type 'code'.
    """
    results = {}
    code_files = [file for file in file_records if file.get('type') == 'code' and file.get('extension') in LANGUAGE_MAPPING]
    total_code = len(code_files)
    logger.info(f"Starting code extraction for {total_code} files in {root_dir}")
    doc_id = 1
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Extracting code...", total=total_code)
        for file in code_files:
            ext = file.get('extension')
            language_name = LANGUAGE_MAPPING[ext]
            language_queries = QUERIES.get(language_name)
            abs_path = os.path.join(root_dir, file['path'])
            file_results = {}
            try:
                language = get_language(language_name)
                parser = get_parser(language_name)
                with open(abs_path, 'rb') as f:
                    code = f.read()
                    tree = parser.parse(code)
                    root_node = tree.root_node
                for construct, query_str_or_list in language_queries.items():
                    query_list = query_str_or_list if isinstance(
                        query_str_or_list, list) else [query_str_or_list]
                    all_captures = []
                    for query_str in query_list:
                        try:
                            query = language.query(query_str)
                            captures = query.captures(root_node)
                            for node, _ in captures:
                                capture_info = {"text": node.text.decode(
                                    'utf-8', errors='ignore').strip(), "line": node.start_point[0] + 1}
                                if capture_info not in all_captures:
                                    all_captures.append(capture_info)
                        except Exception as e:
                            logger.debug(f"Query failed for {construct} in {abs_path}: {e}")
                            continue
                    if all_captures:
                        all_captures.sort(key=lambda c: c['line'])
                        file_results[construct] = all_captures
                if file_results:
                    results[file['path']] = {
                        "language": language_name,
                        "constructs": file_results
                    }
                    logger.info(f"Extracted code entities from {abs_path}")
                    logger.debug(f"Results: {{'language': '{language_name}', 'constructs': {file_results}}}")
            except Exception as e:
                logger.error(f"Error processing {abs_path}: {e}")
            progress.advance(task)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    summary = f"Extracted code entities for {len(results)} files. Output written to {output_path}"
    console.print(f"[bold green]{summary}")
    logger.info(summary)
    logger.debug(f"extract_code_entities completed. Total files: {len(results)}")

def main():
    if os.path.exists(FILES_JSON):
        with open(FILES_JSON, 'r') as f:
            file_records = json.load(f)
        extract_code_entities(file_records, INPUT_DIR, None, CODE_JSON)
    else:
        logger.error(
            f"Error: files.json not found at {FILES_JSON}. Please run extract_files.py first.")

if __name__ == "__main__":
    main()
