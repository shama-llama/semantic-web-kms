from flask import Flask, request, jsonify
from flask_cors import CORS
from elasticsearch import Elasticsearch
import requests
import os
from rdflib import Graph

# Import services using absolute imports if needed, e.g.:
# Import services using absolute imports if needed, e.g.:
# from app.services.rdf_triple_manager import RDFTripleManager
# from app.services.semantic_annotation import SemanticAnnotator
# from app.services.extract_code import ...
# from app.services.extract_docs import ...
# from app.services.detect_files import ...
# from app.ingest.ingest import ...

# Configurations (customize as needed)
FUSEKI_URL = os.environ.get('FUSEKI_URL', 'http://localhost:3030')
FUSEKI_DATASET = os.environ.get('FUSEKI_DATASET', 'semantic-web-kms')
FUSEKI_USER = os.environ.get('FUSEKI_USER')
FUSEKI_PASS = os.environ.get('FUSEKI_PASS')
ELASTIC_URL = os.environ.get('ELASTIC_URL', 'http://localhost:9200')
ELASTIC_INDEX = os.environ.get('ELASTIC_INDEX', 'assets')

app = Flask(__name__)
CORS(app)
es = Elasticsearch([ELASTIC_URL])


@app.route('/api/sparql', methods=['POST'])
def sparql_query():
    data = request.get_json()
    query = data.get('query')
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    fuseki_endpoint = f"{FUSEKI_URL}/{FUSEKI_DATASET}/query"
    headers = {'Accept': 'application/sparql-results+json'}
    auth = (FUSEKI_USER, FUSEKI_PASS) if FUSEKI_USER and FUSEKI_PASS else None
    resp = requests.post(
        fuseki_endpoint,
        data={
            'query': query},
        headers=headers,
        auth=auth)
    if resp.status_code == 200:
        return jsonify(resp.json())
    else:
        return jsonify({'error': resp.text}), resp.status_code


@app.route('/api/search', methods=['GET'])
def search():
    q = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    # Elasticsearch query
    es_query = {
        'query': {
            'multi_match': {
                'query': q,
                'fields': ['label^3', 'doc_text', 'code_comments', 'language']
            }
        },
        'from': (page - 1) * size,
        'size': size
    }
    es_results = es.search(index=ELASTIC_INDEX, body=es_query)
    # TODO: Optionally merge with SPARQL results for structured filters
    return jsonify(es_results)

# --- Indexing logic ---


def index_rdf_assets(ttl_path, index_name=ELASTIC_INDEX):
    g = Graph()
    g.parse(ttl_path, format='turtle')
    docs = []
    for s, p, o in g:
        # Only index assets (customize as needed)
        if str(p).endswith('label'):
            doc = {'uri': str(s), 'label': str(o)}
            # Optionally add more fields by querying the graph
            docs.append(doc)
    # Bulk index
    actions = [
        {'_op_type': 'index', '_index': index_name, '_id': d['uri'], '_source': d}
        for d in docs
    ]
    from elasticsearch.helpers import bulk
    bulk(es, actions)
    print(
        f"Indexed {
            len(docs)} assets into Elasticsearch index '{index_name}'")
