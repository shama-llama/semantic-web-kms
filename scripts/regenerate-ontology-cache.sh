#!/bin/bash

echo "Regenerating ontology cache..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the cache generation
python -m app.utils.generate_ontology_cache

echo "Ontology cache regenerated successfully!"
echo "The cache now contains the latest ontology mappings." 