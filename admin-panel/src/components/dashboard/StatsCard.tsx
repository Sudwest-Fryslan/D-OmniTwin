import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
    label: string;
    value: string | number;
    subValue?: string;
    icon: LucideIcon;
    trend?: 'up' | 'down' | 'neutral';
    color?: string;
}

export const StatsCard: React.FC<StatsCardProps> = ({
    label,
    value,
    subValue,
    icon: Icon,
    color = 'var(--color-primary)'
}) => {
    return (
        <div className="stat-card">
            <div className="stat-content">
                <div className="stat-value">{value}</div>
                <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Icon size={16} />
                    {label}
                </div>
                {subValue && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                        {subValue}
                    </div>
                )}
            </div>
            <div className="stat-icon-bg" style={{
                background: color,
                opacity: 0.1,
                position: 'absolute',
                right: '1rem',
                top: '1rem',
                padding: '0.5rem',
                borderRadius: '8px'
            }}>
                <Icon size={24} color={color} style={{ opacity: 10 }} />
                {/* Note: In real CSS we'd handle opacity differently, simplified here */}
            </div>
        </div>
    );
};
