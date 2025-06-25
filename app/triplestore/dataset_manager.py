import logging
import requests
from typing import Dict, List

logger = logging.getLogger(__name__)

class TripleStoreManager:
    """
    High-level manager for triple store operations including dataset management.
    """
    def __init__(self, base_url: str = "http://localhost:3030"):
        self.base_url = base_url
        self.session = requests.Session()

    def create_dataset(self, dataset_name: str) -> bool:
        try:
            url = f"{self.base_url}/$/datasets"
            data = {"dbName": dataset_name, "dbType": "tdb2"}
            response = self.session.post(url, json=data)
            if response.status_code == 200:
                logger.info(f"Created dataset: {dataset_name}")
                return True
            else:
                logger.error(f"Failed to create dataset: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to create dataset {dataset_name}: {e}")
            return False

    def delete_dataset(self, dataset_name: str) -> bool:
        try:
            url = f"{self.base_url}/$/datasets/{dataset_name}"
            response = self.session.delete(url)
            if response.status_code == 200:
                logger.info(f"Deleted dataset: {dataset_name}")
                return True
            else:
                logger.error(f"Failed to delete dataset: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_name}: {e}")
            return False

    def list_datasets(self) -> List[str]:
        try:
            url = f"{self.base_url}/$/datasets"
            response = self.session.get(url)
            if response.status_code == 200:
                datasets = response.json()
                dataset_names = [ds['ds.name'] for ds in datasets.get('datasets', [])]
                logger.info(f"Found datasets: {dataset_names}")
                return dataset_names
            else:
                logger.error(f"Failed to list datasets: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    def get_dataset_info(self, dataset_name: str) -> Dict:
        try:
            url = f"{self.base_url}/{dataset_name}/query"
            params = {'query': 'SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }'}
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                count = data['results']['bindings'][0]['count']['value']
                return {
                    'name': dataset_name,
                    'triple_count': int(count),
                    'status': 'active'
                }
            else:
                logger.error(f"Failed to get dataset info: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Failed to get dataset info for {dataset_name}: {e}")
            return {}
