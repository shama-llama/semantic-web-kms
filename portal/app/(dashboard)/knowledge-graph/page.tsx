import React from 'react';
import Knowledge_graph_3d from '../../../components/knowledge-graph-3d';

const KnowledgeGraphPage: React.FC = () => (
  <main style={{ width: '100%', height: '100vh', background: '#18181b' }}>
    <h1 style={{ color: '#fff', fontSize: 28, padding: '24px 0 0 24px' }}>Knowledge Graph (3D)</h1>
    <Knowledge_graph_3d />
  </main>
);

export default KnowledgeGraphPage;
