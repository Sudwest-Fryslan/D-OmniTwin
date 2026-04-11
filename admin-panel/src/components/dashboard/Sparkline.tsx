import React from 'react';

interface SparklineProps {
    data: number[];
    width?: number;
    height?: number;
    color?: string;
}

export const Sparkline: React.FC<SparklineProps> = ({
    data,
    width = 100,
    height = 30,
    color = '#3b82f6'
}) => {
    if (!data || data.length < 2) {
        return <div style={{ width, height, background: 'rgba(0,0,0,0.05)', borderRadius: 4 }}></div>;
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Calculate points
    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * width;
        const normalizedVal = (val - min) / range;
        const y = height - (normalizedVal * height); // Invert Y
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg width={width} height={height} style={{ overflow: 'visible' }}>
            <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    );
};
