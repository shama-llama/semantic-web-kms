# Semantic Web KMS Portal

A modern, responsive web portal for the Semantic Web Knowledge Management System. This portal provides an intuitive interface for managing repositories, searching through extracted knowledge, and visualizing semantic relationships.

## Features

### 🏠 Dashboard
- Overview of repository statistics
- Recent activity feed
- Quick action buttons for common tasks
- Real-time metrics display

### 📁 Repository Management
- Add GitHub repositories or local directories
- View repository analysis status
- Monitor file counts, entities, and relationships
- Repository-specific search and details

### 🔍 Knowledge Search
- Full-text search across code and documentation
- Filter by entity type, programming language, and repository
- Semantic search with relationship awareness
- Quick search from any page

### 🕸️ Knowledge Graph Visualization
- Interactive graph view of semantic relationships
- Node and edge statistics
- Graph navigation and exploration
- Export capabilities

### 📊 Analytics
- Language distribution charts
- Entity type analysis
- Repository activity tracking
- Data visualization dashboards

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- No complex frameworks required - pure HTML, CSS, and JavaScript

### Installation
1. Navigate to the portal directory:
   ```bash
   cd portal
   ```

2. Open `index.html` in your web browser:
   ```bash
   # Using Python's built-in server
   python -m http.server 8000
   
   # Or using Node.js
   npx serve .
   
   # Or simply open index.html directly in your browser
   ```

3. Access the portal at `http://localhost:8000`

## Usage

### Adding a Repository
1. Navigate to the "Repositories" section
2. Click "Add Repository"
3. Choose between GitHub repository or local directory
4. Configure analysis options
5. Click "Add Repository" to start the analysis

### Searching Knowledge
1. Go to the "Search" section
2. Enter your search query
3. Use filters to narrow down results
4. Click on results to view detailed information

### Exploring the Knowledge Graph
1. Navigate to "Knowledge Graph"
2. Click "Load Sample Graph" to see a demonstration
3. Interact with nodes to view relationships
4. Use the sidebar for detailed information

## Design Philosophy

This portal follows modern web design principles:

- **Clean & Minimal**: Focus on content and functionality
- **Responsive**: Works on desktop, tablet, and mobile devices
- **Accessible**: Keyboard navigation and screen reader support
- **Fast**: Lightweight implementation without heavy frameworks
- **Intuitive**: Familiar UI patterns and clear navigation

## Technical Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Styling**: Custom CSS with modern design patterns
- **Icons**: Font Awesome 6
- **Fonts**: Inter (Google Fonts)
- **No Dependencies**: Self-contained and lightweight

## Integration with Backend

The portal is designed to integrate with the Semantic Web KMS backend:

- **API Endpoints**: Ready to connect to Flask API endpoints
- **SPARQL Integration**: Prepared for RDF/SPARQL queries
- **Elasticsearch**: Configured for full-text search
- **Real-time Updates**: WebSocket ready for live data

## Customization

### Styling
- Modify `styles.css` to change colors, fonts, and layout
- Update CSS variables for consistent theming
- Add custom animations and transitions

### Functionality
- Extend `script.js` with additional features
- Add new API endpoints and data handling
- Implement additional visualization components

### Content
- Update `index.html` for new sections or pages
- Modify navigation and menu structure
- Add custom modals and forms

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test across different browsers
5. Submit a pull request

## License

This portal is part of the Semantic Web KMS project and follows the same license terms.

## Support

For issues and questions:
- Check the main project README
- Review the API documentation
- Open an issue in the project repository 