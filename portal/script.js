// Global state
let currentView = 'dashboard';
let searchResults = [];
let repositories = [];
let graphData = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    loadSampleData();
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

// View Management
function showView(viewName) {
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

    // Update page title
    const titles = {
        'dashboard': 'Dashboard',
        'repositories': 'Repositories',
        'search': 'Search',
        'graph': 'Knowledge Graph',
        'analytics': 'Analytics'
    };
    document.getElementById('page-title').textContent = titles[viewName];

    // Show/hide views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');

    currentView = viewName;

    // Load view-specific data
    switch(viewName) {
        case 'dashboard':
            updateDashboardStats();
            break;
        case 'repositories':
            loadRepositories();
            break;
        case 'search':
            // Search view is ready
            break;
        case 'graph':
            initializeGraph();
            break;
        case 'analytics':
            loadAnalytics();
            break;
    }
}

// Dashboard Functions
function updateDashboardStats() {
    // Simulate loading stats
    document.getElementById('total-repos').textContent = repositories.length;
    document.getElementById('total-files').textContent = repositories.reduce((sum, repo) => sum + (repo.files || 0), 0);
    document.getElementById('total-entities').textContent = repositories.reduce((sum, repo) => sum + (repo.entities || 0), 0);
    document.getElementById('total-relationships').textContent = repositories.reduce((sum, repo) => sum + (repo.relationships || 0), 0);
}

// Repository Management
function showAddRepoModal() {
    document.getElementById('add-repo-modal').classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function addRepository() {
    const repoType = document.querySelector('input[name="repo-type"]:checked').value;
    let repoUrl = '';
    
    if (repoType === 'github') {
        repoUrl = document.getElementById('github-url').value;
    } else {
        repoUrl = document.getElementById('local-path').value;
    }

    if (!repoUrl) {
        alert('Please enter a repository URL or path');
        return;
    }

    // Simulate adding repository
    const newRepo = {
        id: Date.now(),
        name: repoUrl.split('/').pop() || 'New Repository',
        url: repoUrl,
        type: repoType,
        status: 'analyzing',
        files: 0,
        entities: 0,
        relationships: 0,
        lastUpdated: new Date().toISOString()
    };

    repositories.push(newRepo);
    closeModal('add-repo-modal');
    loadRepositories();
    updateDashboardStats();

    // Simulate analysis completion
    setTimeout(() => {
        newRepo.status = 'completed';
        newRepo.files = Math.floor(Math.random() * 1000) + 100;
        newRepo.entities = Math.floor(Math.random() * 500) + 50;
        newRepo.relationships = Math.floor(Math.random() * 2000) + 200;
        loadRepositories();
        updateDashboardStats();
    }, 3000);
}

function loadRepositories() {
    const grid = document.getElementById('repositories-grid');
    grid.innerHTML = '';

    repositories.forEach(repo => {
        const repoCard = createRepoCard(repo);
        grid.appendChild(repoCard);
    });
}

function createRepoCard(repo) {
    const card = document.createElement('div');
    card.className = 'repo-card';
    
    const statusClass = repo.status === 'completed' ? 'completed' : 'analyzing';
    const statusText = repo.status === 'completed' ? 'Analysis Complete' : 'Analyzing...';
    
    card.innerHTML = `
        <div class="repo-header">
            <div class="repo-name">${repo.name}</div>
            <div class="repo-url">${repo.url}</div>
        </div>
        <div class="repo-stats">
            <div class="repo-stat">
                <div class="repo-stat-number">${repo.files}</div>
                <div class="repo-stat-label">Files</div>
            </div>
            <div class="repo-stat">
                <div class="repo-stat-number">${repo.entities}</div>
                <div class="repo-stat-label">Entities</div>
            </div>
            <div class="repo-stat">
                <div class="repo-stat-number">${repo.relationships}</div>
                <div class="repo-stat-label">Relationships</div>
            </div>
        </div>
        <div class="repo-actions">
            <button class="btn btn-secondary" onclick="viewRepoDetails(${repo.id})">
                <i class="fas fa-eye"></i>
                View Details
            </button>
            <button class="btn btn-secondary" onclick="searchInRepo(${repo.id})">
                <i class="fas fa-search"></i>
                Search
            </button>
        </div>
    `;
    
    return card;
}

// Search Functions
function performSearch() {
    const query = document.getElementById('search-query').value;
    const typeFilter = document.getElementById('filter-type').value;
    const languageFilter = document.getElementById('filter-language').value;
    const repoFilter = document.getElementById('filter-repository').value;

    if (!query.trim()) {
        alert('Please enter a search query');
        return;
    }

    // Simulate search results
    const mockResults = generateMockSearchResults(query, typeFilter, languageFilter, repoFilter);
    displaySearchResults(mockResults);
}

function generateMockSearchResults(query, typeFilter, languageFilter, repoFilter) {
    const mockData = [
        {
            id: 1,
            title: 'CodeExtractor',
            type: 'class',
            language: 'python',
            repository: 'semantic-web-kms',
            path: 'app/extraction/code_extractor.py',
            snippet: `class CodeExtractor:\n    def __init__(self, config):\n        self.config = config\n        self.parser = None`
        },
        {
            id: 4,
            title: 'GraphManager',
            type: 'class',
            language: 'python',
            repository: 'semantic-web-kms',
            path: 'app/core/graph_manager.py',
            snippet: `class GraphManager:\n    """Manages RDF graph operations and SPARQL queries."""\n    \n    def __init__(self, triplestore_url):\n        self.triplestore_url = triplestore_url`
        }
    ];

    // Filter results based on query and filters
    return mockData.filter(item => {
        const matchesQuery = item.title.toLowerCase().includes(query.toLowerCase()) ||
                           item.snippet.toLowerCase().includes(query.toLowerCase());
        const matchesType = !typeFilter || item.type === typeFilter;
        const matchesLanguage = !languageFilter || item.language === languageFilter;
        const matchesRepo = !repoFilter || item.repository === repoFilter;
        
        return matchesQuery && matchesType && matchesLanguage && matchesRepo;
    });
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
        resultItem.onclick = () => showAssetDetails(result);
        
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

// Asset Details
function showAssetDetails(asset) {
    document.getElementById('asset-title').textContent = asset.title;
    
    // Populate asset info
    document.getElementById('asset-info').innerHTML = `
        <div style="display: grid; gap: 1rem;">
            <div>
                <strong>Type:</strong> ${asset.type}
            </div>
            <div>
                <strong>Language:</strong> ${asset.language}
            </div>
            <div>
                <strong>Repository:</strong> ${asset.repository}
            </div>
            <div>
                <strong>Path:</strong> ${asset.path}
            </div>
            <div>
                <strong>Code:</strong>
                <pre style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; margin-top: 0.5rem;">${asset.snippet}</pre>
            </div>
        </div>
    `;
    
    // Populate relationships
    document.getElementById('relationships-list').innerHTML = `
        <div style="color: #64748b; font-style: italic;">
            Related assets will be displayed here based on semantic relationships.
        </div>
    `;
    
    // Populate code
    document.getElementById('code-viewer').innerHTML = `
        <pre style="background: #f8fafc; padding: 1rem; border-radius: 0.5rem; overflow-x: auto;">${asset.snippet}</pre>
    `;
    
    document.getElementById('asset-modal').classList.add('active');
}

// Tab Management
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

// Graph Functions
function initializeGraph() {
    const canvas = document.getElementById('graph-canvas');
    canvas.innerHTML = `
        <div class="graph-placeholder">
            <i class="fas fa-project-diagram"></i>
            <h3>Knowledge Graph</h3>
            <p>Visualize relationships between your code entities and documentation</p>
            <button class="btn btn-primary" onclick="loadSampleGraph()">Load Sample Graph</button>
        </div>
    `;
}

function loadSampleGraph() {
    // Simulate loading graph data
    const canvas = document.getElementById('graph-canvas');
    canvas.innerHTML = `
        <div style="padding: 2rem; text-align: center;">
            <div style="background: #f8fafc; border-radius: 0.5rem; padding: 2rem; margin-bottom: 1rem;">
                <h4>Sample Knowledge Graph</h4>
                <p>This would display an interactive graph visualization using D3.js or Cytoscape.js</p>
                <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem;">
                    <div style="background: #667eea; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem;">CodeExtractor</div>
                    <div style="color: #64748b;">→</div>
                    <div style="background: #10b981; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem;">extractCodeEntities</div>
                    <div style="color: #64748b;">→</div>
                    <div style="background: #f59e0b; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem;">GraphManager</div>
                </div>
            </div>
            <button class="btn btn-secondary" onclick="initializeGraph()">Reset Graph</button>
        </div>
    `;
    
    // Update graph stats
    document.getElementById('node-count').textContent = '3';
    document.getElementById('edge-count').textContent = '2';
}

function resetGraph() {
    initializeGraph();
}

function exportGraph() {
    alert('Graph export functionality would be implemented here');
}

// Analytics Functions
function loadAnalytics() {
    // Simulate loading analytics data
    const charts = ['language-chart', 'entity-chart', 'activity-chart'];
    
    charts.forEach(chartId => {
        const container = document.getElementById(chartId);
        container.innerHTML = `
            <div style="text-align: center; color: #64748b;">
                <i class="fas fa-chart-bar" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                <p>Chart visualization would be rendered here using Chart.js or D3.js</p>
            </div>
        `;
    });
}

// Utility Functions
function loadSampleData() {
    // Load sample repositories
    repositories = [
        {
            id: 1,
            name: 'semantic-web-kms',
            url: 'https://github.com/user/semantic-web-kms',
            type: 'github',
            status: 'completed',
            files: 45,
            entities: 156,
            relationships: 342,
            lastUpdated: '2024-01-15T10:30:00Z'
        },
        {
            id: 2,
            name: 'web-portal-frontend',
            url: 'https://github.com/user/web-portal-frontend',
            type: 'github',
            status: 'completed',
            files: 23,
            entities: 89,
            relationships: 167,
            lastUpdated: '2024-01-14T15:45:00Z'
        }
    ];
    
    updateDashboardStats();
}

function viewRepoDetails(repoId) {
    const repo = repositories.find(r => r.id === repoId);
    if (repo) {
        alert(`Repository details for ${repo.name} would be displayed here`);
    }
}

function searchInRepo(repoId) {
    const repo = repositories.find(r => r.id === repoId);
    if (repo) {
        showView('search');
        document.getElementById('filter-repository').value = repo.name;
        document.getElementById('search-query').focus();
    }
}

// Close modals when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            modal.classList.remove('active');
        });
    }
}); 