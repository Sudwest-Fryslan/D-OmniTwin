import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

export interface IndicatorEntry {
    indicator_naam: string;
    eenheid: string;
    thema: string;
    onderdeel: string;
    score_type: string;
    z_score: number;
    z_score_abs: number;
    impact: string;
    kleur_hex: string;
    waarde: number;
    ref_gemiddelde: number;
    ref_min: number;
    ref_max: number;
}

interface DivergingBarChartProps {
    indicatoren: IndicatorEntry[];
    maxBars?: number;
}

export const DivergingBarChart: React.FC<DivergingBarChartProps> = ({ indicatoren, maxBars = 15 }) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [tooltip, setTooltip] = useState<{show: boolean, x: number, y: number, data: IndicatorEntry | null}>({ show: false, x: 0, y: 0, data: null });

    useEffect(() => {
        if (!svgRef.current || !containerRef.current || indicatoren.length === 0) return;

        const container = containerRef.current;
        const width = container.clientWidth;
        
        const data = [...indicatoren]
            .sort((a, b) => b.z_score_abs - a.z_score_abs)
            .slice(0, maxBars);

        const height = Math.max(300, data.length * 35 + 40);

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        svg.attr('width', width).attr('height', height);

        const margin = { top: 20, right: 80, bottom: 20, left: 160 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        // X scale (diverging from 0)
        const maxZ = d3.max(data, d => Math.abs(d.z_score)) || 1;
        const x = d3.scaleLinear()
            .domain([-maxZ * 1.1, maxZ * 1.1])
            .range([0, innerWidth]);

        // Y scale
        const y = d3.scaleBand()
            .domain(data.map(d => d.indicator_naam))
            .range([0, innerHeight])
            .padding(0.3);

        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Draw 0 line
        g.append('line')
            .attr('x1', x(0))
            .attr('y1', 0)
            .attr('x2', x(0))
            .attr('y2', innerHeight)
            .attr('stroke', 'var(--color-border)')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '4,4');

        // Draw bars
        const bars = g.selectAll('.bar')
            .data(data)
            .enter()
            .append('rect')
            .attr('class', 'bar')
            .attr('y', d => y(d.indicator_naam) || 0)
            .attr('height', y.bandwidth())
            .attr('x', x(0))
            .attr('width', 0)
            .attr('fill', d => d.z_score < 0 ? '#d4b483' : '#2b6ca3')
            .attr('rx', 3)
            .style('cursor', 'pointer')
            .on('mousemove', (event, d) => {
                setTooltip({ show: true, x: event.clientX, y: event.clientY, data: d });
            })
            .on('mouseleave', () => {
                setTooltip(prev => ({ ...prev, show: false }));
            });

        // Animation
        bars.transition()
            .duration(800)
            .ease(d3.easeCubicOut)
            .attr('x', d => Math.min(x(0), x(d.z_score)))
            .attr('width', d => Math.abs(x(d.z_score) - x(0)));

        // Labels left (indicator names)
        g.selectAll('.label')
            .data(data)
            .enter()
            .append('text')
            .attr('x', x(0) - 10)
            .attr('y', d => (y(d.indicator_naam) || 0) + y.bandwidth() / 2)
            .attr('dy', '.35em')
            .attr('text-anchor', 'end')
            .text(d => d.indicator_naam.length > 25 ? d.indicator_naam.substring(0, 23) + '...' : d.indicator_naam)
            .style('font-size', '11px')
            .style('fill', 'var(--color-text-primary)');

        // Value labels right (raw values)
        const valueLabels = g.selectAll('.value-label')
            .data(data)
            .enter()
            .append('text')
            .attr('x', x(0))
            .attr('y', d => (y(d.indicator_naam) || 0) + y.bandwidth() / 2)
            .attr('dy', '.35em')
            .attr('text-anchor', 'start')
            .text(d => `${d.waarde} ${d.eenheid}`)
            .style('font-size', '10px')
            .style('font-weight', '600')
            .style('fill', 'var(--color-text-muted)')
            .style('opacity', 0);

        valueLabels.transition()
            .duration(800)
            .delay(200)
            .attr('x', d => Math.max(x(0), x(d.z_score)) + 10)
            .style('opacity', 1);

    }, [indicatoren, maxBars]);

    return (
        <div ref={containerRef} style={{ width: '100%', position: 'relative' }}>
            <svg ref={svgRef} />
            {tooltip.show && tooltip.data && (
                <div style={{
                    position: 'fixed',
                    top: tooltip.y + 15,
                    left: tooltip.x + 15,
                    background: 'rgba(30, 41, 59, 0.95)',
                    backdropFilter: 'blur(4px)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '8px',
                    padding: '1rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    zIndex: 9999,
                    pointerEvents: 'none',
                    color: 'white',
                    fontSize: '0.85rem',
                    minWidth: '220px'
                }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>
                        {tooltip.data.indicator_naam}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '0.5rem', opacity: 0.9 }}>
                        <span>Waarde:</span> <strong>{tooltip.data.waarde} <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>{tooltip.data.eenheid}</span></strong>
                        <span>Gemiddelde:</span> <strong>{tooltip.data.ref_gemiddelde}</strong>
                        <span>Z-Score:</span> <strong style={{ color: tooltip.data.z_score > 0 ? '#60a5fa' : '#f87171' }}>{tooltip.data.z_score > 0 ? '+' : ''}{tooltip.data.z_score}</strong>
                        <span>Impact:</span> <span style={{ textTransform: 'capitalize' }}>{tooltip.data.impact}</span>
                    </div>
                </div>
            )}
        </div>
    );
};
