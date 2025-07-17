"""Flask API server for Semantic Web KMS."""

import logging
import os
import re
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Union, cast

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; skip loading .env

import requests
from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS

from app.core.paths import get_output_path

# Import progress tracking
from app.core.progress_tracker import create_tracker, get_tracker_by_id

# Setup logging
logger = logging.getLogger(__name__)

# Configurations for AllegroGraph
AGRAPH_URL = os.environ.get("AGRAPH_CLOUD_URL") or os.environ.get("AGRAPH_SERVER_URL")
AGRAPH_REPO = os.environ.get("AGRAPH_REPO")
AGRAPH_USER = os.environ.get("AGRAPH_USERNAME")
AGRAPH_PASS = os.environ.get("AGRAPH_PASSWORD")

app = Flask(__name__)

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
    """Get or create a global session for AllegroGraph connections."""
    global _agraph_session
    if _agraph_session is None:
        _agraph_session = requests.Session()
        if AGRAPH_USER and AGRAPH_PASS:
            _agraph_session.auth = (AGRAPH_USER, AGRAPH_PASS)
    return _agraph_session


# Memory-efficient dashboard stats queries based on WDO ontology
DASHBOARD_QUERIES = {
    "repositories": "SELECT (COUNT(DISTINCT ?repo) AS ?count) WHERE { ?repo a <http://web-development-ontology.netlify.app/wdo#Repository> . }",
    "files": "SELECT (COUNT(DISTINCT ?file) AS ?count) WHERE { ?file a ?fileType . ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#DigitalInformationCarrier> . }",
    "source_files": "SELECT (COUNT(DISTINCT ?file) AS ?count) WHERE { ?file a ?fileType . ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> . }",
    "doc_files": "SELECT (COUNT(DISTINCT ?file) AS ?count) WHERE { ?file a ?fileType . ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#DocumentationFile> . }",
    "asset_files": "SELECT (COUNT(DISTINCT ?file) AS ?count) WHERE { ?file a ?fileType . ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#AssetFile> . }",
    "all_entities": "SELECT (COUNT(DISTINCT ?entity) AS ?count) WHERE { ?entity a ?entityType . ?entityType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#InformationContentEntity> . }",
    "functions": "SELECT (COUNT(DISTINCT ?func) AS ?count) WHERE { ?func a ?funcType . ?funcType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> . }",
    "classes": "SELECT (COUNT(DISTINCT ?class) AS ?count) WHERE { ?class a ?classType . ?classType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#ClassDefinition> . }",
    "interfaces": "SELECT (COUNT(DISTINCT ?interface) AS ?count) WHERE { ?interface a ?interfaceType . ?interfaceType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#InterfaceDefinition> . }",
    "attributes": "SELECT (COUNT(DISTINCT ?attr) AS ?count) WHERE { ?attr a ?attrType . ?attrType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#AttributeDeclaration> . }",
    "variables": "SELECT (COUNT(DISTINCT ?var) AS ?count) WHERE { ?var a ?varType . ?varType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#VariableDeclaration> . }",
    "parameters": "SELECT (COUNT(DISTINCT ?param) AS ?count) WHERE { ?param a ?paramType . ?paramType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Parameter> . }",
    "relationships": "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . ?p a <http://www.w3.org/2002/07/owl#ObjectProperty> . }",
    "imports": "SELECT (COUNT(*) AS ?count) WHERE { ?s <http://web-development-ontology.netlify.app/wdo#imports> ?o . }",
    "complexity": "SELECT (AVG(?complexity) AS ?avg) (SUM(?complexity) AS ?sum) WHERE { ?func a ?funcType . ?funcType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> . ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity . }",
    "language_distribution": "SELECT ?extension (COUNT(DISTINCT ?file) AS ?files) WHERE { ?file a ?fileType . ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> . ?file <http://web-development-ontology.netlify.app/wdo#hasExtension> ?extension . } GROUP BY ?extension ORDER BY DESC(?files)",
    "documentation": "SELECT (COUNT(DISTINCT ?doc) AS ?count) WHERE { ?doc a ?docType . ?docType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Documentation> . }",
    "commits": "SELECT (COUNT(DISTINCT ?commit) AS ?count) WHERE { ?commit a ?commitType . ?commitType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Commit> . }",
    "issues": "SELECT (COUNT(DISTINCT ?issue) AS ?count) WHERE { ?issue a ?issueType . ?issueType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Issue> . }",
    "contributors": "SELECT (COUNT(DISTINCT ?person) AS ?count) WHERE { ?person a ?personType . ?personType rdfs:subClassOf* <http://xmlns.com/foaf/0.1/Person> . }",
}


def detect_organization_directory(temp_dir: str) -> str:
    """
    Detect the root directory for an organization upload.

    Args:
        temp_dir: Path to the temporary upload directory.

    Returns:
        Path to the organization directory to use for the pipeline.
    """
    # Get all subdirectories at the top level of the temp directory
    try:
        subdirs = [
            d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))
        ]

        # If there's exactly one subdirectory and it contains files/subdirectories,
        # treat it as the organization directory
        if len(subdirs) == 1:
            org_dir = os.path.join(temp_dir, subdirs[0])
            # Check if the org directory contains files or subdirectories
            org_contents = os.listdir(org_dir)
            if org_contents:  # Not empty
                logger.info(f"Detected organization directory: {org_dir}")
                return org_dir
    except Exception as e:
        logger.warning(f"Error detecting organization directory: {e}")

    # Fallback to temp directory if no clear organization structure
    logger.info(f"Using temp directory as organization: {temp_dir}")
    return temp_dir


def run_dashboard_sparql(query: str) -> Any:
    """
    Run a SPARQL query for the dashboard.

    Args:
        query (str): The SPARQL query string to execute.

    Returns:
        dict: The JSON-decoded response from the AllegroGraph endpoint.

    Raises:
        requests.HTTPError: If the HTTP request to the endpoint fails.
        Exception: For other unexpected errors during the request.

    Side Effects:
        Sends a POST request to the AllegroGraph server.
    """
    # Handle both cloud and server URL formats
    if AGRAPH_URL and "/repositories/" in AGRAPH_URL:
        # Cloud URL already includes repository path
        agraph_endpoint = AGRAPH_URL
    else:
        # Server URL needs repository appended
        agraph_endpoint = f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"

    headers = {"Accept": "application/sparql-results+json"}

    # Use global session for connection pooling
    session = get_agraph_session()

    # Debug logging
    logger.debug(f"SPARQL endpoint: {agraph_endpoint}")
    logger.debug(f"SPARQL query: {query[:200]}...")  # Log first 200 chars

    resp = session.post(
        agraph_endpoint,
        data={"query": query},
        headers=headers,
        timeout=30,  # Increased timeout for complex queries
    )

    # Debug logging
    logger.debug(f"SPARQL response status: {resp.status_code}")
    if resp.status_code != 200:
        logger.error(f"SPARQL response text: {resp.text}")

    resp.raise_for_status()
    return resp.json()


@cache.cached(timeout=60)  # Cache for 1 minute instead of 5 minutes
def dashboard_stats() -> Any:
    """
    Return dashboard statistics by running separate memory-efficient SPARQL queries.

    Query parameters:
    - organization: Optional organization ID to filter statistics

    Returns:
        flask.Response: A JSON response containing dashboard statistics as key-value pairs.

    Raises:
        Exception: If a SPARQL query fails, an exception may be raised by run_dashboard_sparql.

    Side Effects:
        Caches the response for improved performance.
    """
    try:
        results: Dict[str, Union[int, float, List[Dict[str, Any]]]] = {
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

        # Run separate queries to avoid memory issues
        for query_name, query in DASHBOARD_QUERIES.items():
            try:
                data = run_dashboard_sparql(query)
                bindings = data["results"]["bindings"]

                if bindings and bindings[0]:
                    binding = bindings[0]

                    if query_name == "repositories":
                        results["totalRepos"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "files":
                        results["totalFiles"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "source_files":
                        results["sourceFiles"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "doc_files":
                        results["docFiles"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "asset_files":
                        results["assetFiles"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "all_entities":
                        results["totalAllEntities"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "functions":
                        results["totalFunctions"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "classes":
                        results["totalClasses"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "interfaces":
                        results["totalInterfaces"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "attributes":
                        results["totalAttributes"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "variables":
                        results["totalVariables"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "parameters":
                        results["totalParameters"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "relationships":
                        results["totalRelationships"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "imports":
                        results["totalImports"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "complexity":
                        avg_val = binding.get("avg", {}).get("value", "0")
                        try:
                            results["averageComplexity"] = round(float(avg_val), 2)
                        except Exception:
                            results["averageComplexity"] = 0.0
                        try:
                            results["totalComplexity"] = int(
                                binding.get("sum", {}).get("value", "0")
                            )
                        except Exception:
                            results["totalComplexity"] = 0
                    elif query_name == "documentation":
                        results["totalDocumentation"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "commits":
                        results["totalCommits"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "issues":
                        results["totalIssues"] = int(
                            binding.get("count", {}).get("value", "0")
                        )
                    elif query_name == "contributors":
                        results["totalContributors"] = int(
                            binding.get("count", {}).get("value", "0")
                        )

            except Exception as e:
                logger.warning(f"Query {query_name} failed: {e}")
                # Continue with other queries even if one fails

        # Add language distribution to results
        try:
            data = run_dashboard_sparql(DASHBOARD_QUERIES["language_distribution"])
            bindings = data["results"]["bindings"]
            total = sum(int(b["files"]["value"]) for b in bindings) or 1

            # Extension to language mapping
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

            for b in bindings:
                extension = b["extension"]["value"]
                files = int(b["files"]["value"])
                percentage = round(files / total * 100, 2)

                # Map extension to language name
                language = extension_to_language.get(extension, extension.lstrip("."))

                if "topLanguages" not in results or not isinstance(
                    results["topLanguages"], list
                ):
                    results["topLanguages"] = []
                cast(List[Dict[str, Any]], results["topLanguages"]).append(
                    {
                        "language": language,
                        "entities": files,  # Keep as 'entities' for frontend compatibility
                        "percentage": percentage,
                    }
                )
        except Exception as e:
            logger.warning(f"Language distribution query failed: {e}")

        # Transform results to match frontend expectations
        transformed_results = {
            "totalEntities": results["totalAllEntities"],
            "totalRelationships": results["totalRelationships"],
            "totalImports": results["totalImports"],
            "totalRepositories": results["totalRepos"],
            "totalFiles": results["totalFiles"],
            "totalLines": 0,  # Not calculated in current queries
            "averageComplexity": results["averageComplexity"],
            "recentActivity": {
                "lastUpdated": datetime.now().isoformat(),
                "newEntities": 0,  # Not tracked in current implementation
                "newRelationships": 0,  # Not tracked in current implementation
            },
            "topLanguages": results["topLanguages"],
            "processingStatus": {
                "status": "completed",
                "lastProcessed": datetime.now().isoformat(),
                "nextScheduled": datetime.now().isoformat(),
            },
        }

        return jsonify(transformed_results)

    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        # Return default values on error
        return jsonify(
            {
                "totalRepos": 0,
                "totalFiles": 0,
                "sourceFiles": 0,
                "docFiles": 0,
                "assetFiles": 0,
                "totalFunctions": 0,
                "totalClasses": 0,
                "totalInterfaces": 0,
                "totalAttributes": 0,
                "totalVariables": 0,
                "totalParameters": 0,
                "totalRelationships": 0,
                "averageComplexity": 0.0,
                "totalComplexity": 0,
                "totalDocumentation": 0,
                "totalCommits": 0,
                "totalIssues": 0,
                "totalContributors": 0,
                "topLanguages": [],
            }
        )


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

        # Determine organization directory (from request or default)
        org_dir = data.get("org_dir") or os.environ.get(
            "DEFAULT_INPUT_DIR", "~/downloads/repos/Thinkster/"
        )

        # Start the analysis in a background thread
        import threading

        def run_analysis(org_dir: str):
            try:
                logger.info(f"[Job {job_id}] Starting triplestore clear...")
                # Clear the triplestore before loading new data
                try:
                    clear_query = """
                    DELETE { ?s ?p ?o }
                    WHERE  { ?s ?p ?o }
                    """
                    if AGRAPH_URL and "/repositories/" in AGRAPH_URL:
                        agraph_endpoint = AGRAPH_URL
                    else:
                        agraph_endpoint = f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"
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

                # Set the input directory for the pipeline
                from app.core.paths import set_input_dir

                set_input_dir(org_dir)

                # Import and run the knowledge pipeline
                from app.knowledge_pipeline import main as run_pipeline

                run_pipeline()
            except Exception as e:
                logger.error(f"[Job {job_id}] Error in run_analysis: {e}")
                tracker.end_job(success=False, error=str(e))
                logger.info(f"[Job {job_id}] Marked as error.")
            else:
                tracker.end_job(success=True)
                logger.info(f"[Job {job_id}] Marked as completed.")
            # No temp_dir cleanup needed here

        thread = threading.Thread(target=run_analysis, args=(org_dir,))
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "organization": organization_name,
                "status": "started",
                "message": "Analysis started successfully",
            }
        )

    except Exception as e:
        return jsonify({"error": f"Failed to start analysis: {str(e)}"}), 500


@app.route("/api/upload/organization", methods=["POST"])
def upload_organization() -> Any:
    """
    Upload an organization directory for analysis.

    Returns:
        JSON response with job ID and initial status.
    """
    try:
        # Check if files were uploaded
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded"}), 400

        files = request.files.getlist("files")
        if not files or all(file.filename == "" for file in files):
            return jsonify({"error": "No files selected"}), 400

        # Create a temporary directory to store uploaded files
        temp_dir = tempfile.mkdtemp(prefix="org_upload_")

        try:
            # Save uploaded files to temporary directory
            for file in files:
                if file.filename:
                    # Create directory structure if needed
                    file_path = os.path.join(temp_dir, file.filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)

            # Detect the real organization directory from uploaded files
            org_dir = detect_organization_directory(temp_dir)

            # Create a job ID based on timestamp
            import time

            job_id = f"upload_{int(time.time())}"

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
                        if AGRAPH_URL and "/repositories/" in AGRAPH_URL:
                            agraph_endpoint = AGRAPH_URL
                        else:
                            agraph_endpoint = f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"
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

                    # Set the input directory for the pipeline
                    from app.core.paths import set_input_dir

                    set_input_dir(org_dir)

                    # Import and run the knowledge pipeline
                    from app.knowledge_pipeline import main as run_pipeline

                    run_pipeline()
                except Exception as e:
                    logger.error(f"[Job {job_id}] Error in run_analysis: {e}")
                    tracker.end_job(success=False, error=str(e))
                    logger.info(f"[Job {job_id}] Marked as error.")
                else:
                    tracker.end_job(success=True)
                    logger.info(f"[Job {job_id}] Marked as completed.")
                finally:
                    # Clean up temporary directory
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed to clean up temporary directory {temp_dir}: {cleanup_error}"
                        )

            thread = threading.Thread(target=run_analysis)
            thread.daemon = True
            thread.start()

            return jsonify(
                {
                    "job_id": job_id,
                    "status": "started",
                    "message": "File upload and analysis started successfully",
                    "files_uploaded": len([f for f in files if f.filename]),
                }
            )

        except Exception as e:
            # Clean up on error
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up temporary directory {temp_dir}: {cleanup_error}"
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
        SELECT ?org ?name ?repo ?repoName WHERE {
            ?org a <http://web-development-ontology.netlify.app/wdo#Organization> .
            OPTIONAL { ?org <http://www.w3.org/2000/01/rdf-schema#label> ?name . }
            ?org <http://web-development-ontology.netlify.app/wdo#hasRepository> ?repo .
            ?repo a <http://web-development-ontology.netlify.app/wdo#Repository> .
            OPTIONAL { ?repo <http://www.w3.org/2000/01/rdf-schema#label> ?repoName . }
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
    Validate that the input string is a well-formed HTTP(S) URI for use in SPARQL queries.

    This function is used to prevent SPARQL injection by ensuring that only valid, safe URIs
    are interpolated into SPARQL queries. It uses a regex to check for a well-formed
    HTTP or HTTPS URI, and also rejects URIs containing characters that could break out of
    the URI context in SPARQL (e.g., >, ", ', {, }, ;).
    For stricter security, consider additional checks (e.g., whitelisting domains).

    Args:
        uri (str): The URI to validate.

    Returns:
        bool: True if the URI is a valid HTTP(S) URI and does not contain dangerous characters, False otherwise.
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
        """
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

        # Scoped file count query for this organization (count DigitalInformationCarrier)
        stats_query = f"""
        PREFIX wdo: <http://web-development-ontology.netlify.app/wdo#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT (COUNT(DISTINCT ?file) AS ?totalFiles)
        WHERE {{
            ?org wdo:hasRepository ?repo .
            ?repo wdo:hasFile ?file .
            ?file a/rdfs:subClassOf* wdo:DigitalInformationCarrier .
            VALUES ?org {{ <{org_id}> }}
        }}
        """
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

        return jsonify(
            {
                "id": org_id,
                "name": org_name,
                "totalFiles": total_files,
                "totalRelations": total_relationships,
                "repositories": repositories,
            }
        )
    except Exception as e:
        logger.error(f"Error in get_organization: {str(e)}")
        return jsonify({"error": f"Failed to get organization: {str(e)}"}), 500


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
        organization = request.args.get("organization")

        # 1. Get all repositories with basic info
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
            repos.append(
                {
                    "id": repo_id,
                    "name": name,
                    "lastUpdated": last_updated,
                }
            )

        # 2-5. For each repo, get language, avg complexity, contributors, and entity count
        for repo in repos:
            repo_uri = repo["id"]
            if not is_valid_uri(repo_uri):
                logger.error(f"Invalid repository URI: {repo_uri}")
                return jsonify({"error": f"Invalid repository URI: {repo_uri}"}), 400

            # Validate repo_uri as a URI to prevent injection
            if not is_valid_uri(repo_uri):
                # Optionally, log or collect invalid repos
                continue

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
              # -- Define the Repository you are querying --
              # Replace the URI with the specific repository you want to analyze.
              BIND(<{repo_uri}> AS ?repo)

              # The UNION block finds all entities through the different valid paths.
              # This logic is identical to your original query.
              {{
                # -- Path 1: From File Contents (Direct and Nested) --
                ?repo wdo:hasFile/wdo:bearerOfInformation ?fileContent .
                ?fileContent (wdo:hasCodePart | wdo:hasMethod | wdo:hasDocumentComponent)* ?entity .
              }}
              UNION
              {{
                # -- Path 2: From the Commit History --
                ?repo wdo:hasCommit ?commit .
                {{
                  ?commit wdo:hasCommitMessage ?entity .
                }}
                UNION
                {{
                  ?commit (wdo:addressesIssue|wdo:fixesIssue) ?entity .
                }}
              }}

              # -- We still need the filters to ensure we are counting the right things --
              ?entity a ?entityTypeRaw .

              # Ensure the entity is a WDO class and not a generic BFO class.
              FILTER CONTAINS(STR(?entityTypeRaw), "web-development-ontology.netlify.app")
              # Ensure the entity itself is a named individual, not a blank node.
              FILTER(isIRI(?entity))
            }}
            """  # nosec B608
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
            repo["entities"] = entity_count

        return jsonify(repos)
    except Exception as e:
        logger.error(f"Error in list_repositories: {str(e)}")
        return jsonify([])


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
        SELECT DISTINCT ?entity ?name ?entityType ?editorialNote ?file ?line ?repo ?confidence
        WHERE {
            ?entity a ?entityType .
            OPTIONAL { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?name . }
            OPTIONAL { ?entity <http://www.w3.org/1994/02/skos/core#editorialNote> ?editorialNote . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#hasSourceFile> ?file . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#hasLineNumber> ?line . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#belongsToRepository> ?repo . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#hasConfidence> ?confidence . }
        """

        # Add filters
        if entity_type:
            sparql_query += f"    FILTER(?entityType = <http://web-development-ontology.netlify.app/wdo#{entity_type}>) .\n"

        if repository:
            sparql_query += f"    FILTER(?repo = <{repository}>) .\n"

        # Add search filter
        sparql_query += f"""
            FILTER(
                REGEX(?name, "{query}", "i") ||
                REGEX(?editorialNote, "{query}", "i")
            ) .
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

            entities.append(
                {
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
                }
            )

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

        return jsonify(
            {
                "entities": entities,
                "totalCount": len(entities),
                "semanticInsights": semantic_insights,
            }
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/api/sparql", methods=["POST"])
def sparql_query():
    """
    Execute a SPARQL query against the triplestore.

    Returns:
        flask.Response: A JSON response containing the SPARQL query results or an error message.

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

    # Handle both cloud and server URL formats
    if AGRAPH_URL and "/repositories/" in AGRAPH_URL:
        # Cloud URL already includes repository path
        agraph_endpoint = AGRAPH_URL
    else:
        # Server URL needs repository appended
        agraph_endpoint = f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"

    headers = {"Accept": "application/sparql-results+json"}
    auth = (AGRAPH_USER, AGRAPH_PASS) if AGRAPH_USER and AGRAPH_PASS else None
    resp = requests.post(
        agraph_endpoint, data={"query": query}, headers=headers, auth=auth, timeout=30
    )
    if resp.status_code == 200:
        return jsonify(resp.json())
    else:
        return jsonify({"error": resp.text}), resp.status_code


@app.route("/api/input-directory", methods=["GET"])
def get_input_directory() -> Any:
    """
    Get the input directory for uploads.

    Returns:
        JSON response with the current input directory path.
    """
    try:
        from app.core.paths import get_input_dir

        input_dir = get_input_dir()
        return jsonify(
            {
                "input_directory": input_dir,
                "exists": os.path.exists(input_dir),
                "is_directory": (
                    os.path.isdir(input_dir) if os.path.exists(input_dir) else False
                ),
            }
        )
    except RuntimeError:
        # Input directory not set
        return jsonify(
            {
                "input_directory": None,
                "exists": False,
                "is_directory": False,
                "message": "No input directory currently set",
            }
        )
    except Exception as e:
        return jsonify({"error": f"Failed to get input directory: {str(e)}"}), 500


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
        layout = request.args.get("layout", "force-directed")
        filter_type = request.args.get("filter", "all")
        max_nodes = int(request.args.get("maxNodes", 100))

        # Build SPARQL query to get graph data
        sparql_query = """
        SELECT DISTINCT ?entity ?name ?entityType ?repo ?language
        WHERE {
            ?entity a ?entityType .
            OPTIONAL { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?name . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#belongsToRepository> ?repo . }
            OPTIONAL { ?entity <http://web-development-ontology.netlify.app/wdo#hasProgrammingLanguage> ?language . }
        """

        # Add type filter
        if filter_type != "all":
            sparql_query += f"    FILTER(?entityType = <http://web-development-ontology.netlify.app/wdo#{filter_type}>) .\n"

        sparql_query += f"}} LIMIT {max_nodes}"

        # Execute query
        data = run_dashboard_sparql(sparql_query)
        bindings = data["results"]["bindings"]

        # Transform to nodes
        nodes = []
        node_ids = set()

        for binding in bindings:
            if "entityType" not in binding:
                continue  # Skip nodes without a type
            entity_id = binding["entity"]["value"]
            name = binding.get("name", {}).get("value", "Unknown")
            entity_type = binding["entityType"]["value"].split("#")[-1]
            repo = binding.get("repo", {}).get("value", "")
            language = binding.get("language", {}).get("value", "")

            if entity_id not in node_ids:
                node_ids.add(entity_id)

                # Determine node properties based on type
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

                nodes.append(
                    {
                        "id": entity_id,
                        "name": name,
                        "type": node_type,
                        "size": size,
                        "color": color,
                        "repository": repo.split("/")[-1] if repo else "",
                        "language": language,
                    }
                )

        # Get relationships for edges
        edges_query = """
        SELECT DISTINCT ?source ?target ?relationship
        WHERE {
            ?source ?relationship ?target .
        }
        """

        edges_data = run_dashboard_sparql(edges_query)
        edges_bindings = edges_data["results"]["bindings"]

        edges = []
        for binding in edges_bindings:
            if "relationship" not in binding:
                continue  # Skip edges without a relationship type
            source = binding["source"]["value"]
            target = binding["target"]["value"]
            relationship = binding["relationship"]["value"].split("#")[-1]

            # Only include edges between nodes we have
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

                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "type": edge_type,
                        "weight": weight,
                    }
                )

        # Generate clusters based on repositories
        clusters = []
        repo_clusters: Dict[str, Dict[str, Any]] = {}

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

        clusters = list(repo_clusters.values())

        return jsonify(
            {
                "nodes": nodes,
                "edges": edges,
                "clusters": clusters,
            }
        )

    except Exception as e:
        logger.error(f"Graph data error: {str(e)}")
        return jsonify({"error": f"Failed to load graph data: {str(e)}"}), 500


@app.route("/api/analytics", methods=["GET"])
def get_analytics() -> Any:
    """
    Get analytics data for the dashboard.

    Returns:
        JSON response with analytics data including metrics, trends, and insights.
    """
    try:
        analytics_data: Dict[str, Any] = {
            "codebaseMetrics": {},
            "entityDistribution": {},
            "languageDistribution": [],
            "complexityMetrics": {},
            "documentationMetrics": {},
            "developmentMetrics": {},
            "assetMetrics": {},
            "trends": {},
        }

        # 1. Codebase Metrics - Core Software Development Entities
        try:
            # Total repositories
            repos_query = """
            SELECT (COUNT(DISTINCT ?repo) AS ?count)
            WHERE {
                ?repo a <http://web-development-ontology.netlify.app/wdo#Repository> .
            }
            """
            repos_data = run_dashboard_sparql(repos_query)
            total_repos = (
                int(repos_data["results"]["bindings"][0]["count"]["value"])
                if repos_data["results"]["bindings"]
                else 0
            )

            # Total files (DigitalInformationCarrier)
            files_query = """
            SELECT (COUNT(DISTINCT ?file) AS ?count)
            WHERE {
                ?file a ?fileType .
                ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#DigitalInformationCarrier> .
            }
            """
            files_data = run_dashboard_sparql(files_query)
            total_files = (
                int(files_data["results"]["bindings"][0]["count"]["value"])
                if files_data["results"]["bindings"]
                else 0
            )

            # Source code files
            source_files_query = """
            SELECT (COUNT(DISTINCT ?file) AS ?count)
            WHERE {
                ?file a ?fileType .
                ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> .
            }
            """
            source_files_data = run_dashboard_sparql(source_files_query)
            total_source_files = (
                int(source_files_data["results"]["bindings"][0]["count"]["value"])
                if source_files_data["results"]["bindings"]
                else 0
            )

            # Documentation files
            doc_files_query = """
            SELECT (COUNT(DISTINCT ?file) AS ?count)
            WHERE {
                ?file a ?fileType .
                ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#DocumentationFile> .
            }
            """
            doc_files_data = run_dashboard_sparql(doc_files_query)
            total_doc_files = (
                int(doc_files_data["results"]["bindings"][0]["count"]["value"])
                if doc_files_data["results"]["bindings"]
                else 0
            )

            # Asset files
            asset_files_query = """
            SELECT (COUNT(DISTINCT ?file) AS ?count)
            WHERE {
                ?file a ?fileType .
                ?fileType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#AssetFile> .
            }
            """
            asset_files_data = run_dashboard_sparql(asset_files_query)
            total_asset_files = (
                int(asset_files_data["results"]["bindings"][0]["count"]["value"])
                if asset_files_data["results"]["bindings"]
                else 0
            )

            analytics_data["codebaseMetrics"] = {
                "totalRepositories": total_repos,
                "totalFiles": total_files,
                "sourceCodeFiles": total_source_files,
                "documentationFiles": total_doc_files,
                "assetFiles": total_asset_files,
            }

        except Exception as e:
            logger.warning(f"Codebase metrics query failed: {e}")

        # 2. Entity Distribution - WDO Class Analysis
        try:
            # Function definitions
            functions_query = """
            SELECT (COUNT(DISTINCT ?func) AS ?count)
            WHERE {
                ?func a ?funcType .
                ?funcType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
            }
            """
            functions_data = run_dashboard_sparql(functions_query)
            total_functions = (
                int(functions_data["results"]["bindings"][0]["count"]["value"])
                if functions_data["results"]["bindings"]
                else 0
            )

            # Class definitions
            classes_query = """
            SELECT (COUNT(DISTINCT ?class) AS ?count)
            WHERE {
                ?class a ?classType .
                ?classType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#ClassDefinition> .
            }
            """
            classes_data = run_dashboard_sparql(classes_query)
            total_classes = (
                int(classes_data["results"]["bindings"][0]["count"]["value"])
                if classes_data["results"]["bindings"]
                else 0
            )

            # Interface definitions
            interfaces_query = """
            SELECT (COUNT(DISTINCT ?interface) AS ?count)
            WHERE {
                ?interface a ?interfaceType .
                ?interfaceType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#InterfaceDefinition> .
            }
            """
            interfaces_data = run_dashboard_sparql(interfaces_query)
            total_interfaces = (
                int(interfaces_data["results"]["bindings"][0]["count"]["value"])
                if interfaces_data["results"]["bindings"]
                else 0
            )

            # Attribute declarations
            attributes_query = """
            SELECT (COUNT(DISTINCT ?attr) AS ?count)
            WHERE {
                ?attr a ?attrType .
                ?attrType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#AttributeDeclaration> .
            }
            """
            attributes_data = run_dashboard_sparql(attributes_query)
            total_attributes = (
                int(attributes_data["results"]["bindings"][0]["count"]["value"])
                if attributes_data["results"]["bindings"]
                else 0
            )

            # Variable declarations
            variables_query = """
            SELECT (COUNT(DISTINCT ?var) AS ?count)
            WHERE {
                ?var a ?varType .
                ?varType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#VariableDeclaration> .
            }
            """
            variables_data = run_dashboard_sparql(variables_query)
            total_variables = (
                int(variables_data["results"]["bindings"][0]["count"]["value"])
                if variables_data["results"]["bindings"]
                else 0
            )

            # Parameters
            parameters_query = """
            SELECT (COUNT(DISTINCT ?param) AS ?count)
            WHERE {
                ?param a ?paramType .
                ?paramType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Parameter> .
            }
            """
            parameters_data = run_dashboard_sparql(parameters_query)
            total_parameters = (
                int(parameters_data["results"]["bindings"][0]["count"]["value"])
                if parameters_data["results"]["bindings"]
                else 0
            )

            analytics_data["entityDistribution"] = {
                "functions": total_functions,
                "classes": total_classes,
                "interfaces": total_interfaces,
                "attributes": total_attributes,
                "variables": total_variables,
                "parameters": total_parameters,
            }

        except Exception as e:
            logger.warning(f"Entity distribution query failed: {e}")

        # 3. Language Distribution - Programming Languages
        try:
            language_query = """
            SELECT ?language (COUNT(DISTINCT ?code) AS ?count)
            WHERE {
                ?code a ?codeType .
                ?codeType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#ProgrammingLanguageCode> .
                ?code <http://web-development-ontology.netlify.app/wdo#hasProgrammingLanguage> ?language .
            }
            GROUP BY ?language
            ORDER BY DESC(?count)
            """
            language_data = run_dashboard_sparql(language_query)
            language_distribution = []
            total_language_entities = 0

            for binding in language_data["results"]["bindings"]:
                language = binding["language"]["value"]
                count = int(binding["count"]["value"])
                total_language_entities += count
                language_distribution.append(
                    {
                        "language": language,
                        "entities": count,
                        "percentage": 0,  # Will calculate below
                    }
                )

            # Calculate percentages
            if total_language_entities > 0:
                for lang in language_distribution:
                    lang["percentage"] = round(
                        (lang["entities"] / total_language_entities) * 100, 1
                    )

            analytics_data["languageDistribution"] = language_distribution

        except Exception as e:
            logger.warning(f"Language distribution query failed: {e}")

        # 4. Complexity Metrics
        try:
            # Average cyclomatic complexity
            avg_complexity_query = """
            SELECT (AVG(?complexity) AS ?avg)
            WHERE {
                ?func a ?funcType .
                ?funcType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity .
            }
            """
            avg_complexity_data = run_dashboard_sparql(avg_complexity_query)
            avg_complexity = 0.0
            if avg_complexity_data["results"]["bindings"]:
                avg_val = avg_complexity_data["results"]["bindings"][0]["avg"]["value"]
                if avg_val != "NaN":
                    avg_complexity = round(float(avg_val), 2)

            # High complexity functions (>10)
            high_complexity_query = """
            SELECT (COUNT(DISTINCT ?func) AS ?count)
            WHERE {
                ?func a ?funcType .
                ?funcType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity .
                FILTER(?complexity > 10)
            }
            """
            high_complexity_data = run_dashboard_sparql(high_complexity_query)
            high_complexity_count = (
                int(high_complexity_data["results"]["bindings"][0]["count"]["value"])
                if high_complexity_data["results"]["bindings"]
                else 0
            )

            # Total line count
            line_count_query = """
            SELECT (SUM(?lines) AS ?total)
            WHERE {
                ?code a ?codeType .
                ?codeType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#SoftwareCode> .
                ?code <http://web-development-ontology.netlify.app/wdo#hasLineCount> ?lines .
            }
            """
            line_count_data = run_dashboard_sparql(line_count_query)
            total_lines = (
                int(line_count_data["results"]["bindings"][0]["total"]["value"])
                if line_count_data["results"]["bindings"]
                else 0
            )

            analytics_data["complexityMetrics"] = {
                "averageCyclomaticComplexity": avg_complexity,
                "highComplexityFunctions": high_complexity_count,
                "totalLinesOfCode": total_lines,
            }

        except Exception as e:
            logger.warning(f"Complexity metrics query failed: {e}")

        # 5. Documentation Metrics
        try:
            # Total documentation entities
            doc_entities_query = """
            SELECT (COUNT(DISTINCT ?doc) AS ?count)
            WHERE {
                ?doc a ?docType .
                ?docType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Documentation> .
            }
            """
            doc_entities_data = run_dashboard_sparql(doc_entities_query)
            total_doc_entities = (
                int(doc_entities_data["results"]["bindings"][0]["count"]["value"])
                if doc_entities_data["results"]["bindings"]
                else 0
            )

            # README files
            readme_query = """
            SELECT (COUNT(DISTINCT ?readme) AS ?count)
            WHERE {
                ?readme a ?readmeType .
                ?readmeType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Readme> .
            }
            """
            readme_data = run_dashboard_sparql(readme_query)
            total_readmes = (
                int(readme_data["results"]["bindings"][0]["count"]["value"])
                if readme_data["results"]["bindings"]
                else 0
            )

            # Code comments
            comments_query = """
            SELECT (COUNT(DISTINCT ?comment) AS ?count)
            WHERE {
                ?comment a ?commentType .
                ?commentType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#CodeComment> .
            }
            """
            comments_data = run_dashboard_sparql(comments_query)
            total_comments = (
                int(comments_data["results"]["bindings"][0]["count"]["value"])
                if comments_data["results"]["bindings"]
                else 0
            )

            # API documentation
            api_doc_query = """
            SELECT (COUNT(DISTINCT ?api_doc) AS ?count)
            WHERE {
                ?api_doc a ?apiDocType .
                ?apiDocType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#APIDocumentation> .
            }
            """
            api_doc_data = run_dashboard_sparql(api_doc_query)
            total_api_docs = (
                int(api_doc_data["results"]["bindings"][0]["count"]["value"])
                if api_doc_data["results"]["bindings"]
                else 0
            )

            analytics_data["documentationMetrics"] = {
                "totalDocumentationEntities": total_doc_entities,
                "readmeFiles": total_readmes,
                "codeComments": total_comments,
                "apiDocumentation": total_api_docs,
            }

        except Exception as e:
            logger.warning(f"Documentation metrics query failed: {e}")

        # 6. Development Metrics
        try:
            # Total commits
            commits_query = """
            SELECT (COUNT(DISTINCT ?commit) AS ?count)
            WHERE {
                ?commit a ?commitType .
                ?commitType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Commit> .
            }
            """
            commits_data = run_dashboard_sparql(commits_query)
            total_commits = (
                int(commits_data["results"]["bindings"][0]["count"]["value"])
                if commits_data["results"]["bindings"]
                else 0
            )

            # Total issues
            issues_query = """
            SELECT (COUNT(DISTINCT ?issue) AS ?count)
            WHERE {
                ?issue a ?issueType .
                ?issueType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#Issue> .
            }
            """
            issues_data = run_dashboard_sparql(issues_query)
            total_issues = (
                int(issues_data["results"]["bindings"][0]["count"]["value"])
                if issues_data["results"]["bindings"]
                else 0
            )

            # Contributors
            contributors_query = """
            SELECT (COUNT(DISTINCT ?person) AS ?count)
            WHERE {
                ?person a ?personType .
                ?personType rdfs:subClassOf* <http://xmlns.com/foaf/0.1/Person> .
            }
            """
            contributors_data = run_dashboard_sparql(contributors_query)
            total_contributors = (
                int(contributors_data["results"]["bindings"][0]["count"]["value"])
                if contributors_data["results"]["bindings"]
                else 0
            )

            analytics_data["developmentMetrics"] = {
                "totalCommits": total_commits,
                "totalIssues": total_issues,
                "totalContributors": total_contributors,
            }

        except Exception as e:
            logger.warning(f"Development metrics query failed: {e}")

        # 7. Asset Metrics
        try:
            # Image files
            images_query = """
            SELECT (COUNT(DISTINCT ?image) AS ?count)
            WHERE {
                ?image a ?imageType .
                ?imageType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#ImageFile> .
            }
            """
            images_data = run_dashboard_sparql(images_query)
            total_images = (
                int(images_data["results"]["bindings"][0]["count"]["value"])
                if images_data["results"]["bindings"]
                else 0
            )

            # Audio files
            audio_query = """
            SELECT (COUNT(DISTINCT ?audio) AS ?count)
            WHERE {
                ?audio a ?audioType .
                ?audioType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#AudioFile> .
            }
            """
            audio_data = run_dashboard_sparql(audio_query)
            total_audio = (
                int(audio_data["results"]["bindings"][0]["count"]["value"])
                if audio_data["results"]["bindings"]
                else 0
            )

            # Video files
            video_query = """
            SELECT (COUNT(DISTINCT ?video) AS ?count)
            WHERE {
                ?video a ?videoType .
                ?videoType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#VideoFile> .
            }
            """
            video_data = run_dashboard_sparql(video_query)
            total_video = (
                int(video_data["results"]["bindings"][0]["count"]["value"])
                if video_data["results"]["bindings"]
                else 0
            )

            # Font files
            font_query = """
            SELECT (COUNT(DISTINCT ?font) AS ?count)
            WHERE {
                ?font a ?fontType .
                ?fontType rdfs:subClassOf* <http://web-development-ontology.netlify.app/wdo#FontFile> .
            }
            """
            font_data = run_dashboard_sparql(font_query)
            total_fonts = (
                int(font_data["results"]["bindings"][0]["count"]["value"])
                if font_data["results"]["bindings"]
                else 0
            )

            analytics_data["assetMetrics"] = {
                "imageFiles": total_images,
                "audioFiles": total_audio,
                "videoFiles": total_video,
                "fontFiles": total_fonts,
            }

        except Exception as e:
            logger.warning(f"Asset metrics query failed: {e}")

        # 8. Trends (placeholder for future implementation)
        from datetime import datetime

        current_time = datetime.now().isoformat()

        analytics_data["trends"] = {
            "complexity": {
                "timestamps": [current_time],
                "values": [
                    analytics_data.get("complexityMetrics", {}).get(
                        "averageCyclomaticComplexity", 0
                    )
                ],
            },
            "documentation": {
                "timestamps": [current_time],
                "values": [
                    analytics_data.get("documentationMetrics", {}).get(
                        "totalDocumentationEntities", 0
                    )
                ],
            },
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
        SELECT ?entity ?type ?label ?editorialNote
        WHERE {{
            ?entity a ?type .
            OPTIONAL {{ ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
            OPTIONAL {{ ?entity <http://www.w3.org/1994/02/skos/core#editorialNote> ?editorialNote }}
            FILTER(?entity = <{entity_id}>)
        }}
        """

        entity_data = run_dashboard_sparql(entity_query)

        if not entity_data["results"]["bindings"]:
            return jsonify({"error": "Entity not found"}), 404

        binding = entity_data["results"]["bindings"][0]

        # Query for relationships
        relationships_query = f"""
        SELECT ?relatedEntity ?relationshipType ?relatedLabel
        WHERE {{
            {{
                <{entity_id}> ?relationshipType ?relatedEntity .
            }}
            UNION
            {{
                ?relatedEntity ?relationshipType <{entity_id}> .
            }}
            OPTIONAL {{ ?relatedEntity <http://www.w3.org/2000/01/rdf-schema#label> ?relatedLabel }}
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
        SELECT ?relationshipType (COUNT(*) AS ?count)
        WHERE {
            ?s ?relationshipType ?o .
            FILTER(?relationshipType IN (
                <http://web-development-ontology.netlify.app/wdo#invokes>,
                <http://web-development-ontology.netlify.app/wdo#callsFunction>,
                <http://web-development-ontology.netlify.app/wdo#extendsType>,
                <http://web-development-ontology.netlify.app/wdo#implementsInterface>,
                <http://web-development-ontology.netlify.app/wdo#declaresCode>,
                <http://web-development-ontology.netlify.app/wdo#hasField>,
                <http://web-development-ontology.netlify.app/wdo#hasMethod>,
                <http://web-development-ontology.netlify.app/wdo#isRelatedTo>,
                <http://web-development-ontology.netlify.app/wdo#usesFramework>,
                <http://web-development-ontology.netlify.app/wdo#tests>,
                <http://web-development-ontology.netlify.app/wdo#documentsEntity>,
                <http://web-development-ontology.netlify.app/wdo#modifies>,
                <http://web-development-ontology.netlify.app/wdo#imports>,
                <http://web-development-ontology.netlify.app/wdo#isImportedBy>
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

        return jsonify(
            {
                "relationships": relationships,
                "totalRelationships": sum(r["count"] for r in relationships),
            }
        )

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
        SELECT ?fileName ?totalComplexity ?avgComplexity ?functionCount ?lineCount ?tokenCount
        WHERE {
            {
                SELECT ?fileName (SUM(?complexity) AS ?totalComplexity) (AVG(?complexity) AS ?avgComplexity) (COUNT(?func) AS ?functionCount)
                WHERE {
                    ?func a <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                    ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity .
                    ?func <http://web-development-ontology.netlify.app/wdo#isCodePartOf> ?codeContent .
                    ?file <http://web-development-ontology.netlify.app/wdo#bearerOfInformation> ?codeContent .
                    ?file a <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> .
                    BIND(REPLACE(STR(?file), ".*/([^/]+)$", "$1") AS ?fileName)
                }
                GROUP BY ?fileName
            }

            # Get line count for functions in this file
            {
                SELECT ?fileName (SUM(?lines) AS ?lineCount)
                WHERE {
                    ?func a <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                    ?func <http://web-development-ontology.netlify.app/wdo#hasLineCount> ?lines .
                    ?func <http://web-development-ontology.netlify.app/wdo#isCodePartOf> ?codeContent .
                    ?file <http://web-development-ontology.netlify.app/wdo#bearerOfInformation> ?codeContent .
                    ?file a <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> .
                    BIND(REPLACE(STR(?file), ".*/([^/]+)$", "$1") AS ?fileName)
                }
                GROUP BY ?fileName
            }

            # Get token count for functions in this file
            {
                SELECT ?fileName (SUM(?tokens) AS ?tokenCount)
                WHERE {
                    ?func a <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                    ?func <http://web-development-ontology.netlify.app/wdo#hasTokenCount> ?tokens .
                    ?func <http://web-development-ontology.netlify.app/wdo#isCodePartOf> ?codeContent .
                    ?file <http://web-development-ontology.netlify.app/wdo#bearerOfInformation> ?codeContent .
                    ?file a <http://web-development-ontology.netlify.app/wdo#SourceCodeFile> .
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

            files.append(
                {
                    "file": file_name,
                    "complexity": total_complexity_val,
                    "avgComplexity": avg_complexity_val,
                    "lines": line_count,
                    "functions": function_count,
                    "tokens": token_count,
                }
            )

            total_complexity += total_complexity_val
            file_count += 1

        # Get additional complexity metrics
        try:
            # Average complexity across all functions
            overall_avg_query = """
            SELECT (AVG(?complexity) AS ?avgComplexity) (COUNT(?func) AS ?totalFunctions)
            WHERE {
                ?func a <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity .
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
            SELECT ?complexityRange (COUNT(?func) AS ?count)
            WHERE {
                ?func a <http://web-development-ontology.netlify.app/wdo#FunctionDefinition> .
                ?func <http://web-development-ontology.netlify.app/wdo#hasCyclomaticComplexity> ?complexity .
                BIND(
                    CASE
                        WHEN ?complexity <= 5 THEN "Low (1-5)"
                        WHEN ?complexity <= 10 THEN "Medium (6-10)"
                        WHEN ?complexity <= 20 THEN "High (11-20)"
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
                complexity_distribution.append(
                    {
                        "range": binding["complexityRange"]["value"],
                        "count": int(binding["count"]["value"]),
                    }
                )

        except Exception as e:
            logger.warning(f"Additional complexity metrics failed: {e}")
            overall_avg = 0.0
            total_functions = 0
            complexity_distribution = []

        avg_complexity = total_complexity / file_count if file_count > 0 else 0
        high_complexity_files = len([f for f in files if f["complexity"] > 10])

        return jsonify(
            {
                "averageComplexity": round(avg_complexity, 2),
                "overallAverageComplexity": overall_avg,
                "highComplexityFiles": high_complexity_files,
                "totalFiles": file_count,
                "totalFunctions": total_functions,
                "complexityDistribution": complexity_distribution,
                "files": files[:20],  # Return top 20 most complex files
            }
        )

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
        import os

        output_dir = os.path.join("output")
        filesystem_healthy = os.path.exists(output_dir)

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
            jsonify(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            503,
        )


@app.route("/api/export/<format>", methods=["GET"])
def export_data(format: str) -> Any:
    """
    Export data from the triplestore.

    Args:
        format: Export format (json, ttl, rdf, csv)

    Returns:
        Exported data in the requested format.
    """
    try:
        if format not in ["json", "ttl", "rdf", "csv"]:
            return jsonify({"error": "Unsupported format"}), 400

        # Query all triples
        export_query = """
        CONSTRUCT { ?s ?p ?o }
        WHERE { ?s ?p ?o }
        """

        if format == "json":
            # Convert to JSON-LD format
            data = run_dashboard_sparql(export_query)
            return jsonify(data)

        elif format == "ttl":
            # Return Turtle format
            from rdflib import Graph

            g = Graph()

            # Load from TTL file if exists
            ttl_path = get_output_path("wdkb.ttl")
            if os.path.exists(ttl_path):
                g.parse(ttl_path, format="turtle")
                return (
                    g.serialize(format="turtle"),
                    200,
                    {"Content-Type": "text/turtle"},
                )
            else:
                return jsonify({"error": "No TTL file found"}), 404

        elif format == "rdf":
            # Return RDF/XML format
            from rdflib import Graph

            g = Graph()

            ttl_path = get_output_path("wdkb.ttl")
            if os.path.exists(ttl_path):
                g.parse(ttl_path, format="turtle")
                return (
                    g.serialize(format="xml"),
                    200,
                    {"Content-Type": "application/rdf+xml"},
                )
            else:
                return jsonify({"error": "No TTL file found"}), 404

        elif format == "csv":
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
                "url": AGRAPH_URL,
                "repository": AGRAPH_REPO,
                "connected": bool(AGRAPH_URL and AGRAPH_REPO),
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
    return dashboard_stats()


if __name__ == "__main__":
    # Read host, port, and debug mode from environment variables, with sensible defaults
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", 8000))
    debug = os.environ.get("API_DEBUG", "true").lower() == "true"

    app.run(host=host, port=port, debug=debug)
