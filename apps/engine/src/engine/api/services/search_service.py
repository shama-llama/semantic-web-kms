from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query

def search_entities(query, entity_type=None, repository=None, limit=50):
    """
    Search for entities in the knowledge graph.
    Args:
        query (str): Search term
        entity_type (str): Optional entity type filter
        repository (str): Optional repository filter
        limit (int): Max results
    Returns:
        list[dict]: List of matching entities
    """
    type_filter = f"FILTER(?entityType = wdo:{entity_type})" if entity_type else ""
    repo_filter = f"FILTER(?repo = <{repository}>)" if repository else ""
    sparql = load_query('search/search_entities.rq').format(
        query=query.replace('"', ''),
        type_filter=type_filter,
        repo_filter=repo_filter,
        limit=limit
    )
    result = db_connector.execute_sparql_query(sparql)
    bindings = result.get('results', {}).get('bindings', [])
    entities = []
    for binding in bindings:
        if 'entityType' not in binding:
            continue
        entity_id = binding['entity']['value']
        name = binding.get('name', {}).get('value', 'Unknown')
        entity_type_val = binding.get('entityType', {}).get('value', 'Unknown')
        entity_type_short = entity_type_val.split('#')[-1] if entity_type_val != 'Unknown' else 'Unknown'
        editorial_note = binding.get('editorialNote', {}).get('value', '')
        file = binding.get('file', {}).get('value', '')
        line = int(binding.get('line', {}).get('value', '0'))
        repo = binding.get('repo', {}).get('value', '')
        confidence = float(binding.get('confidence', {}).get('value', '0.5'))
        file_name = file.split('/')[-1] if file else ''
        entities.append({
            'id': entity_id,
            'name': name,
            'type': entity_type_short.lower(),
            'repository': repo.split('/')[-1] if repo else 'Unknown',
            'description': editorial_note,
            'editorialNote': editorial_note,
            'enrichedDescription': editorial_note,
            'confidence': confidence,
            'snippet': f"{entity_type_short}: {name}",
            'file': file_name,
            'line': line,
        })
    return entities 