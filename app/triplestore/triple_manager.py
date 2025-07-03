import logging

import requests

logger = logging.getLogger(__name__)


class RDFTripleManager:
    """Minimal manager for uploading Turtle (.ttl) files to Apache Fuseki using HTTP PUT to the /data?default endpoint."""

    def __init__(self, triplestore_url: str, dataset_name: str):
        self.triplestore_url = triplestore_url.rstrip("/")
        self.dataset_name = dataset_name

    def upload_ttl_to_fuseki(self, file_path: str) -> bool:
        """Upload a Turtle (.ttl) file to the configured Fuseki dataset using HTTP PUT to the /data?default endpoint.

        See: https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html
        """
        endpoint = f"{self.triplestore_url}/{self.dataset_name}/data?default"
        headers = {"Content-Type": "text/turtle"}
        try:
            with open(file_path, "rb") as f:
                resp = requests.put(endpoint, data=f, headers=headers)
            logger.info(f"Upload to {endpoint}: {resp.status_code}")
            if 200 <= resp.status_code < 300:
                logger.info("Upload successful.")
                return True
            else:
                logger.error(f"Upload failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Exception during upload: {e}")
            return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print(
            "Usage: python triple_manager.py <triplestore_url> <dataset_name> <file_path>"
        )
        sys.exit(1)
    triplestore_url = sys.argv[1]
    dataset_name = sys.argv[2]
    file_path = sys.argv[3]
    manager = RDFTripleManager(triplestore_url, dataset_name)
    success = manager.upload_ttl_to_fuseki(file_path)
    if success:
        print("Upload successful.")
    else:
        print("Upload failed.")
