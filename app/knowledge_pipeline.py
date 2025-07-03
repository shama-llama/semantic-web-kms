import subprocess
import sys
import os
import requests
from app.triplestore.triple_manager import RDFTripleManager

# Paths
EXTRACTION_CMD = [sys.executable, '-m', 'app.extraction.main_extractor']
ANNOTATION_CMD = [sys.executable, '-m', 'app.annotation.semantic_annotator']
TTL_PATH = os.path.join('output', 'web_development_ontology.ttl')

# Triplestore config
TRIPLESTORE_URL = 'http://localhost:3030'
DATASET_NAME = 'semantic-web-kms'
TRIPLESTORE_TYPE = 'fuseki'

# API config for Elasticsearch re-indexing
API_INDEX_URL = 'http://localhost:5000/api/reindex'  # You may need to implement this endpoint if not present


def run_cmd(cmd, desc):
    print(f'\n[STEP] {desc}...')
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'[ERROR] {desc} failed.')
        sys.exit(1)
    print(f'[OK] {desc} complete.')


def upload_ttl_to_fuseki(ttl_path):
    print(f'\n[STEP] Uploading TTL to Fuseki...')
    manager = RDFTripleManager(
        triplestore_url=TRIPLESTORE_URL,
        dataset_name=DATASET_NAME,
        triplestore_type=TRIPLESTORE_TYPE
    )
    success = manager.upload_file_to_fuseki(ttl_path)
    if not success:
        print('[ERROR] Upload to Fuseki failed.')
        sys.exit(1)
    print('[OK] TTL uploaded to Fuseki.')


def reindex_elasticsearch(ttl_path):
    print(f'\n[STEP] Re-indexing Elasticsearch via API...')
    try:
        resp = requests.post(API_INDEX_URL, json={'ttl_path': ttl_path})
        if resp.status_code == 200:
            print('[OK] Elasticsearch re-indexed.')
        else:
            print(f'[ERROR] Elasticsearch re-index failed: {resp.text}')
            sys.exit(1)
    except Exception as e:
        print(f'[ERROR] Elasticsearch re-index failed: {e}')
        sys.exit(1)


def main():
    run_cmd(EXTRACTION_CMD, 'Run Extraction Pipeline')
    run_cmd(ANNOTATION_CMD, 'Run Semantic Annotation')
    upload_ttl_to_fuseki(TTL_PATH)
    reindex_elasticsearch(TTL_PATH)
    print('\n[ALL DONE] Full pipeline complete.')


if __name__ == '__main__':
    main() 