import requests
from flask import current_app, g


class AGraphConnector:
    def init_app(self, app):
        """Initialize the connector with Flask app config."""
        self.agraph_endpoint = f"{app.config['AGRAPH_SERVER_URL']}/repositories/{app.config['AGRAPH_REPO']}"
        self.auth = (app.config["AGRAPH_USERNAME"], app.config["AGRAPH_PASSWORD"])

    def get_session(self):
        """Get or create a session for AllegroGraph communication (per request)."""
        if "agraph_session" not in g:
            g.agraph_session = requests.Session()
            g.agraph_session.auth = self.auth
        return g.agraph_session

    def execute_sparql_query(self, query: str, is_update: bool = False) -> dict:
        """Executes a SPARQL query and returns the JSON result.

        Args:
            query (str): The SPARQL query string.
            is_update (bool): If True, use 'update' instead of 'query' param.

        Returns:
            dict: Parsed JSON result from AllegroGraph.

        Raises:
            Exception: If the request fails or response is invalid.
        """
        session = self.get_session()
        headers = {"Accept": "application/sparql-results+json"}
        payload_key = "update" if is_update else "query"
        try:
            response = session.post(
                self.agraph_endpoint,
                data={payload_key: query},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"SPARQL query failed: {e}")
            raise
