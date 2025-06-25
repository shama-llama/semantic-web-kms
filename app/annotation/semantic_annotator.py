import os
import json
import logging
from app.ontology.wdo import WDOOntology
from app.core.graph_manager import GraphManager
from app.core.config import LOG_DIR
from app.core.paths import get_log_path, get_output_path
from app.annotation.files_annotator import FileAnnotator
from app.annotation.code_annotator import CodeAnnotator
from app.annotation.docs_annotator import DocAnnotator
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

def create_semantic_annotations(project_name, files_json, code_json, docs_json, output_dir):
    # Setup dedicated logger
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = get_log_path("annotation_pipeline.log")
    logger = logging.getLogger("annotation_pipeline")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    if not logger.hasHandlers():
        logger.addHandler(handler)
    console = Console()

    ontology = WDOOntology()
    graph_manager = GraphManager(ontology)
    file_annotator = FileAnnotator(ontology, graph_manager)
    code_annotator = CodeAnnotator(ontology, graph_manager)
    doc_annotator = DocAnnotator(ontology, graph_manager)

    logger.info(f"Starting annotation pipeline for project '{project_name}'")
    console.print("[bold blue]Starting annotation pipeline...[/bold blue]")

    # Annotate files
    file_records = []
    if os.path.exists(files_json):
        with open(files_json, 'r') as f:
            file_records = json.load(f)
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Annotating files...", total=len(file_records))
            file_annotator.annotate(file_records, project_name)
            progress.update(task, completed=len(file_records))
        logger.info(f"File annotation complete. {len(file_records)} files annotated.")
        console.print(f"[bold cyan]File annotation complete. {len(file_records)} files annotated.[/bold cyan]")
    else:
        logger.warning(f"Files JSON not found: {files_json}")
        console.print(f"[bold red]Files JSON not found: {files_json}[/bold red]")

    # Annotate code
    code_data = {}
    if os.path.exists(code_json):
        with open(code_json, 'r') as f:
            code_data = json.load(f)
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Annotating code...", total=len(code_data))
            code_annotator.annotate(code_data)
            progress.update(task, completed=len(code_data))
        logger.info(f"Code annotation complete. {len(code_data)} files annotated.")
        console.print(f"[bold cyan]Code annotation complete. {len(code_data)} files annotated.[/bold cyan]")
    else:
        logger.warning(f"Code JSON not found: {code_json}")
        console.print(f"[bold red]Code JSON not found: {code_json}[/bold red]")

    # Annotate docs
    doc_data = []
    if os.path.exists(docs_json):
        with open(docs_json, 'r') as f:
            doc_data = json.load(f)
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[green]Annotating docs...", total=len(doc_data))
            doc_annotator.annotate(doc_data)
            progress.update(task, completed=len(doc_data))
        logger.info(f"Documentation annotation complete. {len(doc_data)} segments annotated.")
        console.print(f"[bold cyan]Documentation annotation complete. {len(doc_data)} segments annotated.[/bold cyan]")
    else:
        logger.warning(f"Docs JSON not found: {docs_json}")
        console.print(f"[bold red]Docs JSON not found: {docs_json}[/bold red]")

    # Save to file
    output_path = get_output_path(f"{project_name.lower().replace(' ', '_')}_annotations.ttl")
    graph_manager.serialize(output_path, 'turtle')
    logger.info(f"Annotation pipeline complete. Output written to {output_path}")
    console.print(f"[bold green]Annotation pipeline complete. Output written to {output_path}[/bold green]")
    return output_path

if __name__ == '__main__':
    PROJECT_NAME = "semantic-web-kms"
    FILES_JSON = get_output_path("extracted_files.json")
    CODE_JSON = get_output_path("extracted_code.json")
    DOCS_JSON = get_output_path("extracted_docs.json")
    os.makedirs(os.path.dirname(FILES_JSON), exist_ok=True)
    create_semantic_annotations(
        PROJECT_NAME, FILES_JSON, CODE_JSON, DOCS_JSON, os.path.dirname(FILES_JSON)
    )
