"""Extract git commit and repository metadata for semantic web KMS knowledge graph population."""

import logging
import os
from typing import Any, Dict, List

from git import InvalidGitRepositoryError, Repo
from git.objects.commit import Commit
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
logger = logging.getLogger("git_extractor")

# --- Ontology and File Paths ---
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")

TTL_PATH = get_output_path("web_development_ontology.ttl")
INPUT_DIR = get_input_path("")


# --- Helper functions for URI construction ---
def get_repo_uri(repo_name: str) -> URIRef:
    """Return the URI for a repository resource."""
    return URIRef(f"{INST[uri_safe_string(repo_name)]}")


def get_file_uri(repo_name: str, file_path: str) -> URIRef:
    """Return the URI for a file resource."""
    repo_enc = uri_safe_string(repo_name)
    path_enc = uri_safe_string(file_path)
    return URIRef(f"{INST[f'{repo_enc}/{path_enc}']}")


def get_commit_uri(repo_name: str, commit_hash: str) -> URIRef:
    """Return the URI for a commit resource."""
    repo_enc = uri_safe_string(repo_name)
    hash_enc = uri_safe_string(commit_hash)
    return URIRef(f"{INST[f'{repo_enc}/commit/{hash_enc}']}")


def get_commit_message_uri(repo_name: str, commit_hash: str) -> URIRef:
    """Return the URI for a commit message resource."""
    repo_enc = uri_safe_string(repo_name)
    hash_enc = uri_safe_string(commit_hash)
    return URIRef(f"{INST[f'{repo_enc}/commit/{hash_enc}_msg']}")


def get_issue_uri(repo_name: str, issue_id: str) -> URIRef:
    """Generate URI for issue entity."""
    repo_enc = uri_safe_string(repo_name)
    issue_enc = uri_safe_string(issue_id)
    return URIRef(str(INST[f"{repo_enc}/issue/{issue_enc}"]))


def extract_issue_references(message: str) -> list[str]:
    """Extract referenced issue numbers from a commit message."""
    # Why: Enables linking commits to issues for traceability.
    import re

    # Pattern to match issue references (#123, #456, etc.)
    issue_pattern = r"#(\d+)"
    matches = re.findall(issue_pattern, message)

    # Also look for keywords that might indicate issue fixing
    fix_keywords = [
        "fix",
        "fixes",
        "fixed",
        "close",
        "closes",
        "closed",
        "resolve",
        "resolves",
        "resolved",
    ]
    issue_refs = []

    for match in matches:
        issue_refs.append(match)

    return issue_refs


def setup_logging() -> None:
    """Configure logging to file for the git extractor."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format=LOGFORMAT_FILE,
    )
    logger.setLevel(logging.INFO)


def load_ontology_and_cache():
    """Load ontology cache and property/class caches."""
    ontology_cache = get_ontology_cache()
    prop_cache = ontology_cache.get_property_cache(get_git_extraction_properties())
    class_cache = ontology_cache.get_class_cache(get_git_extraction_classes())
    return ontology_cache, prop_cache, class_cache


def scan_repositories(input_dir: str) -> dict:
    """Scan input directory for valid git repositories and their commits."""
    repo_dirs = [
        d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))
    ]
    repo_commit_map: Dict[str, List[Any]] = {}
    total_repos = 0
    total_commits = 0
    for repo_name in repo_dirs:
        repo_path = os.path.join(input_dir, repo_name)
        try:
            repo = Repo(repo_path)
            commits = list(repo.iter_commits())
            repo_commit_map[repo_name] = commits
            total_repos += 1
            total_commits += len(commits)
        except (InvalidGitRepositoryError, Exception):
            continue
    return {
        "repo_commit_map": repo_commit_map,
        "total_repos": total_repos,
        "total_commits": total_commits,
    }


def extract_commit_data(
    repo_commit_map: Dict[str, List[Any]], input_dir: str, progress, overall_task
) -> List[Dict[str, Any]]:
    """Extract commit data from all repositories."""
    all_commit_data: List[Dict[str, Any]] = []
    file_mod_count = 0
    commit_count = 0
    for repo_name, commits in repo_commit_map.items():
        repo_path = os.path.join(input_dir, repo_name)
        try:
            for commit in commits:
                commit: Commit
                commit_hash = commit.hexsha
                commit_message = commit.message.strip()
                issue_refs = extract_issue_references(str(commit_message))
                commit_data: Dict[str, Any] = {
                    "repo_name": repo_name,
                    "commit_hash": commit_hash,
                    "commit_message": commit_message,
                    "commit_timestamp": int(commit.committed_date),
                    "commit_author": commit.author.name,
                    "modified_files": [],
                    "issue_references": issue_refs,
                }
                for parent in commit.parents or []:
                    diff = commit.diff(parent, create_patch=False)
                    for d in diff:
                        if d.a_path:
                            commit_data["modified_files"].append(d.a_path)
                            file_mod_count += 1
                if not commit.parents:
                    # Why: For the initial commit, all files are considered added.
                    for tup in commit.tree.traverse():
                        # Support both: direct object or TraversedTreeTup
                        obj = tup[1] if isinstance(tup, tuple) and len(tup) > 1 else tup
                        if hasattr(obj, "type") and hasattr(obj, "path"):
                            if obj.type == "blob":
                                commit_data["modified_files"].append(obj.path)
                                file_mod_count += 1
                all_commit_data.append(commit_data)
                commit_count += 1
                progress.advance(overall_task)
        except InvalidGitRepositoryError:
            # Why: Skip directories that are not valid git repositories.
            continue
        except Exception as exc:
            # Why: Log and skip any other repo-level errors, but don't halt extraction.
            logger.warning(f"Error processing repo {repo_path}: {exc}")
            continue
    return all_commit_data


def write_ttl(
    all_commit_data: List[Dict[str, Any]],
    prop_cache: dict,
    class_cache: dict,
    input_dir: str,
    progress,
    ttl_task,
    g: Graph,
) -> tuple:
    """Write commit, repository, issue, and file data to the RDF graph."""
    processed_repos: set[str] = set()
    processed_issues: set[str] = set()
    repos_added = 0
    commits_added = 0
    issues_added = 0
    file_mod_count = 0
    for commit_data in all_commit_data:
        repo_name: str = commit_data["repo_name"]
        repo_uri = get_repo_uri(repo_name)
        if repo_name not in processed_repos:
            g.add((repo_uri, RDF.type, class_cache["Repository"]))
            g.add(
                (
                    repo_uri,
                    RDFS.label,
                    Literal(f"Repository: {repo_name}", datatype=XSD.string),
                )
            )
            if "hasSourceRepositoryURL" in prop_cache:
                repo_path = os.path.join(input_dir, repo_name)
                try:
                    repo = Repo(repo_path)
                    origin_url = repo.remotes.origin.url if repo.remotes else None
                    if origin_url:
                        https_url = None
                        if origin_url.startswith("git@github.com:"):
                            https_url = (
                                "https://github.com/" + origin_url.split(":", 1)[1]
                            )
                        elif origin_url.startswith("ssh://git@github.com/"):
                            https_url = (
                                "https://github.com/"
                                + origin_url.split("ssh://git@github.com/", 1)[1]
                            )
                        elif origin_url.startswith("http://") or origin_url.startswith(
                            "https://"
                        ):
                            https_url = origin_url
                        if https_url and (
                            https_url.startswith("http://")
                            or https_url.startswith("https://")
                        ):
                            g.add(
                                (
                                    repo_uri,
                                    prop_cache["hasSourceRepositoryURL"],
                                    Literal(https_url, datatype=XSD.anyURI),
                                )
                            )
                except Exception:
                    pass
            processed_repos.add(repo_name)
            repos_added += 1
        commit_uri = get_commit_uri(repo_name, commit_data["commit_hash"])
        g.add((commit_uri, RDF.type, class_cache["Commit"]))
        short_hash = commit_data["commit_hash"][:7]
        commit_msg_snippet = commit_data["commit_message"][:50].replace("\n", " ")
        g.add(
            (
                commit_uri,
                RDFS.label,
                Literal(
                    f"Commit: {short_hash} ({commit_msg_snippet})", datatype=XSD.string
                ),
            )
        )
        g.add(
            (
                commit_uri,
                prop_cache["hasCommitHash"],
                Literal(commit_data["commit_hash"], datatype=XSD.string),
            )
        )
        commit_msg_uri = get_commit_message_uri(repo_name, commit_data["commit_hash"])
        g.add(
            (
                commit_msg_uri,
                RDF.type,
                class_cache.get(
                    "CommitMessage", class_cache["InformationContentEntity"]
                ),
            )
        )
        g.add(
            (
                commit_msg_uri,
                RDFS.label,
                Literal(f"CommitMessage: {commit_msg_snippet}", datatype=XSD.string),
            )
        )
        content_prop = prop_cache.get("hasContent") or prop_cache.get("hasTextValue")
        if content_prop:
            g.add(
                (
                    commit_msg_uri,
                    content_prop,
                    Literal(commit_data["commit_message"], datatype=XSD.string),
                )
            )
        g.add((commit_uri, prop_cache["hasCommitMessage"], commit_msg_uri))
        g.add((commit_msg_uri, prop_cache["isMessageOfCommit"], commit_uri))
        g.add((repo_uri, prop_cache["hasCommit"], commit_uri))
        g.add((commit_uri, prop_cache["isCommitIn"], repo_uri))
        for issue_id in commit_data["issue_references"]:
            issue_uri = get_issue_uri(repo_name, issue_id)
            if issue_id not in processed_issues:
                g.add((issue_uri, RDF.type, class_cache["Issue"]))
                g.add(
                    (
                        issue_uri,
                        RDFS.label,
                        Literal(f"Issue: #{issue_id}", datatype=XSD.string),
                    )
                )
                processed_issues.add(issue_id)
                issues_added += 1
            g.add((commit_uri, prop_cache["addressesIssue"], issue_uri))
            g.add((issue_uri, prop_cache["isAddressedBy"], commit_uri))
            commit_message_lower = commit_data["commit_message"].lower()
            fix_keywords = [
                "fix",
                "fixes",
                "fixed",
                "close",
                "closes",
                "closed",
                "resolve",
                "resolves",
                "resolved",
            ]
            if any(keyword in commit_message_lower for keyword in fix_keywords):
                g.add((commit_uri, prop_cache["fixesIssue"], issue_uri))
                g.add((issue_uri, prop_cache["isFixedBy"], commit_uri))
        for file_path in commit_data["modified_files"]:
            file_path_str: str = str(file_path)
            file_uri = get_file_uri(repo_name, file_path_str)
            g.add(
                (
                    file_uri,
                    RDFS.label,
                    Literal(f"File: {file_path_str}", datatype=XSD.string),
                )
            )
            g.add((commit_uri, prop_cache["modifies"], file_uri))
            g.add((file_uri, prop_cache["isModifiedBy"], commit_uri))
            g.add((repo_uri, prop_cache.get("hasFile", WDO.hasFile), file_uri))
            file_mod_count += 1
        commits_added += 1
        progress.advance(ttl_task)
    return repos_added, commits_added, issues_added, file_mod_count


def load_or_create_graph(ttl_path: str) -> Graph:
    """Load an existing RDF graph from TTL or create a new one."""
    g = Graph()
    if os.path.exists(ttl_path):
        g.parse(ttl_path, format="turtle")
        logger.info(f"Loaded existing graph with {len(g)} triples")
    else:
        logger.info("No existing TTL file found, starting with empty graph")
    return g


def main() -> None:
    """Orchestrate the git extraction process."""
    setup_logging()
    console = Console()
    logger.info("Starting Git extraction process...")
    ontology_cache, prop_cache, class_cache = load_ontology_and_cache()
    logger.info(f"Available properties: {list(prop_cache.keys())}")
    logger.info(f"Available classes: {list(class_cache.keys())}")
    logger.info(f"hasContent in prop_cache: {'hasContent' in prop_cache}")
    logger.info(f"hasTextValue in prop_cache: {'hasTextValue' in prop_cache}")
    g = load_or_create_graph(TTL_PATH)
    scan_result = scan_repositories(INPUT_DIR)
    repo_commit_map = scan_result["repo_commit_map"]
    total_repos = scan_result["total_repos"]
    total_commits = scan_result["total_commits"]
    logger.info(
        f"Found {total_repos} Git repositories with {total_commits} total commits"
    )
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        overall_task = progress.add_task(
            "[blue]Processing Git repositories and commits...", total=total_commits
        )
        all_commit_data = extract_commit_data(
            repo_commit_map, INPUT_DIR, progress, overall_task
        )
        logger.info("Commit processing complete. Writing TTL...")
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(all_commit_data))
        repos_added, commits_added, issues_added, file_mod_count = write_ttl(
            all_commit_data, prop_cache, class_cache, INPUT_DIR, progress, ttl_task, g
        )
    g.serialize(destination=TTL_PATH, format="turtle")
    logger.info(
        f"Git extraction complete: {total_repos} repos, {len(all_commit_data)} commits, {file_mod_count} file modifications"
    )
    logger.info(f"Total triples in graph: {len(g)}")
    logger.info(
        f"Added to graph: {repos_added} repos, {commits_added} commits, {issues_added} issues"
    )
    console.print(
        f"[bold green]Git extraction complete:[/bold green] {total_repos} repos, {len(all_commit_data)} commits, {file_mod_count} file modifications"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


if __name__ == "__main__":
    main()
