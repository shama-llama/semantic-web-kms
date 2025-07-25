"""This module provides AllegroGraphRESTClient for interacting with AllegroGraph via HTTP."""

import os

import requests
from requests.auth import HTTPBasicAuth


class AllegroGraphRESTClient:
    """A manual REST client for interacting with AllegroGraph, bypassing the hanging issues in the official agraph-python library."""

    def __init__(self):
        """
        Initialize the REST client with environment variables and session.

        Raises:
            ValueError: If any required AllegroGraph environment variable is missing.
        """
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
        Upload a Turtle (TTL) file to the repository's statements endpoint.

        Args:
            file_path (str): Path to the Turtle (.ttl) file to upload.

        Returns:
            bool: True if the file was uploaded successfully, False otherwise.

        Raises:
            None. All exceptions are caught and logged; returns False on error.
        """
        if not os.path.exists(file_path):
            print(f"Error: File not found at '{file_path}'")
            return False

        repo_url: str = self.repo_url  # type: ignore
        statements_url = repo_url.rstrip("/") + "/statements"
        headers = {"Content-Type": "application/x-turtle"}

        print(f"Uploading '{os.path.basename(file_path)}' to {statements_url}...")

        try:
            with open(file_path, "rb") as f:
                response = self.session.post(
                    statements_url, data=f, headers=headers, timeout=60
                )
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
        """
        Test connection to the AllegroGraph statements endpoint.

        Returns:
            tuple: (status_code (int or None), response_text (str)).
                status_code is None if the request fails.
                response_text contains the response body or error message.

        Raises:
            None. All exceptions are caught and logged; returns (None, error_message) on error.
        """
        statements_url = self.repo_url.rstrip("/") + "/statements"  # type: ignore
        try:
            resp = self.session.get(statements_url, timeout=30, verify=False)
            print(f"GET {statements_url} -> {resp.status_code}")
            print(resp.text)
            return resp.status_code, resp.text
        except Exception as e:
            print(f"Connection test failed: {e}")
            return None, str(e)

    def close(self):
        """
        Close the underlying requests session.

        Returns:
            None
        """
        self.session.close()
        print("REST client session closed.")

    def __enter__(self):
        """
        Enter the runtime context for the REST client.

        Returns:
            AllegroGraphRESTClient: The REST client instance itself.
        """
        return self

    def __exit__(self, *_):
        """
        Exit the runtime context and close the REST client session.

        Args:
            *_: Ignored positional arguments (exception type, value, traceback).

        Returns:
            None
        """
        self.close()


if __name__ == "__main__":
    client = AllegroGraphRESTClient()
    client.test_connection()
    client.close()
