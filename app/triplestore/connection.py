import logging
import requests
from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from rdflib.plugins.stores.memory import Memory

logger = logging.getLogger(__name__)

def setup_remote_store(triplestore_url, dataset_name, triplestore_type):
    """Setup connection to remote triplestore (Fuseki or GraphDB). Returns a Graph object."""
    try:
        if triplestore_type == "graphdb":
            # GraphDB endpoints
            query_url = f"{triplestore_url}/repositories/{dataset_name}"
            update_url = f"{triplestore_url}/repositories/{dataset_name}/statements"
            ensure_graphdb_repository(triplestore_url, dataset_name)
        else:
            # Default: Fuseki endpoints
            update_url = f"{triplestore_url}/{dataset_name}/update"
            query_url = f"{triplestore_url}/{dataset_name}/query"
            ensure_fuseki_dataset(triplestore_url, dataset_name)
        store = SPARQLUpdateStore(query_endpoint=query_url, update_endpoint=update_url)
        graph = Graph(store=store)
        # Test connection
        graph.query("ASK { ?s ?p ?o }")
        logger.info(f"Connected to triplestore at {triplestore_url} ({triplestore_type})")
        return graph
    except Exception as e:
        logger.warning(f"Failed to connect to remote triplestore: {e}")
        logger.info("Falling back to in-memory store")
        return Graph(store=Memory())

def ensure_fuseki_dataset(triplestore_url, dataset_name):
    """Ensure the Fuseki dataset exists, create it if it doesn't."""
    try:
        test_url = f"{triplestore_url}/{dataset_name}/query"
        response = requests.get(test_url, params={'query': 'ASK { ?s ?p ?o }'})
        if response.status_code == 404:
            logger.info(f"Dataset '{dataset_name}' does not exist. Creating it...")
            create_fuseki_dataset(triplestore_url, dataset_name)
        elif response.status_code == 200:
            logger.info(f"Dataset '{dataset_name}' already exists.")
        else:
            logger.warning(f"Could not check dataset: {response.status_code}")
            create_fuseki_dataset(triplestore_url, dataset_name)
    except Exception as e:
        logger.warning(f"Error checking/creating dataset: {e}")

def create_fuseki_dataset(triplestore_url, dataset_name):
    """Create a new Fuseki dataset."""
    try:
        admin_url = f"{triplestore_url}/$/datasets"
        dataset_config = {"dbName": dataset_name, "dbType": "tdb2"}
        response = requests.post(admin_url, json=dataset_config)
        if response.status_code == 200:
            logger.info(f"Successfully created dataset '{dataset_name}'")
        else:
            logger.error(f"Failed to create dataset: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")

def ensure_graphdb_repository(triplestore_url, dataset_name):
    """Ensure the GraphDB repository exists, create it if it doesn't."""
    try:
        list_url = f"{triplestore_url}/rest/repositories"
        response = requests.get(list_url)
        if response.status_code == 200:
            repositories = response.json()
            repo_exists = any(repo.get('id') == dataset_name for repo in repositories)
            if not repo_exists:
                logger.info(f"Repository '{dataset_name}' does not exist. Creating it...")
                create_graphdb_repository(triplestore_url, dataset_name)
            else:
                logger.info(f"Repository '{dataset_name}' already exists.")
        else:
            logger.warning(f"Could not check repositories: {response.status_code}")
            create_graphdb_repository(triplestore_url, dataset_name)
    except Exception as e:
        logger.warning(f"Error checking/creating repository: {e}")

def create_graphdb_repository(triplestore_url, dataset_name):
    """Create a new GraphDB repository."""
    try:
        create_url = f"{triplestore_url}/rest/repositories"
        repo_config = {
            "id": dataset_name,
            "title": f"{dataset_name} Repository",
            "type": "graphdb:SailRepository"
        }
        response = requests.post(create_url, json=repo_config)
        if response.status_code == 201:
            logger.info(f"Successfully created repository '{dataset_name}'")
        else:
            logger.error(f"Failed to create repository: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
