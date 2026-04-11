import React from 'react';
import { IndicatorDashboardItem } from '../../types';
import { Sparkline } from './Sparkline';
import { Clock, ChevronUp, ChevronDown } from 'lucide-react';

interface IndicatorsTableProps {
    indicators: IndicatorDashboardItem[];
    loading: boolean;
    sort: string;
    direction: string;
    onSort: (field: string) => void;
}

export const IndicatorsTable: React.FC<IndicatorsTableProps> = ({
    indicators,
    loading,
    sort,
    direction,
    onSort
}) => {
    // Helper for table headers
    const SortIcon = ({ field }: { field: string }) => {
        if (sort !== field) return <div style={{ width: 16 }} />;
        return direction === 'asc' ? <ChevronUp size={16} /> : <ChevronDown size={16} />;
    };

    const renderHeader = (field: string, label: string) => (
        <th
            onClick={() => onSort(field)}
            style={{ cursor: 'pointer', userSelect: 'none' }}
        >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {label}
                <SortIcon field={field} />
            </div>
        </th>
    );

    if (loading) {
        return <div style={{ padding: '1rem', textAlign: 'center' }}>Laden...</div>;
    }

    if (!indicators.length) {
        return <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>Geen indicatoren gevonden.</div>;
    }

    return (
        <div style={{ overflowX: 'auto' }}>
            <table className="table">
                <thead>
                    <tr>
                        {renderHeader('naam', 'Indicator Naam')}
                        {renderHeader('kwadrant', 'Kwadrant')}
                        <th>Status</th>
                        {renderHeader('years_count', 'Data Historie')}
                        <th>Trend (5j)</th>
                        {renderHeader('last_updated', 'Laatste Update')}
                    </tr>
                </thead>
                <tbody>
                    {indicators.map((indicator) => (
                        <tr key={indicator.uuid}>
                            <td>
                                <div style={{ fontWeight: 600 }}>{indicator.naam}</div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>ID: {indicator.uuid.substring(0, 8)}...</div>
                            </td>
                            <td>
                                <span className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
                                    {indicator.kwadrant}
                                </span>
                            </td>
                            <td>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    {/* Data Status */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Waarde</span>
                                        <div style={{ width: 40, height: 4, background: indicator.years_count > 0 ? '#10B981' : '#334155', borderRadius: 2 }} />
                                    </div>

                                    {/* Meta Status */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                        <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>Meta</span>
                                        <div style={{ width: 40, height: 4, background: indicator.meta_complete ? '#10B981' : '#F59E0B', borderRadius: 2 }} />
                                    </div>
                                </div>
                            </td>
                            <td>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    {indicator.years_count} jaar
                                </div>
                            </td>
                            <td>
                                <Sparkline data={indicator.sparkline} width={100} height={30} color="#3b82f6" />
                            </td>
                            <td>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    {indicator.last_updated ? (
                                        <>
                                            <Clock size={14} color="var(--color-text-muted)" />
                                            {new Date(indicator.last_updated).toLocaleDateString()}
                                        </>
                                    ) : (
                                        <span style={{ color: '#EF4444', fontSize: '0.875rem' }}>Nooit</span>
                                    )}
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
