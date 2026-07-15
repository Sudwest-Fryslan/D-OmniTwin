import React, { useState } from 'react';
import { X, FileText, LayoutTemplate, Monitor } from 'lucide-react';

interface ExportPrintModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const ExportPrintModal: React.FC<ExportPrintModalProps> = ({ isOpen, onClose }) => {
    const [isPrinting, setIsPrinting] = useState(false);

    if (!isOpen) return null;

    const handlePrint = (format: 'a4-portrait' | 'a4-landscape' | 'a3-landscape') => {
        setIsPrinting(true);
        
        // 1. Voeg class toe aan body voor CSS styling
        document.body.classList.add(`print-${format}`);
        
        // 2. Injecteer specifieke @page styles
        const styleEl = document.createElement('style');
        styleEl.id = 'dynamic-print-style';
        if (format === 'a4-portrait') {
            styleEl.innerHTML = '@media print { @page { size: A4 portrait; margin: 15mm; } }';
        } else if (format === 'a4-landscape') {
            styleEl.innerHTML = '@media print { @page { size: A4 landscape; margin: 15mm; } }';
        } else if (format === 'a3-landscape') {
            styleEl.innerHTML = '@media print { @page { size: A3 landscape; margin: 15mm; } }';
        }
        document.head.appendChild(styleEl);

        // 3. Wacht even tot browser styles heeft verwerkt, dan printen
        setTimeout(() => {
            window.print();
            
            // 4. Cleanup
            document.body.classList.remove(`print-${format}`);
            const injectedStyle = document.getElementById('dynamic-print-style');
            if (injectedStyle) {
                injectedStyle.remove();
            }
            setIsPrinting(false);
            onClose();
        }, 100);
    };

    return (
        <div className="hide-on-print" style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)', zIndex: 9999,
            display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
            <div className="card" style={{ width: '400px', padding: '0', background: 'var(--color-surface)' }}>
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border)', padding: '1rem 1.5rem' }}>
                    <h3 style={{ margin: 0 }}>Exporteer PDF / Print</h3>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer' }}>
                        <X size={20} />
                    </button>
                </div>
                
                <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <p style={{ margin: '0 0 0.5rem 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                        Kies het gewenste papierformaat en lay-out.
                    </p>
                    
                    <button 
                        className="btn btn-secondary" 
                        style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', justifyContent: 'flex-start' }}
                        onClick={() => handlePrint('a4-portrait')}
                        disabled={isPrinting}
                    >
                        <FileText size={24} />
                        <div style={{ textAlign: 'left' }}>
                            <strong style={{ color: 'var(--color-text)' }}>A4 Staand (Portrait)</strong>
                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Ideaal voor tabellen en lange lijsten</div>
                        </div>
                    </button>
                    
                    <button 
                        className="btn btn-secondary" 
                        style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', justifyContent: 'flex-start' }}
                        onClick={() => handlePrint('a4-landscape')}
                        disabled={isPrinting}
                    >
                        <LayoutTemplate size={24} />
                        <div style={{ textAlign: 'left' }}>
                            <strong style={{ color: 'var(--color-text)' }}>A4 Liggend (Landscape)</strong>
                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Standaard brede weergave</div>
                        </div>
                    </button>
                    
                    <button 
                        className="btn btn-secondary" 
                        style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', justifyContent: 'flex-start' }}
                        onClick={() => handlePrint('a3-landscape')}
                        disabled={isPrinting}
                    >
                        <Monitor size={24} />
                        <div style={{ textAlign: 'left' }}>
                            <strong style={{ color: 'var(--color-text)' }}>A3 Liggend (Landscape)</strong>
                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Groot formaat, kaarten & grafieken naast elkaar</div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
};
