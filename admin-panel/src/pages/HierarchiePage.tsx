import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as d3 from 'd3';
import { hierarchyAPI } from '../services/api';
import type { HierarchyNode, HierarchyResponse } from '../types';
import { ChevronRight, Database, Layers, FileText, RefreshCw } from 'lucide-react';

// D3 Tree Node interface
interface TreeNode extends d3.HierarchyNode<HierarchyNode> {
    x0?: number;
    y0?: number;
    _children?: TreeNode[];
}

export const HierarchiePage: React.FC = () => {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [selectedNode, setSelectedNode] = useState<HierarchyNode | null>(null);
    const [breadcrumbs, setBreadcrumbs] = useState<string[]>([]);
    const [dimensions, setDimensions] = useState({ width: 900, height: 600 });

    // Fetch hierarchy data
    const { data, isLoading, error, refetch } = useQuery<HierarchyResponse>({
        queryKey: ['hierarchy'],
        queryFn: async () => {
            const response = await hierarchyAPI.getTree(1);
            return response.data;
        },
    });

    // Update dimensions on resize
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                const { width, height } = containerRef.current.getBoundingClientRect();
                setDimensions({ width: width - 40, height: Math.max(500, height - 100) });
            }
        };
        updateDimensions();
        window.addEventListener('resize', updateDimensions);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // D3 Tree Visualization
    const renderTree = useCallback(() => {
        if (!data?.tree || !svgRef.current) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const margin = { top: 20, right: 120, bottom: 20, left: 150 };
        const width = dimensions.width - margin.left - margin.right;
        const height = dimensions.height - margin.top - margin.bottom;

        // Create root node from data
        const rootData: HierarchyNode = {
            id: 'root',
            naam: 'Kompas Hiërarchie',
            type: 'thema',
            children: data.tree
        };

        const root = d3.hierarchy<HierarchyNode>(rootData) as TreeNode;

        // Store initial positions
        root.x0 = height / 2;
        root.y0 = 0;

        // Collapse children initially (except first level)
        const collapse = (d: TreeNode) => {
            if (d.children && d.depth > 0) {
                d._children = d.children as TreeNode[];
                d.children = undefined;
                d._children.forEach(collapse);
            } else if (d.children) {
                d.children.forEach(child => collapse(child as TreeNode));
            }
        };
        root.children?.forEach(child => collapse(child as TreeNode));

        // Create tree layout
        const treeLayout = d3.tree<HierarchyNode>().size([height, width]);

        // Create main group with zoom
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Zoom behavior
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.3, 3])
            .on('zoom', (event) => {
                g.attr('transform', `translate(${margin.left + event.transform.x},${margin.top + event.transform.y}) scale(${event.transform.k})`);
            });
        svg.call(zoom);

        // Update function
        const update = (source: TreeNode) => {
            const duration = 300;
            const treeData = treeLayout(root);
            const nodes = treeData.descendants() as TreeNode[];
            const links = treeData.links();

            // Normalize depth
            nodes.forEach(d => { d.y = d.depth * 180; });

            // Nodes
            const node = g.selectAll<SVGGElement, TreeNode>('g.node')
                .data(nodes, d => d.data.id);

            // Enter nodes
            const nodeEnter = node.enter().append('g')
                .attr('class', 'node')
                .attr('transform', () => `translate(${source.y0 || 0},${source.x0 || 0})`)
                .style('cursor', 'pointer')
                .on('click', (event, d) => {
                    event.stopPropagation();
                    // Toggle children
                    if (d.children) {
                        d._children = d.children as TreeNode[];
                        d.children = undefined;
                    } else if (d._children) {
                        d.children = d._children;
                        d._children = undefined;
                    }
                    update(d);
                })
                .on('contextmenu', (event, d) => {
                    event.preventDefault();
                    // Select node for details
                    setSelectedNode(d.data);
                    // Build breadcrumbs
                    const path: string[] = [];
                    let current: TreeNode | null = d;
                    while (current) {
                        if (current.data.naam !== 'Kompas Hiërarchie') {
                            path.unshift(current.data.naam);
                        }
                        current = current.parent as TreeNode | null;
                    }
                    setBreadcrumbs(path);
                });

            // Node circle
            nodeEnter.append('circle')
                .attr('r', 8)
                .attr('fill', d => {
                    if (d.data.type === 'indicator') return '#3b82f6';
                    if (d.data.type === 'onderdeel') return '#22c55e';
                    return '#eab308';
                })
                .attr('stroke', '#1e293b')
                .attr('stroke-width', 2);

            // Expand/collapse indicator
            nodeEnter.append('text')
                .attr('x', 0)
                .attr('y', 0)
                .attr('dy', '0.35em')
                .attr('text-anchor', 'middle')
                .attr('fill', '#1e293b')
                .attr('font-size', '10px')
                .attr('font-weight', 'bold')
                .text(d => d._children ? '+' : (d.children ? '-' : ''));

            // Node label
            nodeEnter.append('text')
                .attr('dy', '.35em')
                .attr('x', d => d.children || d._children ? -15 : 15)
                .attr('text-anchor', d => d.children || d._children ? 'end' : 'start')
                .attr('fill', '#f1f5f9')
                .attr('font-size', '12px')
                .text(d => {
                    const name = d.data.naam || (d.data as any).name || "Naamloos";
                    return name.length > 25 ? name.substring(0, 25) + '...' : name;
                })
                .clone(true).lower()
                .attr('stroke', '#0f172a')
                .attr('stroke-width', 3);

            // Update positions
            const nodeUpdate = nodeEnter.merge(node);
            nodeUpdate.transition().duration(duration)
                .attr('transform', d => `translate(${d.y},${d.x})`);

            // Update circle indicator
            nodeUpdate.select('text')
                .filter((d, i) => i === 1) // Second text element (the +/-)
                .text(d => d._children ? '+' : (d.children ? '-' : ''));

            // Exit nodes
            node.exit().transition().duration(duration)
                .attr('transform', () => `translate(${source.y},${source.x})`)
                .remove();

            // Links
            const link = g.selectAll<SVGPathElement, d3.HierarchyLink<HierarchyNode>>('path.link')
                .data(links, d => (d.target as TreeNode).data.id);

            // Enter links
            const linkEnter = link.enter().insert('path', 'g')
                .attr('class', 'link')
                .attr('fill', 'none')
                .attr('stroke', '#475569')
                .attr('stroke-width', 1.5)
                .attr('d', () => {
                    const o = { x: source.x0 || 0, y: source.y0 || 0 };
                    return diagonal({ source: o, target: o });
                });

            // Update links
            linkEnter.merge(link).transition().duration(duration)
                .attr('d', d => diagonal(d as { source: { x: number; y: number }; target: { x: number; y: number } }));

            // Exit links
            link.exit().transition().duration(duration)
                .attr('d', () => {
                    const o = { x: source.x ?? 0, y: source.y ?? 0 };
                    return diagonal({ source: o, target: o });
                })
                .remove();

            // Store positions for animation
            nodes.forEach(d => {
                d.x0 = d.x;
                d.y0 = d.y;
            });
        };

        // Diagonal generator
        const diagonal = (d: { source: { x: number; y: number }; target: { x: number; y: number } }) => {
            return `M${d.source.y},${d.source.x}
              C${(d.source.y + d.target.y) / 2},${d.source.x}
               ${(d.source.y + d.target.y) / 2},${d.target.x}
               ${d.target.y},${d.target.x}`;
        };

        // Initial render
        update(root);
    }, [data, dimensions]);

    // Render tree when data changes
    useEffect(() => {
        renderTree();
    }, [renderTree]);

    // Get icon for node type
    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'thema': return <Layers size={16} />;
            case 'onderdeel': return <Database size={16} />;
            case 'indicator': return <FileText size={16} />;
            default: return null;
        }
    };

    if (isLoading) {
        return (
            <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                <RefreshCw size={32} className="spin" style={{ color: 'var(--color-primary)' }} />
                <p style={{ marginTop: '1rem', color: 'var(--color-text-secondary)' }}>
                    Hiërarchie laden...
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                <p style={{ color: 'var(--color-error)' }}>Fout bij laden hiërarchie</p>
                <button className="btn btn-primary" onClick={() => refetch()} style={{ marginTop: '1rem' }}>
                    <RefreshCw size={16} /> Opnieuw proberen
                </button>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 140px)' }}>
            {/* Tree Visualization */}
            <div className="card" style={{ flex: 2 }} ref={containerRef}>
                <div className="card-header">
                    <h3 className="card-title">Kompas Hiërarchie</h3>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn btn-secondary" onClick={() => refetch()} title="Ververs">
                            <RefreshCw size={16} />
                        </button>
                    </div>
                </div>

                {/* Breadcrumbs */}
                {breadcrumbs.length > 0 && (
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 1rem',
                        background: 'var(--color-surface-light)',
                        borderRadius: 'var(--radius-md)',
                        marginBottom: '1rem',
                        fontSize: '0.875rem'
                    }}>
                        {breadcrumbs.map((crumb, i) => (
                            <React.Fragment key={i}>
                                {i > 0 && <ChevronRight size={14} style={{ color: 'var(--color-text-muted)' }} />}
                                <span style={{ color: i === breadcrumbs.length - 1 ? 'var(--color-primary)' : 'var(--color-text-secondary)' }}>
                                    {crumb}
                                </span>
                            </React.Fragment>
                        ))}
                    </div>
                )}

                {/* Stats */}
                {data?.stats && (
                    <div style={{
                        display: 'flex',
                        gap: '1rem',
                        marginBottom: '1rem',
                        fontSize: '0.75rem',
                        color: 'var(--color-text-secondary)'
                    }}>
                        <span><strong style={{ color: '#eab308' }}>{data.stats.themas}</strong> Thema's</span>
                        <span><strong style={{ color: '#22c55e' }}>{data.stats.onderdelen}</strong> Onderdelen</span>
                        <span><strong style={{ color: '#3b82f6' }}>{data.stats.indicatoren}</strong> Indicatoren</span>
                    </div>
                )}

                {/* Instructions */}
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                    💡 Klik om uit/in te klappen • Rechtermuisklik voor details • Scroll om te zoomen
                </p>

                {/* SVG Container */}
                <div style={{
                    background: 'var(--color-background)',
                    borderRadius: 'var(--radius-md)',
                    overflow: 'hidden'
                }}>
                    <svg
                        ref={svgRef}
                        width={dimensions.width}
                        height={dimensions.height}
                        style={{ display: 'block' }}
                    />
                </div>
            </div>

            {/* Detail Panel */}
            <div className="card" style={{ flex: 1, maxWidth: '350px' }}>
                <h3 className="card-title" style={{ marginBottom: '1rem' }}>Details</h3>

                {selectedNode ? (
                    <div>
                        {/* Type badge */}
                        <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.25rem 0.75rem',
                            background: selectedNode.type === 'indicator' ? 'rgba(59, 130, 246, 0.2)' :
                                selectedNode.type === 'onderdeel' ? 'rgba(34, 197, 94, 0.2)' :
                                    'rgba(234, 179, 8, 0.2)',
                            color: selectedNode.type === 'indicator' ? '#3b82f6' :
                                selectedNode.type === 'onderdeel' ? '#22c55e' : '#eab308',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '0.75rem',
                            textTransform: 'uppercase',
                            marginBottom: '1rem'
                        }}>
                            {getTypeIcon(selectedNode.type)}
                            {selectedNode.type}
                        </div>

                        {/* Name */}
                        <h4 style={{ marginBottom: '1rem', wordBreak: 'break-word' }}>
                            {selectedNode.naam}
                        </h4>

                        {/* Properties */}
                        <div style={{ fontSize: '0.875rem' }}>
                            <div style={{ marginBottom: '0.5rem' }}>
                                <span style={{ color: 'var(--color-text-secondary)' }}>ID:</span>
                                <code style={{
                                    marginLeft: '0.5rem',
                                    background: 'var(--color-surface-light)',
                                    padding: '0.125rem 0.5rem',
                                    borderRadius: 'var(--radius-sm)',
                                    fontSize: '0.75rem'
                                }}>
                                    {selectedNode.id}
                                </code>
                            </div>

                            {selectedNode.uuid && (
                                <div style={{ marginBottom: '0.5rem' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>UUID:</span>
                                    <code style={{
                                        marginLeft: '0.5rem',
                                        background: 'var(--color-surface-light)',
                                        padding: '0.125rem 0.5rem',
                                        borderRadius: 'var(--radius-sm)',
                                        fontSize: '0.7rem',
                                        wordBreak: 'break-all'
                                    }}>
                                        {selectedNode.uuid}
                                    </code>
                                </div>
                            )}

                            {selectedNode.score_type && (
                                <div style={{ marginBottom: '0.5rem' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Score Type:</span>
                                    <span className={`badge ${selectedNode.score_type.includes('+/+') ? 'badge-positive' : 'badge-negative'}`}
                                        style={{ marginLeft: '0.5rem' }}>
                                        {selectedNode.score_type}
                                    </span>
                                </div>
                            )}

                            {selectedNode.volgorde !== undefined && (
                                <div style={{ marginBottom: '0.5rem' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Volgorde:</span>
                                    <span style={{ marginLeft: '0.5rem' }}>{selectedNode.volgorde}</span>
                                </div>
                            )}

                            {selectedNode.children && (
                                <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--color-border)' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>
                                        {selectedNode.children.length} onderliggende items
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                        Rechtermuisklik op een node om details te bekijken.
                    </p>
                )}
            </div>

            {/* CSS for spin animation */}
            <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
        </div>
    );
};
