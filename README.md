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
    %% Style Definitions for a Versatile, Light/Dark Mode Compatible Theme
    %% Palette: Blue, Green, Purple

    %% Backend Containers (Darker Blue)
    classDef backend-container fill:#1e40af,stroke:#60a5fa,color:#eff6ff,stroke-width:2px;
    %% Backend Inner Nodes (Lighter Blue)
    classDef backend-inner fill:#1d4ed8,stroke:#93c5fd,color:#eff6ff,stroke-width:2px;

    %% Frontend Containers (Darker Green)
    classDef frontend-container fill:#047857,stroke:#34d399,color:#f0fdf4,stroke-width:2px;
    %% Frontend Inner Nodes (Lighter Green)
    classDef frontend-inner fill:#059669,stroke:#6ee7b7,color:#f0fdf4,stroke-width:2px;

    %% Ontology Containers (Darker Purple)
    classDef ontology-container fill:#5b21b6,stroke:#a78bfa,color:#f5f3ff,stroke-width:2px;
    %% Ontology Inner Nodes (Lighter Purple)
    classDef ontology-inner fill:#6d28d9,stroke:#c4b5fd,color:#f5f3ff,stroke-width:2px;
    
    %% External Node Style (Neutral Gray)
    classDef external fill:#4b5563,stroke:#9ca3af,color:#f3f4f6,stroke-width:2px;

    %% A single, default link style is more robust
    linkStyle default stroke:#38bdf8,stroke-width:2px;

    %% Define All Modules First
    
    %% External Actor & Inputs
    user([User])
    repo[(Code Repository)]

    %% Central Pipeline Modules
    subgraph Portal["Portal (Next.js)"]
        direction TB
        upload[Upload UI]
        dashboard[Dashboard & Analytics]
        search[Semantic Search]
        graphviz[Graph Visualization]
    end

    subgraph API["API Server"]
        api_server[FastAPI Server]
    end

    subgraph Extraction["Extraction Module"]
        direction TB
        ext_main[Main Extractor]
        ext_main --> ext_code[Code Extractor] & ext_doc[Doc Extractor] & ext_git[Git Extractor] & ext_content[Content Extractor]
    end

    subgraph Annotation["Annotation Module"]
        direction TB
        annotator[Semantic Annotator]
        sim_calc[Similarity Calculator]
        postproc[Postprocessing]
        annotator --> sim_calc --> postproc
    end

    subgraph KnowledgeGraph["Knowledge Graph Core"]
        direction TB
        graph_manager[Graph Manager]
        namespaces[Namespaces]
        triplestore_api[Triplestore API]
        graph_manager --> namespaces & triplestore_api
    end
    
    %% Supporting Side Modules
    allegrograph[(AllegroGraph<br>Triplestore)]
    subgraph Ontology["Ontology Module"]
        direction TB
        ontology_cache[Ontology Cache]
        wdo[WDO] & bfo[BFO] & dcterms[DCTERMS] --> ontology_cache
    end

    %% Define Connections for Symmetrical Layout
    
    %% Main vertical spine
    user --> Portal --> API --> Extraction --> Annotation --> KnowledgeGraph
    
    %% Inputs from the left
    repo -->|"Source code, docs, git"| Extraction
    
    %% Supporting resources on the right
    Annotation -->|"Links entities to ontology"| Ontology
    KnowledgeGraph -->|"Ontology Lookups"| Ontology
    triplestore_api <-->|"SPARQL Endpoint"| allegrograph
    
    %% Feedback loop on the left. The <.-> syntax creates a dotted line automatically.
    API <.->|"Queries & Manages KG"| KnowledgeGraph


    %% Apply Styling
    
    %% 1. Style external elements
    class user,repo,allegrograph external;
    
    %% 2. Style the INNER nodes
    class upload,dashboard,search,graphviz frontend-inner;
    class api_server,ext_main,ext_code,ext_doc,ext_git,ext_content,annotator,sim_calc,postproc,graph_manager,namespaces,triplestore_api backend-inner;
    class ontology_cache,wdo,bfo,dcterms ontology-inner;

    %% 3. Style the OUTER subgraph containers
    class Portal frontend-container;
    class API,Extraction,Annotation,KnowledgeGraph backend-container;
    class Ontology ontology-container;
```

## Setting Up

### Prerequisites

- **Python 3.12**
- **Node.js 18+** and pnpm
- **Git**
- **Python Virtual Environment** (make sure it is 3.12)

### Backend Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/shama-llama/semantic-web-kms.git
   cd semantic-web-kms
   ```

2. **Set up Python virtual environment**

   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install development dependencies (optional)**

   ```bash
   pip install -r requirements-dev.txt
   ```

5. **Set up environment variables**

   Create a `.env` file in the project root with the following variables:

   ```bash
   # AllegroGraph configuration
   AGRAPH_SERVER_URL=https://xyz.allegrograph.cloud
   AGRAPH_CLOUD_URL=https://xyz.allegrograph.cloud/repositories/semantic-web-kms
   AGRAPH_USER=admin
   AGRAPH_PASSWORD=password # the server password, NOT your ag account password
   AGRAPH_REPOSITORY=semantic-web-kms
   AGRAPH_USE_SSL=true
   
   # Google Gemini API Key (for semantic annotation)
   GOOGLE_API_KEY=api_key
   ```

### Frontend Setup

1. **Navigate to the portal directory**

   ```bash
   cd portal
   ```

2. **Install Node.js dependencies**

   ```bash
   pnpm install
   ```

3. **Set up frontend environment variables**

   Create a `.env.local` file in the `portal` directory with:

   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

### Running the Application

1. **Start the backend server** (from project root)

   ```bash
   flask run
   # or for production:
   # gunicorn --bind 0.0.0.0:5000 wsgi:app
   ```

2. **Start the frontend development server** (from portal directory)

   ```bash
   pnpm dev
   ```

3. **Access the application**

   - Frontend: [http://localhost:3000]
   - API: [http://localhost:8000]

### Development Tools

- **Linting & Formatting**

  ```bash
  # Python
  black .
  isort .
  flake8
  
  # JavaScript/TypeScript (from portal directory)
  pnpm lint
  ```

- **Testing**

  ```bash
  # Python tests
  pytest
  
  # Frontend tests (from portal directory)
  pnpm test
  ```

## License

This project is licensed under the terms of the [MIT License](LICENSE)
