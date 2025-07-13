"""Git commit and repository metadata extraction for Semantic Web KMS."""

import logging
import os
import re
from typing import Any, Dict, List, Set

from git import InvalidGitRepositoryError, Repo
from git.objects.commit import Commit
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from app.core.namespaces import FOAF_PERSON_URI, INST
from app.core.ontology_cache import (
    get_extraction_classes,
    get_extraction_properties,
    get_ontology_cache,
)
from app.core.paths import (
    get_input_dir,
    get_log_path,
    get_output_path,
    uri_safe_file_path,
    uri_safe_string,
)
from app.core.progress_tracker import get_current_tracker

logger = logging.getLogger("git_extractor")

# Ontology and file paths are now set inside main()


class ContributorRegistry:
    """Registry to manage unique contributor URIs across the entire extraction process."""

    def __init__(self):
        """Initialize the contributor registry with an empty dictionary."""
        self._contributor_uris: Dict[str, URIRef] = {}

    def normalize_contributor_name(self, name: str) -> str:
        """
        Normalize contributor name to handle edge cases like "Hamid HAMZA" -> "Hamid Hamza".

        Args:
            name: The original contributor name.

        Returns:
            str: The normalized contributor name.
        """
        if not name:
            return ""

        # Split the name into parts
        parts = name.strip().split()
        if not parts:
            return ""

        # Normalize each part: capitalize first letter, lowercase the rest
        normalized_parts = []
        for part in parts:
            if part:
                # Handle edge cases like "HAMZA" -> "Hamza"
                if part.isupper() and len(part) > 1:
                    normalized_parts.append(part.capitalize())
                else:
                    # Normal case: capitalize first letter, lowercase the rest
                    normalized_parts.append(part.capitalize())

        return " ".join(normalized_parts)

    def get_or_create_contributor_uri(self, contributor_name: str) -> URIRef:
        """
        Get existing contributor URI or create a new one if it doesn't exist.

        Args:
            contributor_name: The name of the contributor.

        Returns:
            URIRef: The URI for the contributor (either existing or newly created).
        """
        normalized_name = self.normalize_contributor_name(contributor_name)
        if normalized_name not in self._contributor_uris:
            # Create a new URI for this contributor
            safe_name = uri_safe_string(normalized_name)
            contributor_uri = URIRef(f"{INST[f'contributor_{safe_name}']}")
            self._contributor_uris[normalized_name] = contributor_uri
        return self._contributor_uris[normalized_name]

    def get_registered_contributors(self) -> Dict[str, URIRef]:
        """
        Get all registered contributors and their URIs.

        Returns:
            Dict[str, URIRef]: A copy of the internal contributor URI mapping.
        """
        return self._contributor_uris.copy()

    def get_contributor_count(self) -> int:
        """
        Get the total number of unique contributors registered.

        Returns:
            int: The number of unique contributors registered.
        """
        return len(self._contributor_uris)

    def reset(self) -> None:
        """Reset the contributor registry to empty state."""
        self._contributor_uris.clear()

    def log_registered_contributors(self) -> None:
        """Log all registered contributors."""
        if self._contributor_uris:
            logger.info(f"Registered contributors ({len(self._contributor_uris)}):")
            for name, uri in self._contributor_uris.items():
                logger.info(f"  {name} -> {uri}")
        else:
            logger.info("No contributors registered")


# Global contributor registry instance
contributor_registry = ContributorRegistry()


# --- Helper functions for URI construction ---
def get_repo_uri(repo_name: str) -> URIRef:
    """
    Return the URI for a repository resource.

    Args:
        repo_name: Name of the repository.
    Returns:
        URIRef for the repository.
    """
    return URIRef(f"{INST[uri_safe_string(repo_name)]}")


def get_file_uri(repo_name: str, file_path: str) -> URIRef:
    """
    Return the URI for a file resource.

    Args:
        repo_name: Name of the repository.
        file_path: Path to the file within the repository.
    Returns:
        URIRef for the file.
    """
    repo_enc = uri_safe_string(repo_name)
    path_enc = uri_safe_file_path(file_path)
    return URIRef(f"{INST[f'{repo_enc}/{path_enc}']}")


def get_commit_uri(repo_name: str, commit_hash: str) -> URIRef:
    """
    Return the URI for a commit resource.

    Args:
        repo_name: Name of the repository.
        commit_hash: Commit hash string.
    Returns:
        URIRef for the commit.
    """
    repo_enc = uri_safe_string(repo_name)
    hash_enc = uri_safe_string(commit_hash)
    return URIRef(f"{INST[f'{repo_enc}/commit/{hash_enc}']}")


def get_commit_message_uri(repo_name: str, commit_hash: str) -> URIRef:
    """
    Return the URI for a commit message resource.

    Args:
        repo_name: Name of the repository.
        commit_hash: Commit hash string.
    Returns:
        URIRef for the commit message.
    """
    repo_enc = uri_safe_string(repo_name)
    hash_enc = uri_safe_string(commit_hash)
    return URIRef(f"{INST[f'{repo_enc}/commit/{hash_enc}_msg']}")


def get_issue_uri(repo_name: str, issue_id: str) -> URIRef:
    """
    Generate URI for issue entity.

    Args:
        repo_name: Name of the repository.
        issue_id: Issue identifier string.
    Returns:
        URIRef for the issue.
    """
    repo_enc = uri_safe_string(repo_name)
    issue_enc = uri_safe_string(issue_id)
    return URIRef(str(INST[f"{repo_enc}/issue/{issue_enc}"]))


def extract_issue_references(message: str) -> list[str]:
    """
    Extract referenced issue numbers from a commit message.

    Args:
        message: Commit message string.
    Returns:
        List of referenced issue numbers as strings.
    """
    # Why: Enables linking commits to issues for traceability.
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


def get_contributor_uri(repo_name: str, contributor_name: str) -> URIRef:
    """
    Return the URI for a contributor (person) resource.

    Note: This function is deprecated. Use contributor_registry.get_or_create_contributor_uri() instead.

    Args:
        repo_name: Name of the repository.
        contributor_name: Name of the contributor.
    Returns:
        URIRef for the contributor.
    """
    return contributor_registry.get_or_create_contributor_uri(contributor_name)


def get_all_git_contributors(repo_path: str) -> Set[str]:
    """
    Get all unique contributors (authors) from the git log of a repository.

    Args:
        repo_path: Path to the git repository.
    Returns:
        Set of normalized contributor names (strings).
    """
    try:
        repo = Repo(repo_path)
        names = set()
        for commit in repo.iter_commits():
            if commit.author and commit.author.name:
                # Normalize the contributor name using the registry
                normalized_name = contributor_registry.normalize_contributor_name(
                    commit.author.name
                )
                names.add(normalized_name)
        return names
    except Exception:
        return set()


def setup_logging() -> None:
    """
    Configure logging to file for the git extractor.

    Args:
        None
    Returns:
        None
    """
    os.makedirs(os.path.dirname(get_log_path("git_extractor.log")), exist_ok=True)
    logging.basicConfig(
        filename=get_log_path("git_extractor.log"),
        level=logging.INFO,
        format="%s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.setLevel(logging.INFO)


def load_ontology_and_cache():
    """
    Load ontology cache and property/class caches.

    Args:
        None
    Returns:
        Tuple of (ontology_cache, prop_cache, class_cache).
    """
    ontology_cache = get_ontology_cache()
    prop_cache = ontology_cache.get_property_cache(get_extraction_properties())
    class_cache = ontology_cache.get_class_cache(get_extraction_classes())
    return ontology_cache, prop_cache, class_cache


def scan_repositories() -> dict:
    """
    Scan input directory for valid git repositories and their commits.

    Returns:
        Dict with repo_commit_map, total_repos, and total_commits.
    """
    input_dir = get_input_dir()
    repo_dirs = [
        d
        for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d))
        and os.path.isdir(
            os.path.join(input_dir, d, ".git")
        )  # Only treat as repo if .git exists
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
    """
    Extract commit data from all repositories.

    Args:
        repo_commit_map: Dict mapping repo names to lists of commits.
        input_dir: Path to the input directory as a string.
        progress: Progress bar object for tracking.
        overall_task: Task ID for progress bar.
    Returns:
        List of commit data dicts.
    """
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
                        # Use current path (b_path) if available, otherwise fall back to old path (a_path)
                        file_path = d.b_path if d.b_path else d.a_path
                        if file_path:
                            commit_data["modified_files"].append(file_path)
                            file_mod_count += 1
                if not commit.parents:
                    # Why: For the initial commit, all files are considered added.
                    for tup in commit.tree.traverse():
                        obj = tup[1] if isinstance(tup, tuple) and len(tup) > 1 else tup
                        # Only access .type and .path if they exist
                        if hasattr(obj, "type") and hasattr(obj, "path"):
                            if getattr(obj, "type", None) == "blob":
                                commit_data["modified_files"].append(
                                    getattr(obj, "path", None)
                                )
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
    """
    Write commit, repository, issue, file, and contributor data to the RDF graph.

    Args:
        all_commit_data: List of commit data dicts.
        prop_cache: Dict of ontology property URIs.
        class_cache: Dict of ontology class URIs.
        input_dir: Path to the input directory as a string.
        progress: Progress bar object for tracking.
        ttl_task: Task ID for progress bar.
        g: RDFLib Graph to add triples to.
    Returns:
        Tuple of (repos_added, commits_added, issues_added, file_mod_count).
    """
    processed_repos: set[str] = set()
    processed_issues: set[str] = set()
    repos_added = 0
    commits_added = 0
    issues_added = 0
    file_mod_count = 0
    referenced_issue_uris: set = set()
    for commit_data in all_commit_data:
        repo_name: str = commit_data["repo_name"]
        repo_uri = get_repo_uri(repo_name)
        repo_path = os.path.join(input_dir, repo_name)
        # Add contributors for this repo (once per repo)
        if repo_name not in processed_repos:
            g.add((repo_uri, RDF.type, class_cache["Repository"]))
            g.add((repo_uri, RDFS.label, Literal(f"{repo_name}", datatype=XSD.string)))
            if "hasSourceRepositoryURL" in prop_cache:
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
                except Exception as e:
                    print(f"Warning: Could not process repository URL: {e}")
            # --- Add contributors ---
            contributors = get_all_git_contributors(repo_path)
            for contributor_name in contributors:
                contributor_uri = contributor_registry.get_or_create_contributor_uri(
                    contributor_name
                )
                # Only add type/label if this is a new contributor instance in the graph
                if (
                    not (
                        contributor_uri,
                        RDF.type,
                        class_cache.get("Contributor", FOAF_PERSON_URI),
                    )
                    in g
                ):
                    g.add(
                        (
                            contributor_uri,
                            RDF.type,
                            class_cache.get("Contributor", FOAF_PERSON_URI),
                        )
                    )
                    g.add(
                        (
                            contributor_uri,
                            RDFS.label,
                            Literal(contributor_name, datatype=XSD.string),
                        )
                    )
                # Add hasContributor and contributesTo relationships
                g.add((repo_uri, prop_cache["hasContributor"], contributor_uri))
                g.add((contributor_uri, prop_cache["contributesTo"], repo_uri))
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
                    f"commit: {short_hash} ({commit_msg_snippet})", datatype=XSD.string
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
        # --- Add committer relationship ---
        committer_name = commit_data.get("commit_author")
        if committer_name:
            # Normalize the committer name
            normalized_committer_name = contributor_registry.normalize_contributor_name(
                committer_name
            )
            committer_uri = contributor_registry.get_or_create_contributor_uri(
                normalized_committer_name
            )
            g.add((commit_uri, prop_cache["committedBy"], committer_uri))
            # Add the inverse relationship: contributor 'committed' commit
            if "committed" in prop_cache:
                g.add((committer_uri, prop_cache["committed"], commit_uri))
            # Only add type/label if this is a new contributor instance in the graph
            if (
                not (
                    committer_uri,
                    RDF.type,
                    class_cache.get("Contributor", FOAF_PERSON_URI),
                )
                in g
            ):
                g.add(
                    (
                        committer_uri,
                        RDF.type,
                        class_cache.get("Contributor", FOAF_PERSON_URI),
                    )
                )
                g.add(
                    (
                        committer_uri,
                        RDFS.label,
                        Literal(normalized_committer_name, datatype=XSD.string),
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
                Literal(f"commitmessage: {commit_msg_snippet}", datatype=XSD.string),
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
            referenced_issue_uris.add((issue_uri, repo_name, issue_id))
            if issue_uri not in processed_issues:
                g.add((issue_uri, RDF.type, class_cache["Issue"]))
                g.add(
                    (
                        issue_uri,
                        RDFS.label,
                        Literal(f"issue: {repo_name} {issue_id}", datatype=XSD.string),
                    )
                )
                processed_issues.add(issue_uri)
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
            # Use the existing file URI (without 'file_' prefix or new instance creation)
            file_uri = get_file_uri(repo_name, file_path_str)
            # Only add the modifies/isModifiedBy relationships, do not add label or type for the file
            g.add((commit_uri, prop_cache["modifies"], file_uri))
            g.add((file_uri, prop_cache["isModifiedBy"], commit_uri))
            # Do NOT add label/type/instance for file_uri here; assume it already exists
            file_mod_count += 1
        commits_added += 1
        progress.advance(ttl_task)
    # Ensure every referenced issue URI has rdf:type and rdfs:label
    for issue_uri, repo_name, issue_id in referenced_issue_uris:
        if (issue_uri, RDF.type, class_cache["Issue"]) not in g:
            g.add((issue_uri, RDF.type, class_cache["Issue"]))
        if (issue_uri, RDFS.label, None) not in g:
            g.add(
                (
                    issue_uri,
                    RDFS.label,
                    Literal(f"issue: {repo_name} {issue_id}", datatype=XSD.string),
                )
            )
    return repos_added, commits_added, issues_added, file_mod_count


def load_or_create_graph(ttl_path: str) -> Graph:
    """
    Load an existing RDF graph from TTL or create a new one.

    Args:
        ttl_path: Path to the TTL file as a string.
    Returns:
        RDFLib Graph object.
    """
    g = Graph()
    if os.path.exists(ttl_path):
        g.parse(ttl_path, format="turtle")
        logger.info(f"Loaded existing graph with {len(g)} triples")
    else:
        logger.info("No existing TTL file found, starting with empty graph")
    return g


def main() -> None:
    """
    Orchestrate the git extraction process for the semantic web KMS.

    Returns:
        None. Writes output to file and logs progress.

    Raises:
        Exceptions may propagate if configuration files are missing or unreadable.
    """
    setup_logging()
    console = Console()
    logger.info("Starting Git extraction process...")
    ontology_cache, prop_cache, class_cache = load_ontology_and_cache()
    logger.info(f"Available properties: {list(prop_cache.keys())}")
    logger.info(f"Available classes: {list(class_cache.keys())}")
    logger.info(f"hasContent in prop_cache: {'hasContent' in prop_cache}")
    logger.info(f"hasTextValue in prop_cache: {'hasTextValue' in prop_cache}")
    g = load_or_create_graph(get_output_path("wdkb.ttl"))
    scan_result = scan_repositories()
    repo_commit_map = scan_result["repo_commit_map"]
    total_repos = scan_result["total_repos"]
    total_commits = scan_result["total_commits"]
    logger.info(
        f"Found {total_repos} Git repositories with {total_commits} total commits"
    )
    tracker = get_current_tracker()
    # Define custom progress bar with green completion styling
    bar_column = BarColumn(
        bar_width=30,  # Thinner bar width
        style="blue",  # Style for the incomplete part of the bar
        complete_style="bold blue",  # Style for the completed part
        finished_style="bold green",  # Style when task is 100% complete
    )

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        bar_column,  # Use custom bar column
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        if tracker:
            tracker.update_stage(
                "gitExtraction", "processing", 0, "Starting git extraction..."
            )
        overall_task = progress.add_task(
            "[blue]Processing Git repositories...", total=total_commits
        )
        processed_commits = 0
        all_commit_data = []
        file_mod_count = 0  # Initialize file_mod_count
        for repo, commits in repo_commit_map.items():
            for commit in commits:
                commit: Commit
                commit_hash = commit.hexsha
                commit_message = commit.message.strip()
                issue_refs = extract_issue_references(str(commit_message))
                commit_data: Dict[str, Any] = {
                    "repo_name": repo,
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
                        # Use current path (b_path) if available, otherwise fall back to old path (a_path)
                        file_path = d.b_path if d.b_path else d.a_path
                        if file_path:
                            commit_data["modified_files"].append(file_path)
                            file_mod_count += 1
                if not commit.parents:
                    # Why: For the initial commit, all files are considered added.
                    for tup in commit.tree.traverse():
                        obj = tup[1] if isinstance(tup, tuple) and len(tup) > 1 else tup
                        # Only access .type and .path if they exist
                        if hasattr(obj, "type") and hasattr(obj, "path"):
                            if getattr(obj, "type", None) == "blob":
                                commit_data["modified_files"].append(
                                    getattr(obj, "path", None)
                                )
                                file_mod_count += 1
                all_commit_data.append(commit_data)
                processed_commits += 1
                progress.advance(overall_task)
                if tracker and (
                    processed_commits % 10 == 0 or processed_commits == total_commits
                ):
                    progress_percentage = int((processed_commits / total_commits) * 60)
                    tracker.update_stage(
                        "gitExtraction",
                        "processing",
                        progress_percentage,
                        f"Processing commits: {processed_commits}/{total_commits}",
                    )
        if tracker:
            tracker.update_stage(
                "gitExtraction",
                "processing",
                60,
                f"Writing ontology: {processed_commits} commits...",
            )
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(all_commit_data))

        class ProgressWrapper:
            def __init__(self, rich_progress, rich_task, tracker):
                self.rich_progress = rich_progress
                self.rich_task = rich_task
                self.tracker = tracker
                self.processed = 0
                self.total = len(all_commit_data)
                self.tasks = {rich_task: type("Task", (), {"total": self.total})()}

            def advance(self, task):
                self.rich_progress.advance(self.rich_task)
                self.processed += 1
                if self.tracker and (
                    self.processed % 10 == 0 or self.processed == self.total
                ):
                    progress_percentage = 60 + int((self.processed / self.total) * 40)
                    self.tracker.update_stage(
                        "gitExtraction",
                        "processing",
                        progress_percentage,
                        f"Writing ontology: {self.processed}/{self.total} commits",
                    )

            def update(self, task, **kwargs):
                self.rich_progress.update(self.rich_task, **kwargs)

        progress_wrapper = ProgressWrapper(progress, ttl_task, tracker)
        repos_added, commits_added, issues_added, ttl_file_mod_count = write_ttl(
            all_commit_data,
            prop_cache,
            class_cache,
            get_input_dir(),
            progress_wrapper,
            ttl_task,
            g,
        )
        # Add the TTL file modifications to the total
        file_mod_count += ttl_file_mod_count
    g.serialize(destination=get_output_path("wdkb.ttl"), format="turtle")
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
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{get_output_path("wdkb.ttl")}[/cyan]"
    )
    contributor_registry.log_registered_contributors()


if __name__ == "__main__":
    main()
