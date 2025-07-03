import os
import requests
from requests.auth import HTTPBasicAuth

class AllegroGraphRESTClient:
    """
    A manual REST client for interacting with AllegroGraph, bypassing the
    hanging issues in the official agraph-python library.
    """
    def __init__(self):
        self.repo_url = os.environ.get("AGRAPH_CLOUD_URL")
        self.username = os.environ.get("AGRAPH_USERNAME")
        self.password = os.environ.get("AGRAPH_PASSWORD")
        if not self.repo_url or not self.username or not self.password:
            raise ValueError("Missing one or more AllegroGraph environment variables.")
        # At this point, all are str (not None)
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        print(f"REST client initialized for repository: {self.repo_url}")

    def upload_ttl_file(self, file_path):
        """
        Uploads a Turtle (TTL) file to the repository's statements endpoint.
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found at '{file_path}'")
            return False

        repo_url: str = self.repo_url  # type: ignore
        statements_url = repo_url.rstrip('/') + "/statements"
        headers = {'Content-Type': 'application/x-turtle'}

        print(f"Uploading '{os.path.basename(file_path)}' to {statements_url}...")

        try:
            with open(file_path, 'rb') as f:
                response = self.session.post(statements_url, data=f, headers=headers, timeout=60)
            response.raise_for_status()
            print("File uploaded successfully.")
            return True
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error during file upload: {e}")
            print(f"Response body: {e.response.text}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during file upload: {e}")
            return False

    def test_connection(self):
        """Test connection to the AllegroGraph statements endpoint."""
        statements_url = self.repo_url.rstrip('/') + "/statements" # type: ignore
        try:
            resp = self.session.get(statements_url, timeout=30, verify=False)
            print(f"GET {statements_url} -> {resp.status_code}")
            print(resp.text)
            return resp.status_code, resp.text
        except Exception as e:
            print(f"Connection test failed: {e}")
            return None, str(e)

    def close(self):
        """Closes the underlying requests session."""
        self.session.close()
        print("REST client session closed.")

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    client = AllegroGraphRESTClient()
    client.test_connection()
    client.close()
