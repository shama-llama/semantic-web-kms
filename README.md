# Semantic Web KMS

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green?logo=node.js)](https://nodejs.org/)
![TypeScript](https://img.shields.io/badge/TypeScript-Portal-blue?logo=typescript)
[![Build](https://github.com/shama-llama/semantic-web-kms/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/shama-llama/semantic-web-kms/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Semantic Web KMS** is a modular platform for extracting, semantically annotating, and managing software knowledge. It uses the [Web Development Ontology (WDO)](https://web-development-ontology.netlify.app/), supports multi-language code and documentation extraction, and provides a Next portal for search, analytics, and knowledge graph visualization.

## Features

- Ontology-driven semantic annotation
- Multi-language code and documentation extraction
- Knowledge graph and SPARQL querying (AllegroGraph)
- Interactive portal: dashboard, search, graph visualization
- Extensible pipeline and modular architecture

## Architecture

![Flask](https://img.shields.io/badge/Flask-API%20Server-green?logo=flask)
![AllegroGraph](https://img.shields.io/badge/AllegroGraph-Triplestore-red?logo=apache)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-Portal-cyan?logo=tailwindcss)
![Next.js](https://img.shields.io/badge/Next.js-Portal-black?logo=next.js)

**Semantic Web KMS** is organized into modular components, each responsible for a distinct part of the knowledge management pipeline:

- **Extraction**: Extracts code, documentation, and metadata from repositories.
- **Annotation**: Semantically annotates extracted artifacts using ontologies.
- **Knowledge Graph**: Manages and queries semantic data (RDF, SPARQL, AllegroGraph).
- **Portal**: Provides a Next.js-based web interface for search, analytics, and visualization.

```mermaid
flowchart TD
    %% Style Definitions
    classDef backend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef frontend fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef external fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    %% External Actors & Data Sources
    user([User])
    repo[(Code Repository)]
    allegrograph[(AllegroGraph<br>Triplestore)]

    %% Main Vertical Flow
    user -->|"Uploads repo, queries, explores"| Portal
    
    subgraph Portal["Portal (Next.js/React)"]
        direction TB
        upload[Upload UI]
        dashboard[Dashboard & Analytics]
        search[Semantic Search]
        graphviz[Graph Visualization]
    end

    Portal -->|"REST/GraphQL API Calls"| API

    subgraph API["API Server"]
        api_server[FastAPI Server]
    end
    
    repo -->|"Source code, docs, git"| Extraction
    API -->|"Triggers Extraction"| Extraction

    subgraph Extraction["Extraction Module"]
        direction TB
        ext_main[Main Extractor]
        ext_main --> ext_code[Code Extractor]
        ext_main --> ext_doc[Doc Extractor]
        ext_main --> ext_git[Git Extractor]
        ext_main --> ext_content[Content Extractor]
    end

    Extraction -->|"Extracted Entities"| Annotation

    subgraph Annotation["Annotation Module"]
        direction TB
        annotator[Semantic Annotator]
        sim_calc[Similarity Calculator]
        postproc[Postprocessing]
        annotator --> sim_calc --> postproc
    end

    Annotation -->|"Clean RDF Triples"| KnowledgeGraph

    subgraph KnowledgeGraph["Knowledge Graph Core"]
        direction TB
        graph_manager[Graph Manager]
        namespaces[Namespaces]
        triplestore[Triplestore API]
        graph_manager --> namespaces
        graph_manager --> triplestore
    end

    %% Side Modules (Supporting)
    subgraph Ontology["Ontology Module"]
        direction TB
        ontology_cache[Ontology Cache]
        wdo[WDO]
        bfo[BFO]
        dcterms[DCTERMS]
        wdo & bfo & dcterms --> ontology_cache
    end
    
    %% Connections to External/Side Modules
    Annotation -->|"Links entities to ontology"| Ontology
    KnowledgeGraph -->|"Ontology Lookups"| Ontology
    triplestore <-->|"SPARQL Endpoint"| allegrograph
    
    %% API Feedback Loop
    API <-->|"Queries & Manages KG"| KnowledgeGraph


    %% Apply Styling
    class Extraction,Annotation,Ontology,KnowledgeGraph,API backend;
    class Portal frontend;
    class repo,allegrograph,user external;
```

## License

This project is licensed under the terms of the [MIT License](LICENSE)
