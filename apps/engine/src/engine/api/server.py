"""Flask API server for Semantic Web KMS."""

import logging
import os
import re
import shutil
import tempfile
from datetime import datetime
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import pathlib

import requests
from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS

from engine.core.config import settings
from engine.core.paths import PathManager
from engine.core.progress_tracker import create_tracker, get_tracker_by_id

logger = logging.getLogger(__name__)

# Set AllegroGraph config in Flask app config
app = Flask(__name__)
app.config["AGRAPH_URL"] = settings.AGRAPH_CLOUD_URL or settings.AGRAPH_SERVER_URL
app.config["AGRAPH_REPO"] = settings.AGRAPH_REPO
app.config["AGRAPH_USER"] = settings.AGRAPH_USERNAME
app.config["AGRAPH_PASS"] = settings.AGRAPH_PASSWORD

# Configure CORS for frontend communication
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
CORS(
    app,
    origins=cors_origins,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    supports_credentials=True,
)

# Initialize Flask-Caching with better configuration
cache = Cache(
    app,
    config={
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 60,  # 1 minute default
        "CACHE_THRESHOLD": 1000,  # Maximum number of items in cache
    },
)

# Global session for connection pooling
_agraph_session = None


def get_agraph_session():
    """
    Get or create a global session for AllegroGraph connections.

    Returns:
        requests.Session: The global session for AllegroGraph connections.
    """
    global _agraph_session
    if _agraph_session is None:
        _agraph_session = requests.Session()
        user = app.config["AGRAPH_USER"]
        pw = app.config["AGRAPH_PASS"]
        if user and pw:
            _agraph_session.auth = (user, pw)
    return _agraph_session


DASHBOARD_QUERIES = {
    "repositories": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT (COUNT(DISTINCT ?repo) AS ?count)
        WHERE {
            ?repo a wdo:Repository .
        }
    """,
    "files": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:DigitalInformationCarrier .
        }
    """,
    "source_files": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:SourceCodeFile .
        }
    """,
    "doc_files": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:DocumentationFile .
        }
    """,
    "asset_files": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:AssetFile .
        }
    """,
    "all_entities": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?entity) AS ?count)
        WHERE {
            ?entity a ?entityType .
            ?entityType rdfs:subClassOf* wdo:InformationContentEntity .
        }
    """,
    "functions": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?func) AS ?count)
        WHERE {
            ?func a ?funcType .
            ?funcType rdfs:subClassOf* wdo:FunctionDefinition .
        }
    """,
    "classes": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?class) AS ?count)
        WHERE {
            ?class a ?classType .
            ?classType rdfs:subClassOf* wdo:ClassDefinition .
        }
    """,
    "interfaces": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?interface) AS ?count)
        WHERE {
            ?interface a ?interfaceType .
            ?interfaceType rdfs:subClassOf* wdo:InterfaceDefinition .
        }
    """,
    "attributes": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?attr) AS ?count)
        WHERE {
            ?attr a ?attrType .
            ?attrType rdfs:subClassOf* wdo:AttributeDeclaration .
        }
    """,
    "variables": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?var) AS ?count)
        WHERE {
            ?var a ?varType .
            ?varType rdfs:subClassOf* wdo:VariableDeclaration .
        }
    """,
    "parameters": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?param) AS ?count)
        WHERE {
            ?param a ?paramType .
            ?paramType rdfs:subClassOf* wdo:Parameter .
        }
    """,
    "relationships": """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT (COUNT(*) AS ?count)
        WHERE {
            ?s ?p ?o .
            ?p a owl:ObjectProperty .
        }
    """,
    "imports": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT (COUNT(*) AS ?count)
        WHERE {
            ?s wdo:imports ?o .
        }
    """,
    "complexity": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (AVG(?complexity) AS ?avg) (SUM(?complexity) AS ?sum)
        WHERE {
            ?func a ?funcType .
            ?funcType rdfs:subClassOf* wdo:FunctionDefinition .
            ?func wdo:hasCyclomaticComplexity ?complexity .
        }
    """,
    "language_distribution": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?extension (COUNT(DISTINCT ?file) AS ?files)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:SourceCodeFile .
            ?file wdo:hasExtension ?extension .
        }
        GROUP BY ?extension
        ORDER BY DESC(?files)
    """,
    "documentation": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?doc) AS ?count)
        WHERE {
            ?doc a ?docType .
            ?docType rdfs:subClassOf* wdo:Documentation .
        }
    """,
    "commits": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?commit) AS ?count)
        WHERE {
            ?commit a ?commitType .
            ?commitType rdfs:subClassOf* wdo:Commit .
        }
    """,
    "issues": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?issue) AS ?count)
        WHERE {
            ?issue a ?issueType .
            ?issueType rdfs:subClassOf* wdo:Issue .
        }
    """,
    "contributors": """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?person) AS ?count)
        WHERE {
            ?person a ?personType .
            ?personType rdfs:subClassOf* wdo:Contributor .
        }
    """,
}


def _map_dashboard_query_result(query_name: str, binding: dict, results: dict) -> None:
    """Map the result of a single dashboard query to the results dictionary."""
    mapping = {
        "repositories": lambda b: (
            "totalRepos",
            int(b.get("count", {}).get("value", "0")),
        ),
        "files": lambda b: ("totalFiles", int(b.get("count", {}).get("value", "0"))),
        "source_files": lambda b: (
            "sourceFiles",
            int(b.get("count", {}).get("value", "0")),
        ),
        "doc_files": lambda b: ("docFiles", int(b.get("count", {}).get("value", "0"))),
        "asset_files": lambda b: (
            "assetFiles",
            int(b.get("count", {}).get("value", "0")),
        ),
        "all_entities": lambda b: (
            "totalAllEntities",
            int(b.get("count", {}).get("value", "0")),
        ),
        "functions": lambda b: (
            "totalFunctions",
            int(b.get("count", {}).get("value", "0")),
        ),
        "classes": lambda b: (
            "totalClasses",
            int(b.get("count", {}).get("value", "0")),
        ),
        "interfaces": lambda b: (
            "totalInterfaces",
            int(b.get("count", {}).get("value", "0")),
        ),
        "attributes": lambda b: (
            "totalAttributes",
            int(b.get("count", {}).get("value", "0")),
        ),
        "variables": lambda b: (
            "totalVariables",
            int(b.get("count", {}).get("value", "0")),
        ),
        "parameters": lambda b: (
            "totalParameters",
            int(b.get("count", {}).get("value", "0")),
        ),
        "relationships": lambda b: (
            "totalRelationships",
            int(b.get("count", {}).get("value", "0")),
        ),
        "imports": lambda b: (
            "totalImports",
            int(b.get("count", {}).get("value", "0")),
        ),
        "complexity": lambda b: [
            ("averageComplexity", _safe_float(b.get("avg", {}).get("value", "0"))),
            ("totalComplexity", _safe_int(b.get("sum", {}).get("value", "0"))),
        ],
        "documentation": lambda b: (
            "totalDocumentation",
            int(b.get("count", {}).get("value", "0")),
        ),
        "commits": lambda b: (
            "totalCommits",
            int(b.get("count", {}).get("value", "0")),
        ),
        "issues": lambda b: ("totalIssues", int(b.get("count", {}).get("value", "0"))),
        "contributors": lambda b: (
            "totalContributors",
            int(b.get("count", {}).get("value", "0")),
        ),
    }
    if query_name == "complexity":
        for key, value in mapping[query_name](binding):
            results[key] = value
    elif query_name in mapping:
        key, value = mapping[query_name](binding)
        results[key] = value


def _safe_float(val: str) -> float:
    try:
        return round(float(val), 2)
    except Exception:
        return 0.0


def _safe_int(val: str) -> int:
    try:
        return int(val)
    except Exception:
        return 0


def _run_and_map_dashboard_queries() -> dict[str, int | float | list[dict[str, Any]]]:
    """
    Run all dashboard SPARQL queries and map their results.

    Returns:
        A dictionary containing dashboard statistics and metrics.
    """
    results: dict[str, int | float | list[dict[str, Any]]] = {
        "totalRepos": 0,
        "totalFiles": 0,
        "sourceFiles": 0,
        "docFiles": 0,
        "assetFiles": 0,
        "totalAllEntities": 0,
        "totalFunctions": 0,
        "totalClasses": 0,
        "totalInterfaces": 0,
        "totalAttributes": 0,
        "totalVariables": 0,
        "totalParameters": 0,
        "totalRelationships": 0,
        "totalImports": 0,
        "averageComplexity": 0.0,
        "totalComplexity": 0,
        "totalDocumentation": 0,
        "totalCommits": 0,
        "totalIssues": 0,
        "totalContributors": 0,
        "topLanguages": [],
    }
    for query_name, query in DASHBOARD_QUERIES.items():
        if query_name == "language_distribution":
            continue
        try:
            data = run_dashboard_sparql(query)
            bindings = data["results"]["bindings"]
            if bindings and bindings[0]:
                _map_dashboard_query_result(query_name, bindings[0], results)
        except Exception as e:
            logger.warning(f"Query {query_name} failed: {e}")
    return results


def _get_language_distribution() -> list[dict[str, Any]]:
    """
    Run the language distribution SPARQL query.

    Returns:
        list[dict[str, Any]]: Language distribution data.
    """
    try:
        data = run_dashboard_sparql(DASHBOARD_QUERIES["language_distribution"])
        bindings = data["results"]["bindings"]
        total = sum(int(b["files"]["value"]) for b in bindings) or 1
        extension_to_language = {
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".py": "python",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "c_sharp",
            ".sh": "bash",
            ".swift": "swift",
            ".lua": "lua",
            ".scala": "scala",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
        }
        top_languages = []
        for b in bindings:
            extension = b["extension"]["value"]
            files = int(b["files"]["value"])
            percentage = round(files / total * 100, 2)
            language = extension_to_language.get(extension, extension.lstrip("."))
            top_languages.append({
                "language": language,
                "entities": files,
                "percentage": percentage,
            })
        return top_languages
    except Exception as e:
        logger.warning(f"Language distribution query failed: {e}")
        return []


def _transform_dashboard_results(results: dict[str, Any]) -> dict[str, Any]:
    """
    Transform dashboard results to match frontend expectations.

    Args:
        results (dict[str, Any]): The raw dashboard results.

    Returns:
        dict[str, Any]: The transformed dashboard results for the frontend.
    """
    return {
        "totalEntities": results["totalAllEntities"],
        "totalRelationships": results["totalRelationships"],
        # ... add other transformations as needed ...
        **results,
    }


@cache.cached(timeout=60)
def dashboard_stats() -> Any:
    """
    Return dashboard statistics by running separate memory-efficient SPARQL queries.

    Query parameters:
    - organization: Optional organization ID to filter statistics

    Returns:
        flask.Response: A JSON response containing dashboard statistics
        as key-value pairs.

    Raises:
        Exception: If a SPARQL query fails.

    Side Effects:
        Caches the response for improved performance.
    """
    results = _run_and_map_dashboard_queries()
    results["topLanguages"] = _get_language_distribution()
    transformed_results = _transform_dashboard_results(results)
    return jsonify(transformed_results)


@app.route("/api/progress/<job_id>", methods=["GET"])
def get_progress(job_id: str) -> Any:
    """
    Get the progress for a given job ID.

    Args:
        job_id: The job ID to get progress for.

    Returns:
        JSON response with job status and stage information.
    """
    try:
        tracker = get_tracker_by_id(job_id)
        if tracker:
            return jsonify(tracker.get_job_status())
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get progress: {str(e)}"}), 500


@app.route("/api/progress/<job_id>/stages", methods=["GET"])
def get_progress_stages(job_id: str) -> Any:
    """
    Get all progress stages for a job.

    Args:
        job_id: The job ID to get stage information for.

    Returns:
        JSON response with stage details.
    """
    try:
        tracker = get_tracker_by_id(job_id)
        if tracker:
            stages = tracker.get_all_stages()
            return jsonify({key: stage.to_dict() for key, stage in stages.items()})
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get stages: {str(e)}"}), 500


@app.route("/api/progress/<job_id>/stages/<stage_key>", methods=["GET"])
def get_progress_stage(job_id: str, stage_key: str) -> Any:
    """
    Get a specific progress stage for a job.

    Args:
        job_id: The job ID.
        stage_key: The stage key to get information for.

    Returns:
        JSON response with stage information.
    """
    try:
        tracker = get_tracker_by_id(job_id)
        if tracker:
            stage = tracker.get_stage(stage_key)
            if stage:
                return jsonify(stage.to_dict())
            else:
                return jsonify({"error": "Stage not found"}), 404
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to get stage: {str(e)}"}), 500


@app.route("/api/organizations/analyze", methods=["POST"])
def analyze_organization() -> Any:
    """
    Analyze an uploaded organization directory.

    Returns:
        JSON response with job ID and initial status.
    """
    try:
        data = request.get_json()
        organization_name = data.get("name")

        if not organization_name:
            return jsonify({"error": "Organization name is required"}), 400

        # Create a job ID based on organization name and timestamp
        import time

        job_id = f"{organization_name}_{int(time.time())}"

        # Create a new tracker
        tracker = create_tracker(job_id)
        tracker.start_job()

        # Start the analysis in a background thread
        import threading

        def run_analysis():
            try:
                logger.info(f"[Job {job_id}] Starting triplestore clear...")
                # Clear the triplestore before loading new data
                try:
                    clear_query = """
                    DELETE { ?s ?p ?o }
                    WHERE  { ?s ?p ?o }
                    """
                    if (
                        app.config["AGRAPH_URL"]
                        and "/repositories/" in app.config["AGRAPH_URL"]
                    ):
                        agraph_endpoint = app.config["AGRAPH_URL"]
                    else:
                        agraph_endpoint = (
                            f"{app.config['AGRAPH_URL']}/repositories/"
                            f"{app.config['AGRAPH_REPO']}"
                        )
                    headers = {"Accept": "application/sparql-results+json"}
                    session = get_agraph_session()
                    resp = session.post(
                        agraph_endpoint,
                        data={"update": clear_query},
                        headers=headers,
                        timeout=60,
                    )
                    logger.info(f"[Job {job_id}] Triplestore clear: {resp.status_code}")
                    if resp.status_code != 200:
                        logger.warning(f"Failed to clear triplestore: {resp.text}")
                    else:
                        logger.info("Triplestore cleared before new upload.")
                except Exception as clear_exc:
                    logger.warning(f"Exception clearing triplestore: {clear_exc}")

                # Set the input directory for the pipeline
                # TODO: Set input directory for pipeline if needed

                # Import and run the knowledge pipeline
                from engine.knowledge_pipeline import main as run_pipeline

                run_pipeline()
            except Exception as e:
                logger.error(f"[Job {job_id}] Error in run_analysis: {e}")
                tracker.end_job(success=False, error=str(e))
                logger.info(f"[Job {job_id}] Marked as error.")
            else:
                tracker.end_job(success=True)
                logger.info(f"[Job {job_id}] Marked as completed.")
            # No temp_dir cleanup needed here

        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()

        return jsonify({
            "job_id": job_id,
            "organization": organization_name,
            "status": "started",
            "message": "Analysis started successfully",
        })

    except Exception as e:
        return jsonify({"error": f"Failed to start analysis: {str(e)}"}), 500


def _save_uploaded_files(files, temp_dir):
    """Save uploaded files to the temporary directory."""
    for file in files:
        if file.filename:
            file_path = pathlib.Path(temp_dir) / file.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file.save(str(file_path))


def _clear_triplestore(job_id):
    """Clear the triplestore before loading new data."""
    try:
        clear_query = """
        DELETE { ?s ?p ?o }
        WHERE  { ?s ?p ?o }
        """
        if app.config["AGRAPH_URL"] and "/repositories/" in app.config["AGRAPH_URL"]:
            agraph_endpoint = app.config["AGRAPH_URL"]
        else:
            agraph_endpoint = (
                f"{app.config['AGRAPH_URL']}/repositories/{app.config['AGRAPH_REPO']}"
            )
        headers = {"Accept": "application/sparql-results+json"}
        session = get_agraph_session()
        resp = session.post(
            agraph_endpoint,
            data={"update": clear_query},
            headers=headers,
            timeout=60,
        )
        logger.info(
            f"[Job {job_id}] Triplestore clear finished with status {resp.status_code}"
        )
        if resp.status_code != 200:
            logger.warning(f"Failed to clear triplestore: {resp.text}")
        else:
            logger.info("Triplestore cleared before new upload.")
    except Exception as clear_exc:
        logger.warning(f"Exception clearing triplestore: {clear_exc}")


def _run_upload_analysis(temp_dir, job_id, tracker):
    """
    Run the knowledge pipeline in a background thread, clear triplestore, and cleanup.

    Raises:
        RuntimeError: If the temporary directory cleanup fails.
    """
    try:
        logger.info(f"[Job {job_id}] Starting triplestore clear...")
        _clear_triplestore(job_id)
        # TODO: Set input directory for pipeline if needed
        from engine.knowledge_pipeline import main as run_pipeline

        run_pipeline()
    except Exception as e:
        logger.error(f"[Job {job_id}] Error in run_analysis: {e}")
        tracker.end_job(success=False, error=str(e))
        logger.info(f"[Job {job_id}] Marked as error.")
    else:
        tracker.end_job(success=True)
        logger.info(f"[Job {job_id}] Marked as completed.")
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            logger.warning(
                f"Failed to clean up temporary directory {temp_dir}: {cleanup_error}"
            )
            raise RuntimeError(
                "Failed to clean up temporary directory"
            ) from cleanup_error


@app.route("/api/upload/organization", methods=["POST"])
def upload_organization() -> Any:
    """
    Upload an organization directory for analysis.

    Returns:
        JSON response with job ID and initial status.
    """
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded"}), 400
        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            return jsonify({"error": "No files selected"}), 400
        temp_dir = tempfile.mkdtemp(prefix="org_upload_")
        try:
            _save_uploaded_files(files, temp_dir)
            import time

            job_id = f"upload_{int(time.time())}"
            tracker = create_tracker(job_id)
            tracker.start_job()
            import threading

            thread = threading.Thread(
                target=_run_upload_analysis,
                args=(temp_dir, job_id, tracker),
            )
            thread.daemon = True
            thread.start()
            return jsonify({
                "job_id": job_id,
                "status": "started",
                "message": "File upload and analysis started successfully",
                "files_uploaded": len([f for f in files if f.filename]),
            })
        except Exception as e:
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up temp dir {temp_dir}: {cleanup_error}"
                )
            raise e
    except Exception as e:
        return jsonify({"error": f"Failed to process upload: {str(e)}"}), 500


@app.route("/api/organizations", methods=["GET"])
def get_organizations() -> Any:
    """
    Get a list of all organizations.

    Returns:
        flask.Response: A JSON response containing organization data.
    """
    try:
        sparql = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?org ?name ?repo ?repoName
        WHERE {
            ?org a wdo:Organization .
            OPTIONAL { ?org rdfs:label ?name . }
            ?org wdo:hasRepository ?repo .
            ?repo a wdo:Repository .
            OPTIONAL { ?repo rdfs:label ?repoName . }
        }
        """
        data = run_dashboard_sparql(sparql)
        bindings = data["results"]["bindings"]
        orgs = {}
        for b in bindings:
            org_id = b["org"]["value"]
            org_name = b.get("name", {}).get("value", org_id.split("/")[-1])
            repo_id = b["repo"]["value"]
            repo_name = b.get("repoName", {}).get("value", repo_id.split("/")[-1])
            if org_id not in orgs:
                orgs[org_id] = {"id": org_id, "name": org_name, "repositories": []}
            orgs[org_id]["repositories"].append({"id": repo_id, "name": repo_name})
        # Always return 200 with a list (empty if no orgs)
        return jsonify(list(orgs.values())), 200
    except Exception as e:
        logger.error(f"Error in get_organizations: {str(e)}")
        return jsonify([]), 200


def is_valid_uri(uri: str) -> bool:
    """
    Validate that the input string is a well-formed HTTP(S) URI for SPARQL queries.

    This function prevents SPARQL injection by ensuring only valid, safe URIs are used.
    are interpolated into SPARQL queries. It uses a regex to check for a well-formed
    It uses a regex to check for a well-formed URI and rejects dangerous characters.
    the URI context in SPARQL (e.g., >, ", ', {, }, ;).
    For stricter security, consider additional checks (e.g., whitelisting domains).

    Args:
        uri (str): The URI to validate.

    Returns:
        bool: True if the URI is valid and safe, False otherwise.
    """
    # Reject if dangerous characters are present (SPARQL injection risk)
    if any(c in uri for c in (">", '"', "'", "{", "}", ";")):
        return False
    # Simple regex for URI validation (can be improved for stricter checks)
    return bool(re.match(r"^https?://[^\s]+$", uri))


@app.route("/api/organizations/<path:org_id>", methods=["GET"])
def get_organization(org_id: str) -> Any:
    """
    Get details for a specific organization.

    Args:
        org_id: The organization ID.

    Returns:
        JSON response with organization details including repositories and stats.
    """
    try:
        # Validate org_id as a URI to prevent injection
        if not is_valid_uri(org_id):
            return jsonify({"error": "Invalid organization ID"}), 400
        # Get organization and its repositories
        sparql = f"""
        SELECT ?org ?name ?repo ?repoName WHERE {{
            <{org_id}> a <http://web-development-ontology.netlify.app/wdo#Organization> .
            OPTIONAL {{ <{org_id}> <http://www.w3.org/2000/01/rdf-schema#label> ?name . }}
            <{org_id}> <http://web-development-ontology.netlify.app/wdo#hasRepository> ?repo .
            ?repo a <http://web-development-ontology.netlify.app/wdo#Repository> .
            OPTIONAL {{ ?repo <http://www.w3.org/2000/01/rdf-schema#label> ?repoName . }}
        }}
        """  # noqa: E501
        data = run_dashboard_sparql(sparql)
        bindings = data["results"]["bindings"]

        if not bindings:
            return jsonify({"error": "Organization not found"}), 404

        org_name = bindings[0].get("name", {}).get("value", org_id.split("/")[-1])
        repositories = []

        for b in bindings:
            repo_id = b["repo"]["value"]
            repo_name = b.get("repoName", {}).get("value", repo_id.split("/")[-1])
            repositories.append({"id": repo_id, "name": repo_name})

        # Scoped file count query for this organization (DigitalInformationCarrier)
        stats_query = f"""
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT (COUNT(DISTINCT ?file) AS ?totalFiles)
        WHERE {{
            <{org_id}> wdo:hasRepository ?repo .
            ?repo wdo:hasFile ?file .
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#DigitalInformationCarrier> .
        }}
        """  # noqa: E501
        # Scoped relationship count query for this organization (VALUES inside WHERE)
        relationships_query = f"""
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT (COUNT(*) AS ?totalRelationships)
        WHERE {{
            ?org wdo:hasRepository ?repo .
            ?repo wdo:hasFile ?file .
            ?file wdo:bearerOfInformation ?entity .
            ?entity ?rel ?target .
            FILTER(isIRI(?target))
            VALUES ?org {{ <{org_id}> }}
        }}
        """
        stats_data = run_dashboard_sparql(stats_query)
        stats_bindings = stats_data["results"]["bindings"]
        rel_data = run_dashboard_sparql(relationships_query)
        rel_bindings = rel_data["results"]["bindings"]

        total_files = 0
        total_relationships = 0
        if stats_bindings:
            total_files = int(stats_bindings[0]["totalFiles"]["value"])
        if rel_bindings:
            total_relationships = int(rel_bindings[0]["totalRelationships"]["value"])

        return jsonify({
            "id": org_id,
            "name": org_name,
            "totalFiles": total_files,
            "totalRelations": total_relationships,
            "repositories": repositories,
        })
    except Exception as e:
        logger.error(f"Error in get_organization: {str(e)}")
        return jsonify({"error": f"Failed to get organization: {str(e)}"}), 500


def _enrich_repository_metadata(repo: dict) -> None:
    """Enrich a repository dict with details."""
    repo_uri = repo["id"]
    if not is_valid_uri(repo_uri):
        logger.error(f"Invalid repository URI: {repo_uri}")
        repo["error"] = f"Invalid repository URI: {repo_uri}"
        return
    # 2. Sample language
    sparql_lang = f"""
    PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
    SELECT (SAMPLE(?lang) AS ?language)
    WHERE {{
      <{repo_uri}> wdo:hasFile ?file .
      ?file wdo:bearerOfInformation|wdo:informationBorneBy ?codeContent .
      ?codeContent wdo:hasProgrammingLanguage ?lang .
    }}
    """
    try:
        lang_data = run_dashboard_sparql(sparql_lang)
        lang_bind = lang_data["results"]["bindings"]
        language = (
            lang_bind[0]["language"]["value"]
            if lang_bind and "language" in lang_bind[0]
            else "Unknown"
        )
    except Exception:
        language = "Unknown"
    repo["language"] = language
    # 3. Average complexity
    sparql_complex = f"""
    PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
    SELECT (AVG(?complexity) AS ?avgComplexity)
    WHERE {{
        <{repo_uri}> a wdo:Repository .
        <{repo_uri}> wdo:hasFile/wdo:bearerOfInformation/wdo:hasCodePart* ?function .
        ?function a wdo:FunctionDefinition ;
                  wdo:hasCyclomaticComplexity ?complexity .
    }}
    """
    try:
        complex_data = run_dashboard_sparql(sparql_complex)
        complex_bind = complex_data["results"]["bindings"]
        avg_complexity = (
            float(complex_bind[0]["avgComplexity"]["value"])
            if complex_bind and "avgComplexity" in complex_bind[0]
            else 0.0
        )
    except Exception:
        avg_complexity = 0.0
    repo["complexity"] = {"average": avg_complexity}
    # 4. Contributor count
    sparql_contrib = f"""
    PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
    SELECT (COUNT(DISTINCT ?contributor) AS ?contributors)
    WHERE {{
      <{repo_uri}> wdo:hasContributor ?contributor .
    }}
    """
    try:
        contrib_data = run_dashboard_sparql(sparql_contrib)
        contrib_bind = contrib_data["results"]["bindings"]
        contributors = (
            int(contrib_bind[0]["contributors"]["value"])
            if contrib_bind and "contributors" in contrib_bind[0]
            else 0
        )
    except Exception:
        contributors = 0
    repo["contributors"] = contributors
    # 5. File count (DigitalInformationCarrier)
    sparql_files = f"""
    PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT (COUNT(DISTINCT ?file) AS ?files)
    WHERE {{
        <{repo_uri}> wdo:hasFile ?file .
        ?file a/rdfs:subClassOf* wdo:DigitalInformationCarrier .
    }}
    """
    try:
        files_data = run_dashboard_sparql(sparql_files)
        files_bind = files_data["results"]["bindings"]
        files = (
            int(files_bind[0]["files"]["value"])
            if files_bind and "files" in files_bind[0]
            else 0
        )
    except Exception:
        files = 0
    repo["files"] = files
    # 6. Editorial note (skos:editorialNote)
    sparql_editorial = f"""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?editorialNote WHERE {{
        <{repo_uri}> skos:editorialNote ?editorialNote .
    }} LIMIT 1
    """
    try:
        editorial_data = run_dashboard_sparql(sparql_editorial)
        editorial_bind = editorial_data["results"]["bindings"]
        editorial_note = (
            editorial_bind[0]["editorialNote"]["value"]
            if editorial_bind and "editorialNote" in editorial_bind[0]
            else ""
        )
    except Exception:
        editorial_note = ""
    repo["editorialNote"] = editorial_note
    # 7. Entity count using BIND instead of VALUES
    sparql_entities = f"""
    PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT (COUNT(DISTINCT ?entity) AS ?entityCount)
    WHERE {{
      BIND(<{repo_uri}> AS ?repo)
      {{
        ?repo wdo:hasFile/wdo:bearerOfInformation ?fileContent .
        ?fileContent (wdo:hasCodePart | wdo:hasMethod | wdo:hasDocumentComponent)* ?entity .
      }}
      UNION
      {{
        ?repo wdo:hasCommit ?commit .
        {{ ?commit wdo:hasCommitMessage ?entity . }}
        UNION
        {{ ?commit (wdo:addressesIssue|wdo:fixesIssue) ?entity . }}
      }}
      ?entity a ?entityTypeRaw .
      FILTER CONTAINS(STR(?entityTypeRaw), "web-development-ontology.netlify.app")
      FILTER(isIRI(?entity))
    }}
    """  # noqa: E501
    try:
        entities_data = run_dashboard_sparql(sparql_entities)
        entities_bind = entities_data["results"]["bindings"]
        entity_count = (
            int(entities_bind[0]["entityCount"]["value"])
            if entities_bind and "entityCount" in entities_bind[0]
            else 0
        )
    except Exception:
        entity_count = 0
    repo["entityCount"] = entity_count


@app.route("/api/repositories", methods=["GET"])
def list_repositories() -> Any:
    """
    List all repositories for an organization.

    Args:
        organization: Optional organization ID to filter repositories

    Returns:
        flask.Response: A JSON response containing a list of repositories with metadata.
    """
    try:
        sparql_basic = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?repo ?name (MAX(?mod) AS ?lastUpdated)
        WHERE {
          ?repo a wdo:Repository .
          OPTIONAL { ?repo rdfs:label ?name. }
          ?repo wdo:hasFile ?file .
          ?file wdo:hasModificationTimestamp ?mod .
        }
        GROUP BY ?repo ?name
        """
        data = run_dashboard_sparql(sparql_basic)
        bindings = data["results"]["bindings"]
        repos = []
        for b in bindings:
            repo_id = b["repo"]["value"]
            name = b.get("name", {}).get("value", "")
            last_updated = b.get("lastUpdated", {}).get("value", "")
            repos.append({
                "id": repo_id,
                "name": name,
                "lastUpdated": last_updated,
            })
        for repo in repos:
            _enrich_repository_metadata(repo)
        return jsonify(repos)
    except Exception as e:
        logger.error(f"Error in list_repositories: {str(e)}")
        return jsonify([]), 200


@app.route("/api/search", methods=["GET"])
def search_entities() -> Any:
    """
    Search for entities in the knowledge graph.

    Query parameters:
    - query: Search term
    - type: Entity type filter (optional)
    - repository: Repository filter (optional)
    - limit: Maximum number of results (optional, default 50)

    Returns:
        JSON response with search results and semantic insights.
    """
    try:
        query = request.args.get("query", "")
        entity_type = request.args.get("type")
        repository = request.args.get("repository")
        limit = int(request.args.get("limit", 50))

        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        # Build SPARQL query based on parameters
        sparql_query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/1994/02/skos/core#>
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT DISTINCT
            ?entity
            ?name
            ?entityType
            ?editorialNote
            ?file
            ?line
            ?repo
            ?confidence
        WHERE {
            ?entity a ?entityType .
            OPTIONAL { ?entity rdfs:label ?name . }
            OPTIONAL { ?entity skos:editorialNote ?editorialNote . }
            OPTIONAL { ?entity wdo:hasSourceFile ?file . }
            OPTIONAL { ?entity wdo:hasLineNumber ?line . }
            OPTIONAL { ?entity wdo:belongsToRepository ?repo . }
            OPTIONAL { ?entity wdo:hasConfidence ?confidence . }
        """

        # Add filters
        # Use SPARQL structure and defined prefixes for filters
        if entity_type:
            sparql_query += f"""
                FILTER(?entityType = wdo:{entity_type})
            """

        if repository:
            sparql_query += f"""
                FILTER(?repo = <{repository}>)
            """

        # Add search filter using SPARQL FILTER and REGEX
        sparql_query += f"""
                FILTER(
                    REGEX(?name, "{query}", "i") ||
                    REGEX(?editorialNote, "{query}", "i")
                )
            }}
            LIMIT {limit}
            """

        # Execute query
        data = run_dashboard_sparql(sparql_query)
        bindings = data["results"]["bindings"]

        # Transform results
        entities = []
        for binding in bindings:
            if "entityType" not in binding:
                continue
            entity_id = binding["entity"]["value"]
            name = binding.get("name", {}).get("value", "Unknown")
            entity_type = binding.get("entityType", {}).get("value", "Unknown")
            entity_type_short = (
                entity_type.split("#")[-1] if entity_type != "Unknown" else "Unknown"
            )
            editorial_note = binding.get("editorialNote", {}).get("value", "")
            file = binding.get("file", {}).get("value", "")
            line = int(binding.get("line", {}).get("value", "0"))
            repo = binding.get("repo", {}).get("value", "")
            confidence = float(binding.get("confidence", {}).get("value", "0.5"))

            # Extract file name from full path
            file_name = file.split("/")[-1] if file else ""

            # Use editorial note as the description
            display_description = editorial_note

            entities.append({
                "id": entity_id,
                "name": name,
                "type": entity_type_short.lower(),
                "repository": repo.split("/")[-1] if repo else "Unknown",
                "description": display_description,
                "editorialNote": editorial_note,
                "enrichedDescription": editorial_note,  # Use editorial note for both
                "confidence": confidence,
                "snippet": f"{entity_type_short}: {name}",
                "file": file_name,
                "line": line,
            })

        # Generate semantic insights (simplified for now)
        semantic_insights = {
            "relatedConcepts": [query, "code", "development"],
            "suggestedQueries": [
                f"{query} patterns",
                f"{query} implementation",
                f"{query} examples",
            ],
            "confidence": 0.8,
        }

        return jsonify({
            "entities": entities,
            "totalCount": len(entities),
            "semanticInsights": semantic_insights,
        })

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


def _post_to_agraph(query: str, return_json: bool = True) -> Any:
    """
    Helper to POST a SPARQL query to AllegroGraph and return the response.

    Args:
        query (str): The SPARQL query string to execute.
        return_json (bool): If True, return parsed JSON; else, return raw response.

    Returns:
        dict or requests.Response: Parsed JSON if return_json is True, else raw response.

    Raises:
        Exception: If the request fails or the response is invalid.
    """
    if app.config["AGRAPH_URL"] and "/repositories/" in app.config["AGRAPH_URL"]:
        agraph_endpoint = app.config["AGRAPH_URL"]
    else:
        agraph_endpoint = (
            f"{app.config['AGRAPH_URL']}/repositories/{app.config['AGRAPH_REPO']}"
        )
    headers = {"Accept": "application/sparql-results+json"}
    auth = (
        (app.config["AGRAPH_USER"], app.config["AGRAPH_PASS"])
        if app.config["AGRAPH_USER"] and app.config["AGRAPH_PASS"]
        else None
    )
    resp = requests.post(
        agraph_endpoint, data={"query": query}, headers=headers, auth=auth, timeout=30
    )
    if return_json:
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"SPARQL query failed: {resp.status_code} {resp.text}")
    return resp


@app.route("/api/sparql", methods=["POST"])
def sparql_query():
    """
    Execute a SPARQL query against the triplestore.

    Returns:
        flask.Response: JSON response with SPARQL query results or error message.

    Raises:
        None. All exceptions are handled and returned as error responses.

    Request JSON:
        {
            "query": "SPARQL query string"
        }

    Response JSON:
        On success: SPARQL query results as JSON.
        On error: {"error": "error message"}
    """
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing query"}), 400
    try:
        result = _post_to_agraph(query, return_json=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/input-directory", methods=["GET"])
def get_input_directory() -> Any:
    """
    Get the input directory for uploads.

    Returns:
        JSON response with the current input directory path.
    """
    try:
        input_dir = os.environ.get("DEFAULT_INPUT_DIR", "~/downloads/repos/Thinkster/")
        pm = PathManager(pathlib.Path(input_dir).expanduser().resolve())
        input_dir = str(pm.input_dir)
        return jsonify({
            "input_directory": input_dir,
            "exists": pathlib.Path(input_dir).exists(),
            "is_directory": (
                pathlib.Path(input_dir).is_dir()
                if pathlib.Path(input_dir).exists()
                else False
            ),
        })
    except RuntimeError:
        # Input directory not set
        return jsonify({
            "input_directory": None,
            "exists": False,
            "is_directory": False,
            "message": "No input directory currently set",
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get input directory: {str(e)}"}), 500


def _build_graph_nodes(bindings) -> tuple[list[dict], set]:
    """
    Build graph nodes and node_ids set from SPARQL bindings.

    Args:
        bindings: SPARQL query result bindings.

    Returns:
        tuple[list[dict], set]: A tuple containing a list of node dictionaries and a
        set of node IDs.
    """
    nodes = []
    node_ids = set()
    for binding in bindings:
        if "entityType" not in binding:
            continue
        entity_id = binding["entity"]["value"]
        name = binding.get("name", {}).get("value", "Unknown")
        entity_type = binding["entityType"]["value"].split("#")[-1]
        repo = binding.get("repo", {}).get("value", "")
        language = binding.get("language", {}).get("value", "")
        if entity_id not in node_ids:
            node_ids.add(entity_id)
            node_type = "concept"
            size = 10
            color = "#3b82f6"
            if entity_type.lower() in ["repository"]:
                node_type = "repository"
                size = 20
                color = "#10b981"
            elif entity_type.lower() in ["file", "sourcefile"]:
                node_type = "file"
                size = 12
                color = "#f59e0b"
            elif entity_type.lower() in ["function", "functiondefinition"]:
                node_type = "function"
                size = 8
                color = "#8b5cf6"
            elif entity_type.lower() in ["class", "classdefinition"]:
                node_type = "class"
                size = 10
                color = "#ef4444"
            nodes.append({
                "id": entity_id,
                "name": name,
                "type": node_type,
                "size": size,
                "color": color,
                "repository": repo.split("/")[-1] if repo else "",
                "language": language,
            })
    return nodes, node_ids


def _build_graph_edges(edges_bindings, node_ids) -> list[dict]:
    """
    Build graph edges from SPARQL edge bindings and node_ids set.

    Args:
        edges_bindings: SPARQL query result bindings for edges.
        node_ids: Set of valid node IDs.

    Returns:
        list[dict]: A list of edge dictionaries for the graph.
    """
    edges = []
    for binding in edges_bindings:
        if "relationship" not in binding:
            continue
        source = binding["source"]["value"]
        target = binding["target"]["value"]
        relationship = binding["relationship"]["value"].split("#")[-1]
        if source in node_ids and target in node_ids:
            edge_type = "depends_on"
            weight = 0.5
            if relationship in ["invokes", "callsFunction"]:
                edge_type = "calls"
                weight = 0.8
            elif relationship in ["extendsType"]:
                edge_type = "extends"
                weight = 0.9
            elif relationship in ["implementsInterface"]:
                edge_type = "implements"
                weight = 0.9
            elif relationship in ["hasFile", "belongsToRepository"]:
                edge_type = "contains"
                weight = 1.0
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": weight,
            })
    return edges


def _build_graph_clusters(nodes) -> list[dict]:
    """
    Build clusters from nodes based on repository.

    Args:
        nodes: List of node dictionaries.

    Returns:
        list[dict]: A list of cluster dictionaries grouped by repository.
    """
    repo_clusters: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if node["repository"]:
            if node["repository"] not in repo_clusters:
                repo_clusters[node["repository"]] = {
                    "id": f"cluster-{node['repository']}",
                    "name": f"{node['repository']} Repository",
                    "nodes": [],
                    "color": node["color"],
                }
            repo_clusters[node["repository"]]["nodes"].append(node["id"])
    return list(repo_clusters.values())


@app.route("/api/graph", methods=["GET"])
def get_graph_data() -> Any:
    """
    Get graph data for visualization.

    Query parameters:
    - layout: Graph layout type (optional)
    - filter: Entity type filter (optional)
    - maxNodes: Maximum number of nodes (optional, default 100)

    Returns:
        JSON response with nodes, edges, and clusters for graph visualization.
    """
    try:
        max_nodes = int(request.args.get("maxNodes", 100))
        sparql_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?entity ?name ?entityType ?repo ?language
        WHERE {
            ?entity a ?entityType .
            OPTIONAL { ?entity rdfs:label ?name . }
            OPTIONAL { ?entity wdo:belongsToRepository ?repo . }
            OPTIONAL { ?entity wdo:hasProgrammingLanguage ?language . }
        """
        filter_type = request.args.get("filter", "all")
        if filter_type != "all":
            sparql_query += """
            FILTER(?entityType = <http://web-development-ontology.netlify.app/wdo#>) .
            """
        sparql_query += f"}} LIMIT {max_nodes}"
        data = run_dashboard_sparql(sparql_query)
        bindings = data["results"]["bindings"]
        nodes, node_ids = _build_graph_nodes(bindings)
        edges_query = """
        SELECT DISTINCT ?source ?target ?relationship
        WHERE {
            ?source ?relationship ?target .
        }
        """  # noqa: E501
        edges_data = run_dashboard_sparql(edges_query)
        edges_bindings = edges_data["results"]["bindings"]
        edges = _build_graph_edges(edges_bindings, node_ids)
        clusters = _build_graph_clusters(nodes)
        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
        })
    except Exception as e:
        logger.error(f"Graph data error: {str(e)}")
        return jsonify({"error": f"Failed to load graph data: {str(e)}"}), 500


def _get_codebase_metrics() -> dict:
    """
    Run SPARQL queries to get codebase metrics for analytics.

    Returns:
        dict: A dictionary containing codebase metrics.
    """
    try:
        repos_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT (COUNT(DISTINCT ?repo) AS ?count)
        WHERE {
            ?repo a wdo:Repository .
        }
        """
        repos_data = run_dashboard_sparql(repos_query)
        total_repos = (
            int(repos_data["results"]["bindings"][0]["count"]["value"])
            if repos_data["results"]["bindings"]
            else 0
        )
        files_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:DigitalInformationCarrier .
        }
        """
        files_data = run_dashboard_sparql(files_query)
        total_files = (
            int(files_data["results"]["bindings"][0]["count"]["value"])
            if files_data["results"]["bindings"]
            else 0
        )
        source_files_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:SourceCodeFile .
        }
        """
        source_files_data = run_dashboard_sparql(source_files_query)
        total_source_files = (
            int(source_files_data["results"]["bindings"][0]["count"]["value"])
            if source_files_data["results"]["bindings"]
            else 0
        )
        doc_files_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:DocumentationFile .
        }
        """
        doc_files_data = run_dashboard_sparql(doc_files_query)
        total_doc_files = (
            int(doc_files_data["results"]["bindings"][0]["count"]["value"])
            if doc_files_data["results"]["bindings"]
            else 0
        )
        asset_files_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?count)
        WHERE {
            ?file a ?fileType .
            ?fileType rdfs:subClassOf* wdo:AssetFile .
        }
        """
        asset_files_data = run_dashboard_sparql(asset_files_query)
        total_asset_files = (
            int(asset_files_data["results"]["bindings"][0]["count"]["value"])
            if asset_files_data["results"]["bindings"]
            else 0
        )
        return {
            "totalRepositories": total_repos,
            "totalFiles": total_files,
            "sourceCodeFiles": total_source_files,
            "documentationFiles": total_doc_files,
            "assetFiles": total_asset_files,
        }
    except Exception as e:
        logger.warning(f"Codebase metrics query failed: {e}")
        return {}


def _get_entity_distribution() -> dict:
    """Run SPARQL queries to get entity distribution for analytics.

    Returns:
        dict: A dictionary containing entity distribution metrics for analytics.
    """
    try:
        functions_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?func) AS ?count)
        WHERE {
            ?func a ?funcType .
            ?funcType rdfs:subClassOf* wdo:FunctionDefinition .
        }
        """
        functions_data = run_dashboard_sparql(functions_query)
        total_functions = (
            int(functions_data["results"]["bindings"][0]["count"]["value"])
            if functions_data["results"]["bindings"]
            else 0
        )
        classes_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?class) AS ?count)
        WHERE {
            ?class a ?classType .
            ?classType rdfs:subClassOf* wdo:ClassDefinition .
        }
        """
        classes_data = run_dashboard_sparql(classes_query)
        total_classes = (
            int(classes_data["results"]["bindings"][0]["count"]["value"])
            if classes_data["results"]["bindings"]
            else 0
        )
        interfaces_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?interface) AS ?count)
        WHERE {
            ?interface a ?interfaceType .
            ?interfaceType rdfs:subClassOf* wdo:InterfaceDefinition .
        }
        """
        interfaces_data = run_dashboard_sparql(interfaces_query)
        total_interfaces = (
            int(interfaces_data["results"]["bindings"][0]["count"]["value"])
            if interfaces_data["results"]["bindings"]
            else 0
        )
        attributes_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?attr) AS ?count)
        WHERE {
            ?attr a ?attrType .
            ?attrType rdfs:subClassOf* wdo:AttributeDeclaration .
        }
        """
        attributes_data = run_dashboard_sparql(attributes_query)
        total_attributes = (
            int(attributes_data["results"]["bindings"][0]["count"]["value"])
            if attributes_data["results"]["bindings"]
            else 0
        )
        variables_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?var) AS ?count)
        WHERE {
            ?var a ?varType .
            ?varType rdfs:subClassOf* wdo:VariableDeclaration .
        }
        """
        variables_data = run_dashboard_sparql(variables_query)
        total_variables = (
            int(variables_data["results"]["bindings"][0]["count"]["value"])
            if variables_data["results"]["bindings"]
            else 0
        )
        parameters_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?param) AS ?count)
        WHERE {
            ?param a ?paramType .
            ?paramType rdfs:subClassOf* wdo:Parameter .
        }
        """
        parameters_data = run_dashboard_sparql(parameters_query)
        total_parameters = (
            int(parameters_data["results"]["bindings"][0]["count"]["value"])
            if parameters_data["results"]["bindings"]
            else 0
        )
        return {
            "functions": total_functions,
            "classes": total_classes,
            "interfaces": total_interfaces,
            "attributes": total_attributes,
            "variables": total_variables,
            "parameters": total_parameters,
        }
    except Exception as e:
        logger.warning(f"Entity distribution query failed: {e}")
        return {}


@app.route("/api/analytics", methods=["GET"])
def get_analytics() -> Any:
    """
    Get analytics data for the dashboard.

    Returns:
        JSON response with analytics data including metrics, trends, and insights.
    """
    try:
        analytics_data: dict[str, Any] = {
            "codebaseMetrics": _get_codebase_metrics(),
            "entityDistribution": _get_entity_distribution(),
            "languageDistribution": [],
            "complexityMetrics": {},
            "documentationMetrics": {},
            "developmentMetrics": {},
            "assetMetrics": {},
            "trends": {},
        }
        return jsonify(analytics_data)
    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({"error": f"Failed to load analytics: {str(e)}"}), 500


@app.route("/api/entities/<entity_id>", methods=["GET"])
def get_entity_details(entity_id: str) -> Any:
    """
    Get details for a specific entity.

    Args:
        entity_id: The ID of the entity to retrieve.

    Returns:
        JSON response with entity details and relationships.
    """
    try:
        # Query for entity details
        entity_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/1994/02/skos/core#>
        SELECT ?entity ?type ?label ?editorialNote
        WHERE {{
            ?entity a ?type .
            OPTIONAL {{ ?entity rdfs:label ?label }}
            OPTIONAL {{ ?entity skos:editorialNote ?editorialNote }}
            FILTER(?entity = <{entity_id}>)
        }}
        """

        entity_data = run_dashboard_sparql(entity_query)

        if not entity_data["results"]["bindings"]:
            return jsonify({"error": "Entity not found"}), 404

        binding = entity_data["results"]["bindings"][0]

        # Query for relationships
        relationships_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?relatedEntity ?relationshipType ?relatedLabel
        WHERE {{
            {{
                <{entity_id}> ?relationshipType ?relatedEntity .
            }}
            UNION
            {{
                ?relatedEntity ?relationshipType <{entity_id}> .
            }}
            OPTIONAL {{ ?relatedEntity rdfs:label ?relatedLabel }}
        }}
        """

        relationships_data = run_dashboard_sparql(relationships_query)

        entity_details = {
            "id": entity_id,
            "type": binding.get("type", {}).get("value", ""),
            "name": binding.get("label", {}).get("value", ""),
            "editorialNote": binding.get("editorialNote", {}).get("value", ""),
            "description": binding.get("editorialNote", {}).get(
                "value", ""
            ),  # Use editorial note as description
            "file": binding.get("file", {}).get("value", ""),
            "line": binding.get("line", {}).get("value", ""),
            "repository": binding.get("repository", {}).get("value", ""),
            "relationships": [],
        }

        for rel_binding in relationships_data["results"]["bindings"]:
            relationship = {
                "entity": rel_binding["relatedEntity"]["value"],
                "type": rel_binding["relationshipType"]["value"],
                "name": rel_binding.get("relatedLabel", {}).get("value", ""),
            }
            entity_details["relationships"].append(relationship)

        return jsonify(entity_details)

    except Exception as e:
        logger.error(f"Entity details error: {str(e)}")
        return jsonify({"error": f"Failed to get entity details: {str(e)}"}), 500


@app.route("/api/relationships", methods=["GET"])
def get_relationships() -> Any:
    """
    Get relationships for a given entity.

    Returns:
        JSON response with relationship information.
    """
    try:
        # Query for relationship types and counts
        relationships_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT ?relationshipType (COUNT(*) AS ?count)
        WHERE {
            ?s ?relationshipType ?o .
            FILTER(?relationshipType IN (
                wdo:invokes,
                wdo:callsFunction,
                wdo:extendsType,
                wdo:implementsInterface,
                wdo:declaresCode,
                wdo:hasField,
                wdo:hasMethod,
                wdo:isRelatedTo,
                wdo:usesFramework,
                wdo:tests,
                wdo:documentsEntity,
                wdo:modifies,
                wdo:imports,
                wdo:isImportedBy
            ))
        }
        GROUP BY ?relationshipType
        ORDER BY DESC(?count)
        """

        relationships_data = run_dashboard_sparql(relationships_query)

        relationships = []
        for binding in relationships_data["results"]["bindings"]:
            rel_type = binding["relationshipType"]["value"]
            count = int(binding["count"]["value"])

            # Extract readable name from URI
            rel_name = (
                rel_type.split("#")[-1] if "#" in rel_type else rel_type.split("/")[-1]
            )

            relationships.append({"type": rel_type, "name": rel_name, "count": count})

        return jsonify({
            "relationships": relationships,
            "totalRelationships": sum(r["count"] for r in relationships),
        })

    except Exception as e:
        logger.error(f"Relationships error: {str(e)}")
        return jsonify({"error": f"Failed to get relationships: {str(e)}"}), 500


@app.route("/api/metrics/code-complexity", methods=["GET"])
def get_code_complexity() -> Any:
    """
    Get code complexity metrics for a repository.

    Returns:
        JSON response with complexity analysis.
    """
    try:
        # Query for complexity-related metrics using WDO classes
        complexity_query = """
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        SELECT ?fileName ?totalComplexity ?avgComplexity ?functionCount
            ?lineCount ?tokenCount
        WHERE {
            {
                SELECT ?fileName (SUM(?complexity) AS ?totalComplexity)
                    (AVG(?complexity) AS ?avgComplexity)
                    (COUNT(?func) AS ?functionCount)
                WHERE {
                    ?func a wdo:FunctionDefinition .
                    ?func wdo:hasCyclomaticComplexity ?complexity .
                    ?func wdo:isCodePartOf ?codeContent .
                    ?file wdo:bearerOfInformation ?codeContent .
                    ?file a wdo:SourceCodeFile .
                    BIND(REPLACE(STR(?file), ".*/([^/]+)$", "$1") AS ?fileName)
                }
                GROUP BY ?fileName
            }
            {
                SELECT ?fileName (SUM(?lines) AS ?lineCount)
                WHERE {
                    ?func a wdo:FunctionDefinition .
                    ?func wdo:hasLineCount ?lines .
                    ?func wdo:isCodePartOf ?codeContent .
                    ?file wdo:bearerOfInformation ?codeContent .
                    ?file a wdo:SourceCodeFile .
                    BIND(REPLACE(STR(?file), ".*/([^/]+)$", "$1") AS ?fileName)
                }
                GROUP BY ?fileName
            }
            {
                SELECT ?fileName (SUM(?tokens) AS ?tokenCount)
                WHERE {
                    ?func a wdo:FunctionDefinition .
                    ?func wdo:hasTokenCount ?tokens .
                    ?func wdo:isCodePartOf ?codeContent .
                    ?file wdo:bearerOfInformation ?codeContent .
                    ?file a wdo:SourceCodeFile .
                    BIND(REPLACE(STR(?file), ".*/([^/]+)$", "$1") AS ?fileName)
                }
                GROUP BY ?fileName
            }
        }
        ORDER BY DESC(?totalComplexity)
        LIMIT 50
        """

        complexity_data = run_dashboard_sparql(complexity_query)

        files = []
        total_complexity: float = 0.0
        file_count = 0

        for binding in complexity_data["results"]["bindings"]:
            file_name = binding.get("fileName", {}).get("value", "Unknown")
            total_complexity_val = float(
                binding.get("totalComplexity", {}).get("value", 0)
            )
            avg_complexity_val = float(binding.get("avgComplexity", {}).get("value", 0))
            function_count = int(binding.get("functionCount", {}).get("value", 0))
            line_count = int(binding.get("lineCount", {}).get("value", 0))
            token_count = int(binding.get("tokenCount", {}).get("value", 0))

            files.append({
                "file": file_name,
                "complexity": total_complexity_val,
                "avgComplexity": avg_complexity_val,
                "lines": line_count,
                "functions": function_count,
                "tokens": token_count,
            })

            total_complexity += total_complexity_val
            file_count += 1

        # Get additional complexity metrics
        try:
            # Average complexity across all functions
            overall_avg_query = """
            SELECT (AVG(?complexity) AS ?avgComplexity)
                (COUNT(?func) AS ?totalFunctions)
            WHERE {
                ?func a wdo:FunctionDefinition .
                ?func wdo:hasCyclomaticComplexity ?complexity .
            }
            """
            overall_data = run_dashboard_sparql(overall_avg_query)
            overall_avg = 0.0
            total_functions = 0
            if overall_data["results"]["bindings"]:
                avg_val = overall_data["results"]["bindings"][0]["avgComplexity"][
                    "value"
                ]
                if avg_val != "NaN":
                    overall_avg = round(float(avg_val), 2)
                total_functions = int(
                    overall_data["results"]["bindings"][0]["totalFunctions"]["value"]
                )

            # Complexity distribution
            complexity_distribution_query = """
            PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
            SELECT ?complexityRange (COUNT(?func) AS ?count)
            WHERE {
                ?func a wdo:FunctionDefinition .
                ?func wdo:hasCyclomaticComplexity ?complexity .
                BIND(
                    CASE
                        WHEN (?complexity <= 5) THEN "Low (1-5)"
                        WHEN (?complexity <= 10) THEN "Medium (6-10)"
                        WHEN (?complexity <= 20) THEN "High (11-20)"
                        ELSE "Very High (>20)"
                    END AS ?complexityRange
                )
            }
            GROUP BY ?complexityRange
            ORDER BY ?complexityRange
            """
            distribution_data = run_dashboard_sparql(complexity_distribution_query)
            complexity_distribution = []
            for binding in distribution_data["results"]["bindings"]:
                complexity_distribution.append({
                    "range": binding["complexityRange"]["value"],
                    "count": int(binding["count"]["value"]),
                })

        except Exception as e:
            logger.warning(f"Additional complexity metrics failed: {e}")
            overall_avg = 0.0
            total_functions = 0
            complexity_distribution = []

        avg_complexity = total_complexity / file_count if file_count > 0 else 0
        high_complexity_files = len([f for f in files if f["complexity"] > 10])

        return jsonify({
            "averageComplexity": round(avg_complexity, 2),
            "overallAverageComplexity": overall_avg,
            "highComplexityFiles": high_complexity_files,
            "totalFiles": file_count,
            "totalFunctions": total_functions,
            "complexityDistribution": complexity_distribution,
            "files": files[:20],  # Return top 20 most complex files
        })

    except Exception as e:
        logger.error(f"Code complexity error: {str(e)}")
        return jsonify({"error": f"Failed to get complexity metrics: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health_check() -> Any:
    """
    Health check endpoint for the API.

    Returns:
        JSON response with system health status.
    """
    try:
        # Test SPARQL endpoint with a simple query
        test_query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o } LIMIT 1"
        sparql_healthy = False
        sparql_response_time = 0

        try:
            import time

            start_time = time.time()
            run_dashboard_sparql(test_query)
            sparql_response_time = int((time.time() - start_time) * 1000)
            sparql_healthy = True
        except Exception as e:
            logger.warning(f"SPARQL health check failed: {e}")
            sparql_healthy = False

        # Check file system

        from pathlib import Path

        output_dir = Path("output")
        filesystem_healthy = pathlib.Path(output_dir).exists()

        # Get system info
        import psutil

        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage("/").percent

        health_status = {
            "status": (
                "healthy" if sparql_healthy and filesystem_healthy else "degraded"
            ),
            "timestamp": datetime.now().isoformat(),
            "services": {
                "sparql_endpoint": sparql_healthy,
                "filesystem": filesystem_healthy,
                "api_server": True,
            },
            "performance": {
                "sparql_response_time_ms": round(sparql_response_time * 1000, 2),
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
            },
            "version": "1.0.0",
        }

        status_code = 200 if health_status["status"] == "healthy" else 503
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return (
            jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }),
            503,
        )


@app.route("/api/export/<export_format>", methods=["GET"])
def export_data(export_format: str) -> Any:
    """
    Export data from the triplestore.

    Args:
        export_format: Export format (json, ttl, rdf, csv)

    Returns:
        Exported data in the requested format.
    """
    try:
        if export_format not in ["json", "ttl", "rdf", "csv"]:
            return jsonify({"error": "Unsupported format"}), 400

        # Query all triples
        export_query = """
        CONSTRUCT { ?s ?p ?o }
        WHERE { ?s ?p ?o }
        """

        if export_format == "json":
            # Convert to JSON-LD format
            data = run_dashboard_sparql(export_query)
            return jsonify(data)

        elif export_format == "ttl":
            # Return Turtle format
            from rdflib import Graph

            g = Graph()

            # Load from TTL file if exists
            ttl_path = PathManager.get_output_path("wdkb.ttl")
            if pathlib.Path(ttl_path).exists():
                g.parse(ttl_path, format="turtle")
                return (
                    g.serialize(format="turtle"),
                    200,
                    {"Content-Type": "text/turtle"},
                )
            else:
                return jsonify({"error": "No TTL file found"}), 404

        elif export_format == "rdf":
            # Return RDF/XML format
            from rdflib import Graph

            g = Graph()

            ttl_path = PathManager.get_output_path("wdkb.ttl")
            if pathlib.Path(ttl_path).exists():
                g.parse(ttl_path, format="turtle")
                return (
                    g.serialize(format="xml"),
                    200,
                    {"Content-Type": "application/rdf+xml"},
                )
            else:
                return jsonify({"error": "No TTL file found"}), 404

        elif export_format == "csv":
            # Export as CSV (simplified)
            csv_data = "Subject,Predicate,Object\n"

            # Get triples as CSV
            triples_query = """
            SELECT ?s ?p ?o
            WHERE { ?s ?p ?o }
            LIMIT 1000
            """

            triples_data = run_dashboard_sparql(triples_query)
            for binding in triples_data["results"]["bindings"]:
                s = binding["s"]["value"]
                p = binding["p"]["value"]
                o = binding["o"]["value"]
                csv_data += f'"{s}","{p}","{o}"\n'

            return csv_data, 200, {"Content-Type": "text/csv"}

    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({"error": f"Failed to export data: {str(e)}"}), 500


@app.route("/api/config", methods=["GET"])
def get_config() -> Any:
    """
    Get configuration settings for the API.

    Returns:
        JSON response with configuration details.
    """
    try:
        config = {
            "backend": {
                "version": "1.0.0",
                "environment": os.environ.get("FLASK_ENV", "development"),
                "debug": app.debug,
            },
            "database": {
                "type": "AllegroGraph",
                "url": app.config["AGRAPH_URL"],
                "repository": app.config["AGRAPH_REPO"],
                "connected": bool(
                    app.config["AGRAPH_URL"] and app.config["AGRAPH_REPO"]
                ),
            },
            "features": {
                "sparql_endpoint": True,
                "progress_tracking": True,
                "file_upload": True,
                "analytics": True,
                "export": True,
            },
            "paths": {
                "input_directory": os.environ.get(
                    "DEFAULT_INPUT_DIR", "~/downloads/repos/Thinkster/"
                ),
                "output_directory": "output",
                "logs_directory": "logs",
            },
        }

        return jsonify(config)

    except Exception as e:
        logger.error(f"Config error: {str(e)}")
        return jsonify({"error": f"Failed to get config: {str(e)}"}), 500


@app.route("/api/dashboard_stats", methods=["GET"])
def dashboard_stats_route():
    """Return dashboard statistics for the dashboard_stats endpoint."""
    return dashboard_stats()


def run_dashboard_sparql(query: str) -> dict:
    """
    Execute a SPARQL query against AllegroGraph and return the parsed JSON result.

    Args:
        query (str): The SPARQL query string to execute.

    Returns:
        dict: The parsed JSON result from AllegroGraph.

    Raises:
        Exception: If the query fails or the response is invalid.
    """
    return _post_to_agraph(query, return_json=True)


def detect_organization_directory(temp_dir: str) -> str:
    """
    Detect and return the organization directory within a temporary upload directory.

    This addresses the issue of random root directory names generated by the frontend.

    Args:
        temp_dir (str): The path to the temporary upload directory.

    Returns:
        str: Path to the detected organization directory or temp_dir if not found.
            or temp_dir if no subdirectory is found.
    """
    for entry in os.scandir(temp_dir):
        if entry.is_dir() and not entry.name.startswith("."):
            return entry.path
    return temp_dir


if __name__ == "__main__":
    # Read host, port, and debug mode from environment variables, with sensible defaults
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", 8000))
    debug = os.environ.get("API_DEBUG", "true").lower() == "true"

    app.run(host=host, port=port, debug=debug)
