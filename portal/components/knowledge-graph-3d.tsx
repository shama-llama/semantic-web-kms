"use client";

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import ForceGraph3D to avoid SSR issues
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false });

interface Node {
  id: string;
  name: string;
  type: string;
  color: string;
  size: number;
  repository?: string;
  language?: string;
}

interface Link {
  source: string;
  target: string;
  type: string;
  weight: number;
}

interface Cluster {
  id: string;
  name: string;
  nodes: string[];
  color: string;
}

interface GraphData {
  nodes: Node[];
  edges: Link[];
  clusters: Cluster[];
}

const Knowledge_graph_3d: React.FC = () => {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  // ref to ForceGraph3D is not used, so removed
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 400 });

  useEffect(() => {
    fetch('/api/graph?maxNodes=150')
      .then((res) => res.json())
      .then((data) => setGraphData({
        nodes: data.nodes,
        edges: data.edges,
        clusters: data.clusters,
      }));
  }, []);

  useEffect(() => {
    function handleResize() {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    }
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleNodeClick = (node: object) => {
    // Type guard for Node
    if (
      node &&
      typeof (node as Node).name === 'string' &&
      typeof (node as Node).type === 'string' &&
      typeof (node as Node).id === 'string'
    ) {
      setSelectedNode(node as Node)
    }
  }

  return (
    <div className="flex w-full h-full" style={{ minHeight: 0 }}>
      <div ref={containerRef} className="flex-1 min-w-0 h-full relative">
        {graphData && (
          <ForceGraph3D
            // ref removed
            graphData={{ nodes: graphData.nodes, links: graphData.edges }}
            width={dimensions.width}
            height={dimensions.height}
            nodeAutoColorBy="type"
            nodeLabel={(node: object) => {
              const n = node as Node;
              return n.name && n.type ? `${n.name} (${n.type})` : '';
            }}
            nodeThreeObjectExtend={true}
            onNodeClick={handleNodeClick}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={2}
            linkColor={() => '#aaa'}
            nodeOpacity={0.85}
            linkOpacity={0.5}
            backgroundColor="#18181b"
          />
        )}
      </div>
      <div style={{ width: 320, background: '#222', color: '#fff', padding: 16, overflowY: 'auto' }}>
        <h2 style={{ fontSize: 20, marginBottom: 12 }}>Node Details</h2>
        {selectedNode ? (
          <div>
            <div><b>Name:</b> {selectedNode.name}</div>
            <div><b>Type:</b> {selectedNode.type}</div>
            <div><b>ID:</b> <span style={{ wordBreak: 'break-all' }}>{selectedNode.id}</span></div>
            {selectedNode.repository && <div><b>Repository:</b> {selectedNode.repository}</div>}
            {selectedNode.language && <div><b>Language:</b> {selectedNode.language}</div>}
          </div>
        ) : (
          <div>Select a node to see details.</div>
        )}
      </div>
    </div>
  );
};

export default Knowledge_graph_3d; 