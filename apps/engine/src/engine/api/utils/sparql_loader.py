import os

from flask import current_app


def load_query(name: str) -> str:
    """Loads a SPARQL query from the sparql directory.

    Args:
        name (str): Relative path to the .rq file (e.g., 'dashboard/repositories_count.rq')

    Returns:
        str: The contents of the SPARQL query file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = os.path.join(current_app.root_path, "sparql", name)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        current_app.logger.error(f"SPARQL query file not found: {path}")
        raise
