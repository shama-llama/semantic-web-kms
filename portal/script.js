// --- Utility: SPARQL Query Helper ---
async function sparqlQuery(query) {
    const response = await fetch('http://localhost:5000/api/sparql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
    });
    return response.json();
}

// --- Dashboard Stats ---
async function updateDashboardStats() {
    // Show loading states
    document.getElementById('total-repos').textContent = '...';
    document.getElementById('total-files').textContent = '...';
    document.getElementById('total-entities').textContent = '...';
    document.getElementById('total-relationships').textContent = '...';

    try {
        const response = await fetch('http://localhost:5000/api/dashboard_stats');
        if (!response.ok) throw new Error('Failed to fetch dashboard stats');
        const data = await response.json();
        document.getElementById('total-repos').textContent = data.totalRepos ?? 0;
        document.getElementById('total-files').textContent = data.totalFiles ?? 0;
        document.getElementById('total-entities').textContent = data.totalEntities ?? 0;
        document.getElementById('total-relationships').textContent = data.totalRelationships ?? 0;
    } catch (e) {
        document.getElementById('total-repos').textContent = 0;
        document.getElementById('total-files').textContent = 0;
        document.getElementById('total-entities').textContent = 0;
        document.getElementById('total-relationships').textContent = 0;
    }
}

// --- Repositories ---
let repositories = [];
async function fetchRepositories() {
    const query = `
        SELECT ?repository ?name
          (COUNT(DISTINCT ?file) AS ?fileCount)
          (COALESCE(?entityCountSub, 0) AS ?entityCount)
          (COALESCE(?relationshipCountSub, 0) AS ?relationshipCount)
        WHERE {
          ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
          OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name }
          OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file }
          OPTIONAL {
            SELECT ?repository (COUNT(DISTINCT ?entity) AS ?entityCountSub)
            WHERE {
              ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file2 .
              ?entity <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file2 .
              ?entity a ?entityType .
              FILTER(?entityType IN (
                <http://semantic-web-kms.edu.et/wdo#SoftwareCode>,
                <http://semantic-web-kms.edu.et/wdo#FunctionDefinition>,
                <http://semantic-web-kms.edu.et/wdo#ClassDefinition>
              ))
            }
            GROUP BY ?repository
          }
          OPTIONAL {
            SELECT ?repository (COUNT(DISTINCT ?relationship) AS ?relationshipCountSub)
            WHERE {
              ?repository <http://semantic-web-kms.edu.et/wdo#hasFile> ?file3 .
              ?entityA <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file3 .
              ?entityB <http://semantic-web-kms.edu.et/wdo#isElementOf> ?file3 .
              FILTER(?entityA != ?entityB)
              ?entityA ?relPred ?entityB .
              FILTER(?relPred IN (
                <http://semantic-web-kms.edu.et/wdo#invokes>,
                <http://semantic-web-kms.edu.et/wdo#callsFunction>,
                <http://semantic-web-kms.edu.et/wdo#extendsType>,
                <http://semantic-web-kms.edu.et/wdo#implementsInterface>,
                <http://semantic-web-kms.edu.et/wdo#declaresCode>,
                <http://semantic-web-kms.edu.et/wdo#hasField>,
                <http://semantic-web-kms.edu.et/wdo#hasMethod>,
                <http://semantic-web-kms.edu.et/wdo#isRelatedTo>,
                <http://semantic-web-kms.edu.et/wdo#usesFramework>,
                <http://semantic-web-kms.edu.et/wdo#tests>,
                <http://semantic-web-kms.edu.et/wdo#documentsEntity>,
                <http://semantic-web-kms.edu.et/wdo#modifies>,
                <http://semantic-web-kms.edu.et/wdo#imports>,
                <http://semantic-web-kms.edu.et/wdo#isImportedBy>,
                <http://semantic-web-kms.edu.et/wdo#conformsToGuideline>,
                <http://semantic-web-kms.edu.et/wdo#copiesFrom>,
                <http://semantic-web-kms.edu.et/wdo#embedsCode>,
                <http://semantic-web-kms.edu.et/wdo#generates>,
                <http://semantic-web-kms.edu.et/wdo#hasArgument>,
                <http://semantic-web-kms.edu.et/wdo#hasResource>,
                <http://semantic-web-kms.edu.et/wdo#isAbout>,
                <http://semantic-web-kms.edu.et/wdo#isAboutCode>,
                <http://semantic-web-kms.edu.et/wdo#isDependencyOf>,
                <http://semantic-web-kms.edu.et/wdo#specifiesDependency>,
                <http://semantic-web-kms.edu.et/wdo#styles>
              ))
              BIND(CONCAT(STR(?entityA), STR(?relPred), STR(?entityB)) AS ?relationship)
            }
            GROUP BY ?repository
          }
        }
        GROUP BY ?repository ?name ?entityCountSub ?relationshipCountSub
    `;
    try {
        const data = await sparqlQuery(query);
        repositories = (data.results?.bindings || []).map(item => ({
            uri: item.repository.value,
            name: item.name ? item.name.value : item.repository.value.split('/').pop(),
            fileCount: item.fileCount ? parseInt(item.fileCount.value) : 0,
            entityCount: item.entityCount ? parseInt(item.entityCount.value) : 0,
            relationshipCount: item.relationshipCount ? parseInt(item.relationshipCount.value) : 0
        }));
        renderRepositories();
        updateDashboardStats();
        updateRepositoryFilter();
    } catch (e) {
        repositories = [];
        renderRepositories();
        updateDashboardStats();
        updateRepositoryFilter();
    }
}

function renderRepositories() {
    const grid = document.getElementById('repositories-grid');
    if (!grid) return;
    grid.innerHTML = '';
    if (repositories.length === 0) {
        grid.innerHTML = '<div style="padding:2rem;text-align:center;color:#64748b;">No repositories found.</div>';
        return;
    }
    repositories.forEach(repo => {
        const card = document.createElement('div');
        card.className = 'repo-card';
        card.innerHTML = `
            <div class="repo-header">
                <div class="repo-name">${repo.name}</div>
                <div class="repo-url">${repo.uri}</div>
            </div>
            <div class="repo-stats">
                <div class="repo-stat">
                    <div class="repo-stat-number">${repo.fileCount}</div>
                    <div class="repo-stat-label">Files</div>
                </div>
                <div class="repo-stat">
                    <div class="repo-stat-number">${repo.entityCount}</div>
                    <div class="repo-stat-label">Entities</div>
                </div>
                <div class="repo-stat">
                    <div class="repo-stat-number">${repo.relationshipCount}</div>
                    <div class="repo-stat-label">Relationships</div>
                </div>
            </div>
            <div class="repo-actions">
                <button class="btn btn-secondary" onclick="viewRepoDetails('${repo.uri}')">
                    <i class="fas fa-eye"></i>
                    View Details
                </button>
                <button class="btn btn-secondary" onclick="searchInRepo('${repo.uri}')">
                    <i class="fas fa-search"></i>
                    Search
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
    addGraphButton();
}

function updateRepositoryFilter() {
    const select = document.getElementById('filter-repository');
    if (!select) return;
    select.innerHTML = '<option value="">All Repositories</option>';
    repositories.forEach(repo => {
        const opt = document.createElement('option');
        opt.value = repo.uri;
        opt.textContent = repo.name;
        select.appendChild(opt);
    });
}

// --- Search ---
async function performSearch() {
    const queryText = document.getElementById('search-query').value;
    const typeFilter = document.getElementById('filter-type').value;
    const languageFilter = document.getElementById('filter-language').value;
    const repoFilter = document.getElementById('filter-repository').value;
    if (!queryText.trim()) {
        alert('Please enter a search query');
        return;
    }
    let sparql = `SELECT ?entity ?title ?type ?language ?repository ?path ?snippet ?canonicalName ?startLine ?endLine WHERE { ?entity <http://www.w3.org/2000/01/rdf-schema#label> ?title . OPTIONAL { ?entity a ?type } OPTIONAL { ?entity <http://purl.org/dc/terms/language> ?language } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#isInRepository> ?repository } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#hasRelativePath> ?path } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#hasSourceCodeSnippet> ?snippet } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#hasCanonicalName> ?canonicalName } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#startsAtLine> ?startLine } OPTIONAL { ?entity <http://semantic-web-kms.edu.et/wdo#endsAtLine> ?endLine } FILTER(CONTAINS(LCASE(?title), LCASE(\"${queryText}\")))`;
    if (typeFilter) sparql += ` FILTER(?type = <http://semantic-web-kms.edu.et/wdo#${typeFilter.charAt(0).toUpperCase() + typeFilter.slice(1)}>)`;
    if (languageFilter) sparql += ` FILTER(?language = \"${languageFilter}\")`;
    if (repoFilter) sparql += ` FILTER(?repository = <${repoFilter}>)`;
    sparql += ' } LIMIT 50';
    try {
        const data = await sparqlQuery(sparql);
        if (data && data.results && data.results.bindings) {
            const results = data.results.bindings.map((item, idx) => ({
                id: idx + 1,
                uri: item.entity.value,
                title: item.title ? item.title.value : '',
                type: item.type ? item.type.value.split('#').pop() : '',
                language: item.language ? item.language.value : '',
                repository: item.repository ? item.repository.value : '',
                path: item.path ? item.path.value : '',
                snippet: item.snippet ? item.snippet.value : '',
                canonicalName: item.canonicalName ? item.canonicalName.value : '',
                startLine: item.startLine ? item.startLine.value : '',
                endLine: item.endLine ? item.endLine.value : ''
            }));
            displaySearchResults(results);
        } else {
            displaySearchResults([]);
        }
    } catch (e) {
        displaySearchResults([]);
    }
}

function displaySearchResults(results) {
    const container = document.getElementById('search-results');
    container.innerHTML = '';
    if (results.length === 0) {
        container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: #64748b;">
                <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>No results found for your search query.</p>
            </div>
        `;
        return;
    }
    results.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';
        resultItem.onclick = () => showAssetDetails(result.uri);
        resultItem.innerHTML = `
            <div class="result-header">
                <div class="result-title">${result.title}</div>
                <div class="result-type">${result.type}</div>
            </div>
            <div class="result-path">${result.path}</div>
            <div class="result-snippet">${result.snippet}</div>
        `;
        container.appendChild(resultItem);
    });
}

// --- Asset Details Modal ---
async function showAssetDetails(assetUri) {
    // Query all possible fields for the asset
    const query = `SELECT ?type ?language ?repository ?path ?snippet ?canonicalName ?startLine ?endLine ?content WHERE { OPTIONAL { <${assetUri}> a ?type } OPTIONAL { <${assetUri}> <http://purl.org/dc/terms/language> ?language } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#isInRepository> ?repository } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasRelativePath> ?path } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasSourceCodeSnippet> ?snippet } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasCanonicalName> ?canonicalName } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#startsAtLine> ?startLine } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#endsAtLine> ?endLine } OPTIONAL { <${assetUri}> <http://semantic-web-kms.edu.et/wdo#hasContent> ?content } } LIMIT 1`;
    try {
        const data = await sparqlQuery(query);
        const b = data.results?.bindings?.[0] || {};
        document.getElementById('asset-title').textContent = b.canonicalName ? b.canonicalName.value : (b.path ? b.path.value : assetUri.split('/').pop());
        document.getElementById('asset-info').innerHTML = `
            <div style="display: grid; gap: 1rem;">
                <div><strong>Type:</strong> ${b.type ? b.type.value.split('#').pop() : ''}</div>
                <div><strong>Language:</strong> ${b.language ? b.language.value : ''}</div>
                <div><strong>Repository:</strong> ${b.repository ? b.repository.value.split('/').pop() : ''}</div>
                <div><strong>Path:</strong> ${b.path ? b.path.value : ''}</div>
                <div><strong>Start Line:</strong> ${b.startLine ? b.startLine.value : ''}</div>
                <div><strong>End Line:</strong> ${b.endLine ? b.endLine.value : ''}</div>
                <div><strong>Code:</strong><pre style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; margin-top: 0.5rem;">${b.snippet ? b.snippet.value : ''}</pre></div>
                <div><strong>Content:</strong><pre style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; margin-top: 0.5rem;">${b.content ? b.content.value : ''}</pre></div>
            </div>
        `;
        // Relationships tab (example: show all outgoing relationships)
        const relQuery = `SELECT ?predicate ?object WHERE { <${assetUri}> ?predicate ?object . FILTER(STRSTARTS(STR(?predicate), "http://semantic-web-kms.edu.et/wdo#")) } LIMIT 20`;
        const relData = await sparqlQuery(relQuery);
        document.getElementById('relationships-list').innerHTML = relData.results?.bindings?.length
            ? relData.results.bindings.map(r => `<div><strong>${r.predicate.value.split('#').pop()}:</strong> ${r.object.value}</div>`).join('')
            : `<div style="color: #64748b; font-style: italic;">No semantic relationships found.</div>`;
        // Code tab
        document.getElementById('code-viewer').innerHTML = `<pre style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; overflow-x: auto;">${b.snippet ? b.snippet.value : ''}</pre>`;
        document.getElementById('asset-modal').classList.add('active');
    } catch (e) {
        document.getElementById('asset-title').textContent = 'Asset Details';
        document.getElementById('asset-info').innerHTML = '<div style="color:#64748b;">Failed to load asset details.</div>';
        document.getElementById('relationships-list').innerHTML = '';
        document.getElementById('code-viewer').innerHTML = '';
        document.getElementById('asset-modal').classList.add('active');
    }
}

// --- Knowledge Graph Implementation ---
let network = null;
let currentGraphData = { nodes: [], edges: [] };
let selectedNode = null;
let currentRepo = null;

// Enhanced knowledge graph loading with analytics
async function loadKnowledgeGraph(repoUri) {
    currentRepo = repoUri;
    const canvas = document.getElementById('graph-canvas');
    const sidebar = document.getElementById('graph-sidebar');
    
    // Show loading state
    canvas.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#64748b;">
            <div class="loading-spinner"></div>
            <div style="margin-top:1rem;">Loading knowledge graph...</div>
        </div>
    `;
    
    try {
        // Load graph data
        const graphResponse = await fetch(`/api/graph?repo=${encodeURIComponent(repoUri)}`);
        const graphData = await graphResponse.json();
        
        // Load analytics
        const analyticsResponse = await fetch(`/api/graph/analytics?repo=${encodeURIComponent(repoUri)}`);
        const analyticsData = await analyticsResponse.json();
        
        // Process and display graph
        displayGraph(graphData, analyticsData);
        
        // Update sidebar with analytics
        updateGraphSidebar(analyticsData);
        
    } catch (e) {
        console.error('Failed to load knowledge graph:', e);
        canvas.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:#ff6b6b;">
                <i class="fas fa-exclamation-triangle" style="font-size:3rem;margin-bottom:1rem;"></i>
                <div>Failed to load knowledge graph</div>
                <div style="font-size:0.9rem;margin-top:0.5rem;">${e.message}</div>
            </div>
        `;
    }
}

function displayGraph(graphData, analyticsData) {
    const canvas = document.getElementById('graph-canvas');
    canvas.innerHTML = '';
    
    // Store current data
    currentGraphData = graphData;
    
    // Create color mapping for node types
    const colorMap = createColorMap(analyticsData.node_types);
    
    // Prepare nodes with colors and sizes based on centrality
    const nodes = new vis.DataSet(graphData.nodes.map(node => {
        const centrality = analyticsData.centrality.find(c => c.entity === node.id);
        const size = centrality ? Math.min(30, Math.max(16, centrality.degree * 2)) : 16;
        
        return {
            ...node,
            color: colorMap[node.group] || '#666',
            size: size,
            font: { size: Math.max(12, size * 0.6) },
            title: `${node.label}\nType: ${node.group}\nDegree: ${centrality ? centrality.degree : 0}`
        };
    }));
    
    // Prepare edges with colors and labels
    const edges = new vis.DataSet(graphData.edges.map(edge => ({
        ...edge,
        arrows: 'to',
        color: { color: '#999', opacity: 0.6 },
        font: { size: 10, align: 'middle' },
        smooth: { type: 'curvedCW', roundness: 0.2 }
    })));
    
    // Network options
    const options = {
        nodes: {
            shape: 'dot',
            borderWidth: 2,
            shadow: true,
            font: {
                face: 'Inter',
                size: 14,
                color: '#333'
            }
        },
        edges: {
            width: 1,
            shadow: true,
            smooth: {
                type: 'curvedCW',
                roundness: 0.2
            }
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -2000,
                springConstant: 0.04,
                springLength: 200
            },
            stabilization: {
                enabled: true,
                iterations: 1000,
                updateInterval: 100
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true
        },
        layout: {
            improvedLayout: true,
            hierarchical: {
                enabled: false
            }
        }
    };
    
    // Create network
    network = new vis.Network(canvas, { nodes, edges }, options);
    
    // Event handlers
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            showNodeDetails(nodeId);
        } else {
            hideNodeDetails();
        }
    });
    
    network.on('hoverNode', function(params) {
        canvas.style.cursor = 'pointer';
    });
    
    network.on('blurNode', function(params) {
        canvas.style.cursor = 'default';
    });
    
    // Update statistics
    document.getElementById('node-count').textContent = graphData.nodes.length;
    document.getElementById('edge-count').textContent = graphData.edges.length;
}

function createColorMap(nodeTypes) {
    const colors = [
        '#4299e1', '#48bb78', '#ed8936', '#f56565', '#9f7aea',
        '#38b2ac', '#ed64a6', '#667eea', '#f09383', '#4fd1c7'
    ];
    
    const colorMap = {};
    nodeTypes.forEach((type, index) => {
        colorMap[type.type] = colors[index % colors.length];
    });
    
    return colorMap;
}

function updateGraphSidebar(analyticsData) {
    const sidebar = document.getElementById('graph-sidebar');
    
    // Add analytics sections
    const analyticsHtml = `
        <div class="sidebar-section">
            <h4>Graph Analytics</h4>
            <div class="analytics-summary">
                <div class="analytics-item">
                    <span class="analytics-label">Node Types:</span>
                    <span class="analytics-value">${analyticsData.node_types.length}</span>
                </div>
                <div class="analytics-item">
                    <span class="analytics-label">Relationship Types:</span>
                    <span class="analytics-value">${analyticsData.relationship_types.length}</span>
                </div>
                <div class="analytics-item">
                    <span class="analytics-label">Most Connected:</span>
                    <span class="analytics-value">${analyticsData.centrality[0]?.degree || 0}</span>
                </div>
            </div>
        </div>
        
        <div class="sidebar-section">
            <h4>Top Node Types</h4>
            <div class="node-types-list">
                ${analyticsData.node_types.slice(0, 5).map(type => `
                    <div class="type-item">
                        <span class="type-name">${type.type}</span>
                        <span class="type-count">${type.count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="sidebar-section">
            <h4>Top Relationships</h4>
            <div class="relationship-types-list">
                ${analyticsData.relationship_types.slice(0, 5).map(rel => `
                    <div class="rel-item">
                        <span class="rel-name">${rel.type}</span>
                        <span class="rel-count">${rel.count}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="sidebar-section">
            <h4>Most Central Entities</h4>
            <div class="centrality-list">
                ${analyticsData.centrality.slice(0, 5).map(entity => `
                    <div class="centrality-item" onclick="focusOnNode('${entity.entity}')">
                        <span class="entity-name">${entity.label}</span>
                        <span class="entity-degree">${entity.degree}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    // Insert analytics before existing content
    const existingContent = sidebar.innerHTML;
    sidebar.innerHTML = analyticsHtml + existingContent;
}

async function showNodeDetails(nodeId) {
    selectedNode = nodeId;
    const detailsContainer = document.getElementById('node-details');
    
    try {
        const response = await fetch(`/api/graph/entity/${encodeURIComponent(nodeId)}`);
        const data = await response.json();
        
        const details = data.details;
        const incoming = data.incoming;
        const outgoing = data.outgoing;
        
        detailsContainer.innerHTML = `
            <div class="node-details-content">
                <div class="node-header">
                    <h5>${details.label || 'Unknown Entity'}</h5>
                    <span class="node-type">${details.type}</span>
                </div>
                
                ${details.description ? `
                    <div class="node-description">
                        <p>${details.description}</p>
                    </div>
                ` : ''}
                
                ${details.file ? `
                    <div class="node-file">
                        <strong>File:</strong> ${details.file.split('/').pop()}
                        ${details.startLine ? ` (Lines ${details.startLine}-${details.endLine})` : ''}
                    </div>
                ` : ''}
                
                <div class="node-relationships">
                    <div class="rel-section">
                        <h6>Incoming (${incoming.length})</h6>
                        <div class="rel-list">
                            ${incoming.slice(0, 5).map(rel => `
                                <div class="rel-item" onclick="focusOnNode('${rel.source}')">
                                    <span class="rel-source">${rel.sourceLabel}</span>
                                    <span class="rel-type">${rel.relType}</span>
                                </div>
                            `).join('')}
                            ${incoming.length > 5 ? `<div class="rel-more">+${incoming.length - 5} more</div>` : ''}
                        </div>
                    </div>
                    
                    <div class="rel-section">
                        <h6>Outgoing (${outgoing.length})</h6>
                        <div class="rel-list">
                            ${outgoing.slice(0, 5).map(rel => `
                                <div class="rel-item" onclick="focusOnNode('${rel.target}')">
                                    <span class="rel-target">${rel.targetLabel}</span>
                                    <span class="rel-type">${rel.relType}</span>
                                </div>
                            `).join('')}
                            ${outgoing.length > 5 ? `<div class="rel-more">+${outgoing.length - 5} more</div>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="node-actions">
                    <button class="btn btn-sm btn-primary" onclick="showNeighborhood('${nodeId}')">
                        <i class="fas fa-expand"></i>
                        Show Neighborhood
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="highlightConnections('${nodeId}')">
                        <i class="fas fa-link"></i>
                        Highlight Connections
                    </button>
                </div>
            </div>
        `;
        
    } catch (e) {
        detailsContainer.innerHTML = `
            <div class="node-details-content">
                <p>Failed to load node details</p>
            </div>
        `;
    }
}

function hideNodeDetails() {
    selectedNode = null;
    document.getElementById('node-details').innerHTML = '<p>Select a node to view details</p>';
}

function focusOnNode(nodeId) {
    if (network) {
        network.focus(nodeId, { scale: 1.5, animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
        showNodeDetails(nodeId);
    }
}

async function showNeighborhood(nodeId) {
    try {
        const response = await fetch(`/api/graph/neighborhood/${encodeURIComponent(nodeId)}?depth=2`);
        const data = await response.json();
        
        // Update graph with neighborhood data
        displayGraph(data, { node_types: [], centrality: [] });
        
        // Focus on the center node
        if (network) {
            network.focus(nodeId, { scale: 1.2 });
        }
        
    } catch (e) {
        console.error('Failed to load neighborhood:', e);
        alert('Failed to load neighborhood data');
    }
}

function highlightConnections(nodeId) {
    if (!network) return;
    
    // Reset all nodes and edges
    const nodes = network.body.data.nodes;
    const edges = network.body.data.edges;
    
    nodes.forEach(node => {
        nodes.update({ id: node.id, color: { background: '#ddd', border: '#999' } });
    });
    
    edges.forEach(edge => {
        edges.update({ id: edge.id, color: { color: '#999', opacity: 0.3 } });
    });
    
    // Highlight the selected node
    nodes.update({ id: nodeId, color: { background: '#f56565', border: '#e53e3e' } });
    
    // Highlight connected nodes and edges
    const connectedEdges = edges.get().filter(edge => 
        edge.from === nodeId || edge.to === nodeId
    );
    
    connectedEdges.forEach(edge => {
        edges.update({ 
            id: edge.id, 
            color: { color: '#f56565', opacity: 0.8 },
            width: 3
        });
        
        const connectedNodeId = edge.from === nodeId ? edge.to : edge.from;
        nodes.update({ 
            id: connectedNodeId, 
            color: { background: '#4299e1', border: '#3182ce' } 
        });
    });
}

// Graph search functionality
async function searchInGraph() {
    const searchInput = document.getElementById('graph-search-input');
    const query = searchInput.value.trim();
    
    if (!query) return;
    
    try {
        const response = await fetch(`/api/graph/search?q=${encodeURIComponent(query)}&repo=${encodeURIComponent(currentRepo)}`);
        const data = await response.json();
        
        displaySearchResults(data.results);
        
    } catch (e) {
        console.error('Graph search failed:', e);
    }
}

function displaySearchResults(results) {
    const resultsContainer = document.getElementById('graph-search-results');
    
    if (results.length === 0) {
        resultsContainer.innerHTML = '<p>No results found</p>';
        return;
    }
    
    resultsContainer.innerHTML = results.map(result => `
        <div class="search-result-item" onclick="focusOnNode('${result.entity}')">
            <div class="result-header">
                <span class="result-label">${result.label}</span>
                <span class="result-type">${result.type}</span>
            </div>
            ${result.description ? `<div class="result-description">${result.description}</div>` : ''}
            ${result.file ? `<div class="result-file">${result.file.split('/').pop()}</div>` : ''}
        </div>
    `).join('');
}

// Graph filtering
function filterGraphByType(type) {
    if (!network) return;
    
    const nodes = network.body.data.nodes;
    const edges = network.body.data.edges;
    
    if (type === 'all') {
        // Show all nodes and edges
        nodes.forEach(node => {
            nodes.update({ id: node.id, hidden: false });
        });
        edges.forEach(edge => {
            edges.update({ id: edge.id, hidden: false });
        });
    } else {
        // Hide nodes that don't match the type
        nodes.forEach(node => {
            const shouldShow = node.group === type;
            nodes.update({ id: node.id, hidden: !shouldShow });
        });
        
        // Hide edges where both nodes are hidden
        edges.forEach(edge => {
            const fromNode = nodes.get(edge.from);
            const toNode = nodes.get(edge.to);
            const shouldShow = !fromNode.hidden && !toNode.hidden;
            edges.update({ id: edge.id, hidden: !shouldShow });
        });
    }
}

// Graph export functionality
function exportGraph() {
    if (!currentGraphData) return;
    
    const dataStr = JSON.stringify(currentGraphData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = `knowledge-graph-${Date.now()}.json`;
    link.click();
}

// Graph reset functionality
function resetGraph() {
    if (network) {
        network.fit({ animation: { duration: 1000, easingFunction: 'easeInOutQuad' } });
        hideNodeDetails();
    }
}

// Enhanced graph loading with repository selection
function addGraphButton() {
    const grid = document.getElementById('repositories-grid');
    if (!grid) return;
    
    let btn = document.getElementById('show-graph-btn');
    if (!btn) {
        btn = document.createElement('button');
        btn.id = 'show-graph-btn';
        btn.className = 'btn btn-primary';
        btn.innerHTML = '<i class="fas fa-project-diagram"></i> Show Knowledge Graph';
        btn.style = 'margin-bottom: 1rem;';
        btn.onclick = () => {
            const select = document.getElementById('filter-repository');
            const repoUri = select && select.value ? select.value : (repositories[0]?.uri || '');
            if (repoUri) {
                showView('graph');
                loadKnowledgeGraph(repoUri);
            } else {
                alert('Please select a repository first');
            }
        };
        grid.parentNode.insertBefore(btn, grid);
    }
}

function showView(viewName) {
    // Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    // Show the selected view
    const view = document.getElementById(viewName + '-view');
    if (view) view.classList.add('active');

    // Fetch data for the view
    if (viewName === 'dashboard') {
        updateDashboardStats();
        updateRecentActivity();
    }
    if (viewName === 'repositories') fetchRepositories();
    if (viewName === 'analytics') updateAnalytics();
    if (viewName === 'graph') loadKnowledgeGraph(currentRepo);
    // Add more as needed for other views
}

// --- Sidebar Navigation Handler ---
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', function() {
        // Remove active from all
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        this.classList.add('active');
        // Show the corresponding view
        const viewName = this.getAttribute('data-view');
        if (viewName) showView(viewName);
    });
});

// --- Ensure data is loaded on page load ---
document.addEventListener('DOMContentLoaded', function() {
    showView('dashboard');
});

// --- MISSING GLOBAL FUNCTIONS FOR BUTTONS ---
function showAddRepoModal() {
    const modal = document.getElementById('add-repo-modal');
    if (modal) modal.classList.add('active');
}

function addRepository() {
    // Placeholder: You should implement actual repository addition logic here
    alert('Add Repository functionality not implemented yet.');
    closeModal('add-repo-modal');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

function resetGraph() {
    // Placeholder: You should implement actual graph reset logic here
    alert('Reset Graph functionality not implemented yet.');
}

function exportGraph() {
    // Placeholder: You should implement actual graph export logic here
    alert('Export Graph functionality not implemented yet.');
}

function viewRepoDetails(repoUri) {
    // Placeholder: You should implement actual repository details logic here
    alert('View details for: ' + repoUri);
}

function searchInRepo(repoUri) {
    // Switch to search view and filter by repo
    showView('search');
    const select = document.getElementById('filter-repository');
    if (select) select.value = repoUri;
}

// Call addGraphButton after repositories are rendered
const origRenderRepositories = renderRepositories;
renderRepositories = function() {
    origRenderRepositories.apply(this, arguments);
    addGraphButton();
};

// --- Recent Activity ---
async function updateRecentActivity() {
    const container = document.getElementById('activity-list');
    container.innerHTML = '<div style="padding:1rem;color:#64748b;">Loading...</div>';
    try {
        const response = await fetch('/api/recent_activity');
        const data = await response.json();
        if (!data.length) {
            container.innerHTML = '<div style="padding:1rem;color:#64748b;">No recent activity.</div>';
            return;
        }
        container.innerHTML = data.map(item => `
            <div class="activity-item">
                <i class="fas fa-${item.type === 'add' ? 'plus-circle' : item.type === 'update' ? 'edit' : 'trash-alt'}" style="color:${item.type === 'add' ? '#10b981' : item.type === 'update' ? '#667eea' : '#ff6b6b'};"></i>
                <div class="activity-content">
                    <div class="activity-title">${item.title}</div>
                    <div class="activity-desc">${item.desc}</div>
                    <div class="activity-time">${item.time}</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<div style="padding:1rem;color:#ff6b6b;">Failed to load activity.</div>';
    }
}

// --- Analytics ---
async function updateAnalytics() {
    // File Distribution
    const fileDist = document.getElementById('file-distribution-list');
    fileDist.innerHTML = '<div style="padding:1rem;color:#64748b;">Loading...</div>';
    try {
        const resp = await fetch('/api/analytics/file_distribution');
        const data = await resp.json();
        fileDist.innerHTML = data.map(item => `
            <div class="activity-item">
                <i class="fas fa-file-code" style="color:#667eea;"></i>
                <div class="activity-content">
                    <div class="activity-title">${item.label}</div>
                    <div class="activity-desc">${item.count} files</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        fileDist.innerHTML = '<div style="padding:1rem;color:#ff6b6b;">Failed to load file distribution.</div>';
    }
    // Entity Types
    const entityTypes = document.getElementById('entity-types-list');
    entityTypes.innerHTML = '<div style="padding:1rem;color:#64748b;">Loading...</div>';
    try {
        const resp = await fetch('/api/analytics/entity_types');
        const data = await resp.json();
        entityTypes.innerHTML = data.map(item => `
            <div class="activity-item">
                <i class="fas fa-cube" style="color:#764ba2;"></i>
                <div class="activity-content">
                    <div class="activity-title">${item.label}</div>
                    <div class="activity-desc">${item.count} entities</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        entityTypes.innerHTML = '<div style="padding:1rem;color:#ff6b6b;">Failed to load entity types.</div>';
    }
    // Repo Activity
    const repoActivity = document.getElementById('repo-activity-list');
    repoActivity.innerHTML = '<div style="padding:1rem;color:#64748b;">Loading...</div>';
    try {
        const resp = await fetch('/api/analytics/repo_activity');
        const data = await resp.json();
        repoActivity.innerHTML = data.map(item => `
            <div class="activity-item">
                <i class="fas fa-chart-line" style="color:#48bb78;"></i>
                <div class="activity-content">
                    <div class="activity-title">${item.repo}</div>
                    <div class="activity-desc">${item.activity} activities</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        repoActivity.innerHTML = '<div style="padding:1rem;color:#ff6b6b;">Failed to load repo activity.</div>';
    }
}