import logging
import os
from typing import Any, Dict, List

from git import InvalidGitRepositoryError, Repo
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from app.core.ontology_cache import (
    get_git_extraction_classes,
    get_git_extraction_properties,
    get_ontology_cache,
)
from app.core.paths import (
    get_input_path,
    get_log_path,
    get_output_path,
    uri_safe_string,
)

# Setup logging to file only
log_path = get_log_path("git_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("git_extractor")

# --- Ontology and File Paths ---
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")

TTL_PATH = get_output_path("web_development_ontology.ttl")
INPUT_DIR = get_input_path("")


def get_repo_uri(repo_name: str) -> URIRef:
    """Generate URI for repository entity."""
    return URIRef(str(INST[uri_safe_string(repo_name)]))


def get_file_uri(repo_name: str, rel_path: str) -> URIRef:
    """Generate URI for file entity."""
    repo_enc = uri_safe_string(repo_name)
    path_enc = uri_safe_string(rel_path)
    return URIRef(str(INST[f"{repo_enc}/{path_enc}"]))


def main() -> None:
    """Main function for Git extraction."""
    console = Console()

    logger.info("Starting Git extraction process...")

    # Load ontology and cache
    ontology_cache = get_ontology_cache()
    prop_cache = ontology_cache.get_property_cache(get_git_extraction_properties())
    class_cache = ontology_cache.get_class_cache(get_git_extraction_classes())

    g = Graph()
    if os.path.exists(TTL_PATH):
        g.parse(TTL_PATH, format="turtle")

    # Pre-scan to count repositories and commits
    repo_dirs = [
        d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))
    ]
    total_repos = 0
    total_commits = 0
    repo_commit_map: Dict[str, List[Any]] = {}

    for repo_name in repo_dirs:
        repo_path = os.path.join(INPUT_DIR, repo_name)
        try:
            repo = Repo(repo_path)
            commits = list(repo.iter_commits())
            repo_commit_map[repo_name] = commits
            total_repos += 1
            total_commits += len(commits)
        except (InvalidGitRepositoryError, Exception):
            continue

    logger.info(
        f"Found {total_repos} Git repositories with {total_commits} total commits"
    )

    progress_columns = [
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
    ]

    # Store all commit data for TTL writing
    all_commit_data: List[Dict[str, Any]] = []
    repo_count = 0
    commit_count = 0
    file_mod_count = 0

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Single overall progress bar for the entire process
        overall_task = progress.add_task(
            "[blue]Processing Git repositories and commits...", total=total_commits
        )

        for repo_name, commits in repo_commit_map.items():
            repo_path = os.path.join(INPUT_DIR, repo_name)

            for commit in commits:
                commit_hash = commit.hexsha
                commit_data: dict = {
                    "repo_name": repo_name,
                    "commit_hash": commit_hash,
                    "commit_message": commit.message.strip(),
                    "commit_timestamp": int(commit.committed_date),
                    "commit_author": commit.author.name,
                    "modified_files": [],
                }

                # Files changed in this commit
                for parent in commit.parents or []:
                    diff = commit.diff(parent, create_patch=False)
                    for d in diff:
                        if d.a_path:
                            commit_data["modified_files"].append(d.a_path)
                            file_mod_count += 1

                # For initial commit (no parent)
                if not commit.parents:
                    for obj in commit.tree.traverse():
                        # Type guard to ensure obj has the required attributes
                        if hasattr(obj, "type") and hasattr(obj, "path"):
                            if obj.type == "blob":  # type: ignore[union-attr]
                                commit_data["modified_files"].append(obj.path)  # type: ignore[union-attr]
                                file_mod_count += 1

                all_commit_data.append(commit_data)
                commit_count += 1
                progress.advance(overall_task)

            repo_count += 1

        logger.info("Commit processing complete. Writing TTL...")

        # --- Write code structure entities to TTL & RDF ---
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(all_commit_data))

        # Track repositories to avoid duplicates
        processed_repos = set()

        for commit_data in all_commit_data:
            repo_name = commit_data["repo_name"]
            repo_uri = get_repo_uri(repo_name)

            # Define repository entity if not already processed
            if repo_name not in processed_repos:
                g.add((repo_uri, RDF.type, class_cache["Repository"]))
                # --- NEW: Create repository metadata as InformationContentEntity ---
                repo_metadata_uri = INST[f"{uri_safe_string(repo_name)}_metadata"]
                g.add(
                    (
                        repo_metadata_uri,
                        RDF.type,
                        class_cache["InformationContentEntity"],
                    )
                )
                g.add(
                    (
                        repo_metadata_uri,
                        prop_cache["hasSimpleName"],
                        Literal(repo_name, datatype=XSD.string),
                    )
                )
                # Link metadata to repository using isAbout
                g.add((repo_metadata_uri, prop_cache["isAbout"], repo_uri))
                processed_repos.add(repo_name)

            # Create commit entity
            commit_uri = INST[
                f"{uri_safe_string(repo_name)}/commit/{commit_data['commit_hash']}"
            ]
            g.add((commit_uri, RDF.type, class_cache["Commit"]))
            g.add(
                (
                    commit_uri,
                    prop_cache["hasCommitHash"],
                    Literal(commit_data["commit_hash"], datatype=XSD.string),
                )
            )
            # --- NEW: Create CommitMessage individual for commit message ---
            commit_msg_uri = INST[
                f"{uri_safe_string(repo_name)}/commit/{commit_data['commit_hash']}_msg"
            ]
            g.add((commit_msg_uri, RDF.type, class_cache.get("CommitMessage", class_cache["InformationContentEntity"])))
            g.add(
                (
                    commit_msg_uri,
                    prop_cache["hasContent"],
                    Literal(commit_data["commit_message"], datatype=XSD.string),
                )
            )
            g.add((commit_uri, prop_cache["hasCommitMessage"], commit_msg_uri))
            # --- END NEW ---
            g.add((repo_uri, prop_cache["hasCommit"], commit_uri))

            # Add file modifications
            for file_path in commit_data["modified_files"]:
                file_uri = get_file_uri(repo_name, file_path)
                g.add((commit_uri, prop_cache["modifies"], file_uri))
                g.add((repo_uri, RDFS.member, file_uri))

            progress.advance(ttl_task)

    g.serialize(destination=TTL_PATH, format="turtle")

    logger.info(
        f"Git extraction complete: {repo_count} repos, {commit_count} commits, {file_mod_count} file modifications"
    )
    console.print(
        f"[bold green]Git extraction complete:[/bold green] {repo_count} repos, {commit_count} commits, {file_mod_count} file modifications"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


if __name__ == "__main__":
    main()
