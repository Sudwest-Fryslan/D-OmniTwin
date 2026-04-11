import React from 'react';

interface QuadrantChartProps {
    name: string;
    percentage: number;
    color: string;
    detail?: string;
}

export const QuadrantChart: React.FC<QuadrantChartProps> = ({
    name,
    percentage,
    color,
    detail
}) => {
    return (
        <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{name.toUpperCase()}</span>
                <span style={{ fontWeight: 600, fontSize: '0.875rem', color: color }}>{percentage}% Complete</span>
            </div>

            {/* Progress Bar Container */}
            <div style={{
                height: '14px',
                width: '100%',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: '7px',
                overflow: 'hidden'
            }}>
                {/* Progress Bar Fill */}
                <div style={{
                    height: '100%',
                    width: `${percentage}%`,
                    background: color,
                    borderRadius: '7px',
                    transition: 'width 1s ease-in-out'
                }}></div>
            </div>

            {detail && (
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                    {detail}
                </div>
            )}
        </div>
    );
};
