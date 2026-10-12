import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import axios from 'axios';
import { useDialogFocus } from '../hooks/useDialogFocus';

export interface MeldModalContext {
    rapport_type?: string;
    gebied_id?: string;
    gebied_naam?: string;
    url?: string;
}

export interface MeldModalProps {
    isOpen: boolean;
    onClose: () => void;
    context?: MeldModalContext;
}

export const MeldModal: React.FC<MeldModalProps> = ({ isOpen, onClose, context }) => {
    const [type, setType] = useState<'data' | 'ai' | 'systeem' | 'overig'>('data');
    const [onderwerp, setOnderwerp] = useState('');
    const [toelichting, setToelichting] = useState('');
    const [email, setEmail] = useState('');
    const [website, setWebsite] = useState(''); // Honeypot
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [foutmelding, setFoutmelding] = useState<string | null>(null);

    const dialogRef = useDialogFocus<HTMLDivElement>(isOpen, onClose);

    // Initialiseer formulier en default onderwerp op basis van context
    useEffect(() => {
        if (isOpen) {
            setType('data');
            setToelichting('');
            setEmail('');
            setWebsite('');
            setStatus('idle');
            setFoutmelding(null);

            const delen: string[] = [];
            if (context?.rapport_type) delen.push(context.rapport_type);
            if (context?.gebied_naam) delen.push(context.gebied_naam);
            else if (context?.gebied_id) delen.push(context.gebied_id);

            if (delen.length > 0) {
                setOnderwerp(`Afwijking in ${delen.join(' - ')}`);
            } else {
                setOnderwerp('Afwijking in rapport');
            }
        }
    }, [isOpen, context]);

    if (!isOpen) return null;

    // Context omschrijving voor de roze/tint context-balk
    const contextTekst = (() => {
        const items: string[] = [];
        if (context?.rapport_type) items.push(`Rapport: ${context.rapport_type}`);
        if (context?.gebied_naam) items.push(`Gebied: ${context.gebied_naam}`);
        else if (context?.gebied_id) items.push(`Gebied: ${context.gebied_id}`);
        return items.length > 0 ? items.join(' | ') : null;
    })();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setStatus('idle');
        setFoutmelding(null);

        // Honeypot: als website is ingevuld, doen alsof het gelukt is
        if (website.trim()) {
            setIsSubmitting(false);
            setStatus('success');
            setTimeout(() => onClose(), 1500);
            return;
        }

        try {
            await axios.post('/api/meldingen', {
                type,
                onderwerp: onderwerp.trim(),
                toelichting: toelichting.trim(),
                melder_email: email.trim() || undefined,
                context: {
                    ...context,
                    url: context?.url || window.location.href,
                    bron: 'rapport',
                },
            });

            setStatus('success');
            setTimeout(() => {
                onClose();
            }, 1500);
        } catch (err: any) {
            setStatus('error');
            const detail = err?.response?.data?.detail;
            if (typeof detail === 'string') {
                setFoutmelding(detail);
            } else {
                setFoutmelding('Er ging iets mis bij het verzenden van de melding. Probeer het later opnieuw.');
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div
            className="hide-on-print"
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.6)',
                backdropFilter: 'blur(2px)',
                zIndex: 9999,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '1rem',
            }}
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="meld-dialoog-titel"
                className="card"
                style={{
                    width: '540px',
                    maxWidth: '96vw',
                    maxHeight: '90vh',
                    overflowY: 'auto',
                    padding: '1.5rem',
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-lg, 8px)',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
                }}
            >
                {/* Header */}
                <div
                    style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '1rem',
                        borderBottom: '1px solid var(--color-border)',
                        paddingBottom: '0.75rem',
                    }}
                >
                    <h2
                        id="meld-dialoog-titel"
                        style={{
                            margin: 0,
                            fontSize: '1.2rem',
                            fontWeight: 600,
                            color: 'var(--color-text-primary)',
                        }}
                    >
                        Melding doorgeven
                    </h2>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Sluiten"
                        title="Sluiten"
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--color-text-secondary)',
                            cursor: 'pointer',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            borderRadius: '4px',
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Context banner */}
                {contextTekst && (
                    <div
                        style={{
                            background: 'color-mix(in srgb, var(--merk-bg, #a2103e) 12%, transparent)',
                            border: '1px solid color-mix(in srgb, var(--merk-bg, #a2103e) 25%, transparent)',
                            borderRadius: '6px',
                            padding: '0.6rem 0.8rem',
                            marginBottom: '1rem',
                            fontSize: '0.85rem',
                            display: 'flex',
                            gap: '6px',
                        }}
                    >
                        <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Context:</span>
                        <span style={{ color: 'var(--color-text-secondary)' }}>{contextTekst}</span>
                    </div>
                )}

                {/* Statusbericht bij succes */}
                {status === 'success' ? (
                    <div
                        role="status"
                        aria-live="polite"
                        style={{
                            padding: '1.5rem',
                            textAlign: 'center',
                            color: 'var(--color-success, #16a34a)',
                            fontWeight: 600,
                        }}
                    >
                        ✓ Bedankt! Uw melding is geregistreerd.
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {/* Categorie */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="meld-modal-type" style={{ display: 'block', marginBottom: '0.35rem', fontWeight: 500 }}>
                                Categorie
                            </label>
                            <select
                                id="meld-modal-type"
                                className="form-select"
                                value={type}
                                onChange={(e) => setType(e.target.value as any)}
                                style={{ width: '100%' }}
                            >
                                <option value="data">Data- of indicatorafwijking</option>
                                <option value="ai">AI-uitkomst of assistent</option>
                                <option value="systeem">Technisch probleem of bug</option>
                                <option value="overig">Suggestie of overig</option>
                            </select>
                        </div>

                        {/* Onderwerp */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="meld-modal-onderwerp" style={{ display: 'block', marginBottom: '0.35rem', fontWeight: 500 }}>
                                Onderwerp
                            </label>
                            <input
                                id="meld-modal-onderwerp"
                                type="text"
                                className="form-input"
                                required
                                maxLength={120}
                                value={onderwerp}
                                onChange={(e) => setOnderwerp(e.target.value)}
                                placeholder="Korte omschrijving van wat opvalt"
                                style={{ width: '100%' }}
                            />
                        </div>

                        {/* Toelichting */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="meld-modal-toelichting" style={{ display: 'block', marginBottom: '0.35rem', fontWeight: 500 }}>
                                Toelichting
                            </label>
                            <textarea
                                id="meld-modal-toelichting"
                                className="form-input"
                                required
                                maxLength={4000}
                                rows={4}
                                value={toelichting}
                                onChange={(e) => setToelichting(e.target.value)}
                                placeholder="Beschrijf wat er volgens u niet klopt of wat u verwachtte."
                                style={{ width: '100%', resize: 'vertical' }}
                            />
                            <small style={{ color: 'var(--color-warning, #d97706)', fontSize: '0.8rem', display: 'block', marginTop: '4px' }}>
                                ⚠️ Vermeld geen persoonsgegevens zoals namen, burgerservicenummers of contactgegevens in de toelichting.
                            </small>
                        </div>

                        {/* E-mailadres */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="meld-modal-email" style={{ display: 'block', marginBottom: '0.35rem', fontWeight: 500 }}>
                                E-mailadres (optioneel)
                            </label>
                            <input
                                id="meld-modal-email"
                                type="email"
                                className="form-input"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="naam@organisatie.nl"
                                style={{ width: '100%' }}
                            />
                            <small style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem', display: 'block', marginTop: '4px' }}>
                                Alleen als u een terugkoppeling wenst. Wordt conform AVG gewist zodra de melding is afgehandeld.
                            </small>
                        </div>

                        {/* Honeypot veld tegen bots */}
                        <div style={{ display: 'none' }} aria-hidden="true">
                            <label htmlFor="meld-modal-website">Laat dit veld leeg</label>
                            <input
                                id="meld-modal-website"
                                type="text"
                                tabIndex={-1}
                                autoComplete="off"
                                value={website}
                                onChange={(e) => setWebsite(e.target.value)}
                            />
                        </div>

                        {/* Foutmelding */}
                        {status === 'error' && (
                            <div role="alert" style={{ color: 'var(--color-error, #dc2626)', fontSize: '0.85rem' }}>
                                {foutmelding}
                            </div>
                        )}

                        {/* Knoppen */}
                        <div
                            style={{
                                display: 'flex',
                                justifyContent: 'flex-end',
                                gap: '0.75rem',
                                marginTop: '0.5rem',
                            }}
                        >
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={onClose}
                                disabled={isSubmitting}
                            >
                                Annuleren
                            </button>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={isSubmitting || !onderwerp.trim() || !toelichting.trim()}
                            >
                                {isSubmitting ? 'Versturen...' : 'Versturen'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
};
