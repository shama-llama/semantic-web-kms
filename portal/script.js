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
          (COUNT(DISTINCT ?entity) AS ?entityCount)
          (COUNT(DISTINCT ?relationship) AS ?relationshipCount)
        WHERE {
          ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
          OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name }
          OPTIONAL { ?repository <http://www.w3.org/2000/01/rdf-schema#member> ?file }
          OPTIONAL {
            ?repository <http://www.w3.org/2000/01/rdf-schema#member> ?entity .
            ?entity a ?entityType .
            FILTER(?entityType IN (
              <http://semantic-web-kms.edu.et/wdo#SoftwareCode>,
              <http://semantic-web-kms.edu.et/wdo#FunctionDefinition>,
              <http://semantic-web-kms.edu.et/wdo#ClassDefinition>
            ))
          }
          OPTIONAL {
            ?repository <http://www.w3.org/2000/01/rdf-schema#member> ?entity2 .
            ?entity2 ?relPred ?o .
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
            BIND(CONCAT(STR(?entity2), STR(?relPred), STR(?o)) AS ?relationship)
          }
        }
        GROUP BY ?repository ?name
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

// --- Graph View ---
async function initializeGraph() {
    const canvas = document.getElementById('graph-canvas');
    canvas.innerHTML = `<div style="padding:2rem;text-align:center;color:#64748b;">Loading graph...</div>`;
    const query = `SELECT ?source ?target ?label WHERE { ?source <http://semantic-web-kms.edu.et/wdo#isRelatedTo> ?target . OPTIONAL { ?source <http://www.w3.org/2000/01/rdf-schema#label> ?label } } LIMIT 100`;
    try {
        const data = await sparqlQuery(query);
        if (data && data.results && data.results.bindings) {
            // For demo: just show JSON, but you can render a real graph here
            canvas.innerHTML = `<pre>${JSON.stringify(data.results.bindings, null, 2)}</pre>`;
            document.getElementById('node-count').textContent = data.results.bindings.length;
            document.getElementById('edge-count').textContent = data.results.bindings.length;
        } else {
            canvas.innerHTML = `<div style="padding:2rem;text-align:center;color:#64748b;">No graph data found.</div>`;
            document.getElementById('node-count').textContent = 0;
            document.getElementById('edge-count').textContent = 0;
        }
    } catch (e) {
        canvas.innerHTML = `<div style="padding:2rem;text-align:center;color:#64748b;">Failed to load graph data.</div>`;
        document.getElementById('node-count').textContent = 0;
        document.getElementById('edge-count').textContent = 0;
    }
}
function resetGraph() { initializeGraph(); }
function exportGraph() { alert('Graph export functionality would be implemented here'); }

// --- Analytics ---
async function loadAnalytics() {
    // Language Distribution (use wdo:programmingLanguage)
    const langQuery = `SELECT ?language (COUNT(?entity) AS ?count) WHERE { ?entity <http://semantic-web-kms.edu.et/wdo#programmingLanguage> ?language . } GROUP BY ?language`;
    // Entity Types (only WDO types)
    const typeQuery = `SELECT ?type (COUNT(?entity) AS ?count) WHERE { ?entity a ?type . FILTER(STRSTARTS(STR(?type), "http://semantic-web-kms.edu.et/wdo#")) } GROUP BY ?type`;
    // Repository Activity (commits per repo)
    const repoQuery = `SELECT ?repository (COUNT(?commit) AS ?commitCount) WHERE { ?commit a <http://semantic-web-kms.edu.et/wdo#Commit> . ?commit <http://semantic-web-kms.edu.et/wdo#hasRepository> ?repository . } GROUP BY ?repository`;
    // Recently added repositories (fallback if no commit activity)
    const recentRepoQuery = `SELECT ?repo ?name ?created WHERE { ?repo a <http://semantic-web-kms.edu.et/wdo#Repository> . OPTIONAL { ?repo <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name } OPTIONAL { ?repo <http://semantic-web-kms.edu.et/wdo#hasCreationTimestamp> ?created } } ORDER BY DESC(?created) LIMIT 5`;
    const [langData, typeData, repoData, recentRepoData] = await Promise.all([
        sparqlQuery(langQuery),
        sparqlQuery(typeQuery),
        sparqlQuery(repoQuery),
        sparqlQuery(recentRepoQuery)
    ]);
    // Render file distribution (was language distribution)
    const fileDistList = document.getElementById('file-distribution-list');
    if (langData.results?.bindings?.length) {
        fileDistList.innerHTML = langData.results.bindings.map(l => `
            <div class="activity-item">
                <i class="fas fa-file-code" style="color:#6366f1"></i>
                <div class="activity-content">
                    <div class="activity-title">${l.language.value}</div>
                    <div class="activity-desc">Files: ${l.count.value}</div>
                </div>
            </div>
        `).join('');
    } else {
        fileDistList.innerHTML = '<div style="color:#64748b;text-align:center;">No data</div>';
    }
    // Render entity types
    const entityTypesList = document.getElementById('entity-types-list');
    if (typeData.results?.bindings?.length) {
        const filtered = typeData.results.bindings.filter(t => t.type.value.startsWith('http://semantic-web-kms.edu.et/wdo#'));
        entityTypesList.innerHTML = filtered.length
            ? filtered.map(t => `
                <div class="activity-item">
                    <i class="fas fa-cubes" style="color:#10b981"></i>
                    <div class="activity-content">
                        <div class="activity-title">${t.type.value.split('#').pop()}</div>
                        <div class="activity-desc">Count: ${t.count.value}</div>
                    </div>
                </div>
            `).join('')
            : '<div style="color:#64748b;text-align:center;">No data</div>';
    } else {
        entityTypesList.innerHTML = '<div style="color:#64748b;text-align:center;">No data</div>';
    }
    // Render repo activity
    const repoActivityList = document.getElementById('repo-activity-list');
    if (repoData.results?.bindings?.length) {
        repoActivityList.innerHTML = repoData.results.bindings.map(r => `
            <div class="activity-item">
                <i class="fas fa-database" style="color:#f59e42"></i>
                <div class="activity-content">
                    <div class="activity-title">${r.repository.value.split('/').pop()}</div>
                    <div class="activity-desc">Commits: ${r.commitCount.value}</div>
                </div>
            </div>
        `).join('');
    } else if (recentRepoData.results?.bindings?.length) {
        repoActivityList.innerHTML = recentRepoData.results.bindings.map(r => `
            <div class="activity-item">
                <i class="fas fa-plus-circle" style="color:#10b981"></i>
                <div class="activity-content">
                    <div class="activity-title">${r.name ? r.name.value : r.repo.value.split('/').pop()}</div>
                    <div class="activity-desc">Added ${r.created ? new Date(r.created.value).toLocaleDateString() : 'unknown'}</div>
                </div>
            </div>
        `).join('');
    } else {
        repoActivityList.innerHTML = '<div style="color:#64748b;text-align:center;">No data</div>';
    }
}

// --- Navigation, Tabs, and Modal Management ---
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    fetchRepositories();
});

function initializeApp() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            const view = this.dataset.view;
            showView(view);
        });
    });
    // Quick search
    document.getElementById('quick-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            showView('search');
            document.getElementById('search-query').value = this.value;
            performSearch();
        }
    });
    // Repository type toggle
    document.querySelectorAll('input[name="repo-type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const githubFields = document.getElementById('github-fields');
            const localFields = document.getElementById('local-fields');
            if (this.value === 'github') {
                githubFields.style.display = 'block';
                localFields.style.display = 'none';
            } else {
                githubFields.style.display = 'none';
                localFields.style.display = 'block';
            }
        });
    });
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });
}

// --- Recent Activity (Dashboard) ---
async function fetchRecentActivity() {
    // Get recent commits
    const commitQuery = `
        SELECT ?type ?repo ?date ?desc WHERE {
          ?event a ?type .
          FILTER(?type IN (
            <http://semantic-web-kms.edu.et/wdo#Commit>,
            <http://semantic-web-kms.edu.et/wdo#Repository>
          ))
          OPTIONAL { ?event <http://semantic-web-kms.edu.et/wdo#hasRepository> ?repo }
          OPTIONAL { ?event <http://semantic-web-kms.edu.et/wdo#hasCreationTimestamp> ?date }
          OPTIONAL { ?event <http://purl.org/dc/terms/date> ?date }
          OPTIONAL { ?event <http://semantic-web-kms.edu.et/wdo#hasCommitMessage> ?desc }
          OPTIONAL { ?event <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?desc }
        }
        ORDER BY DESC(?date)
        LIMIT 8
    `;
    const data = await sparqlQuery(commitQuery);
    const list = document.getElementById('activity-list');
    list.innerHTML = '';
    if (data.results?.bindings?.length) {
        // Track seen repository additions to avoid duplicates
        const seenRepos = new Set();
        data.results.bindings.forEach(item => {
            const type = item.type ? item.type.value.split('#').pop() : '';
            const repo = item.repo ? item.repo.value.split('/').pop() : '';
            const date = item.date ? new Date(item.date.value).toLocaleString() : '';
            let icon = 'fa-plus-circle', color = '#10b981', title = '', desc = '', time = date;
            if (type === 'Commit') {
                icon = 'fa-code-branch';
                color = '#6366f1';
                title = 'Commit';
                desc = item.desc ? item.desc.value : repo;
            } else if (type === 'Repository') {
                // Prefer item.desc (hasSimpleName), then extract from item.repo URI
                let repoName = (item.desc && item.desc.value)
                    ? item.desc.value
                    : (item.repo && item.repo.value ? item.repo.value.split('/').pop() : null);
                if (!repoName) return; // skip if no name at all
                if (seenRepos.has(repoName)) return; // skip duplicate
                seenRepos.add(repoName);
                icon = 'fa-plus-circle';
                color = '#10b981';
                title = `Repository added ${repoName}`;
                desc = repoName;
            }
            // Only add to list if not a duplicate repo addition
            if (type !== 'Repository' || (type === 'Repository' && desc && !seenRepos.has(desc))) {
                list.innerHTML += `
                    <div class="activity-item">
                        <i class="fas ${icon}" style="color:${color}"></i>
                        <div class="activity-content">
                            <div class="activity-title">${title}</div>
                            <div class="activity-desc">${desc}</div>
                            <div class="activity-time">${time}</div>
                        </div>
                    </div>
                `;
            }
        });
    } else {
        list.innerHTML = '<div style="color:#64748b;text-align:center;">No recent activity found.</div>';
    }
}

function showView(viewName) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
    const titles = {
        'dashboard': 'Dashboard',
        'repositories': 'Repositories',
        'search': 'Search',
        'graph': 'Knowledge Graph',
        'analytics': 'Analytics'
    };
    document.getElementById('page-title').textContent = titles[viewName];
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');
    switch(viewName) {
        case 'dashboard':
            updateDashboardStats();
            fetchRecentActivity();
            break;
        case 'repositories':
            fetchRepositories();
            break;
        case 'search':
            break;
        case 'graph':
            initializeGraph();
            break;
        case 'analytics':
            loadAnalytics();
            break;
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            modal.classList.remove('active');
        });
    }
});

// --- Repo Details and Search in Repo ---
function viewRepoDetails(repoUri) {
    alert(`Repository details for ${repoUri} would be displayed here`);
}
function searchInRepo(repoUri) {
    showView('search');
    document.getElementById('filter-repository').value = repoUri;
    document.getElementById('search-query').focus();
}
// --- Add Repo Modal (simulated, not persisted) ---
function showAddRepoModal() {
    document.getElementById('add-repo-modal').classList.add('active');
}
function addRepository() {
    alert('Repository addition is not implemented in this demo.');
    closeModal('add-repo-modal');
}
