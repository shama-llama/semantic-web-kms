from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query

def get_entity_details(entity_id: str):
    """
    Get details for a specific entity, including relationships.
    Args:
        entity_id (str): The entity URI.
    Returns:
        dict or None: Entity details and relationships, or None if not found.
    """
    # Query for entity details
    details_query = load_query('entities/get_entity_details.rq').format(entity_id=entity_id)
    details_result = db_connector.execute_sparql_query(details_query)
    bindings = details_result.get('results', {}).get('bindings', [])
    if not bindings:
        return None
    binding = bindings[0]
    # Query for relationships
    rel_query = load_query('entities/get_entity_relationships.rq').format(entity_id=entity_id)
    rel_result = db_connector.execute_sparql_query(rel_query)
    rel_bindings = rel_result.get('results', {}).get('bindings', [])
    relationships = []
    for rel in rel_bindings:
        relationships.append({
            'entity': rel['relatedEntity']['value'],
            'type': rel['relationshipType']['value'],
            'name': rel.get('relatedLabel', {}).get('value', ''),
        })
    return {
        'id': entity_id,
        'type': binding.get('type', {}).get('value', ''),
        'name': binding.get('label', {}).get('value', ''),
        'editorialNote': binding.get('editorialNote', {}).get('value', ''),
        'description': binding.get('editorialNote', {}).get('value', ''),
        'file': binding.get('file', {}).get('value', ''),
        'line': binding.get('line', {}).get('value', ''),
        'repository': binding.get('repository', {}).get('value', ''),
        'relationships': relationships,
    } 