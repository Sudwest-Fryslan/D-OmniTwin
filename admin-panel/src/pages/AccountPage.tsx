import React, { useState } from 'react';
import { User, Lock, ArrowRight, Loader2, CheckCircle } from 'lucide-react';
import { useAdminStore } from '../hooks/useAdminStore';
import { authAPI } from '../services/api';

export const AccountPage: React.FC = () => {
    const { user } = useAdminStore();
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (newPassword !== confirmPassword) {
            setStatus('error');
            setMessage('Nieuwe wachtwoorden komen niet overeen.');
            return;
        }

        if (newPassword.length < 6) {
            setStatus('error');
            setMessage('Wachtwoord moet minimaal 6 tekens bevatten.');
            return;
        }

        setStatus('loading');
        setMessage('');

        try {
            const res = await authAPI.changePassword({ old_password: oldPassword, new_password: newPassword });
            setStatus('success');
            setMessage(res.data.message || 'Wachtwoord succesvol gewijzigd!');
            setOldPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (err: any) {
            setStatus('error');
            setMessage(err.response?.data?.detail || 'Er is een fout opgetreden bij het wijzigen van het wachtwoord.');
        }
    };

    return (
        <div className="account-container">
            <div className="card" style={{ maxWidth: '500px', margin: '0 auto', marginTop: '2rem' }}>
                <div className="card-header" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div style={{ background: 'var(--color-primary-transparent)', padding: '0.5rem', borderRadius: '50%' }}>
                        <User size={24} color="var(--color-primary)" />
                    </div>
                    <div>
                        <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Mijn Account</h2>
                        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', margin: 0 }}>
                            Beheer je inloggegevens
                        </p>
                    </div>
                </div>

                <div style={{ marginBottom: '2rem', padding: '1rem', background: 'var(--color-bg-secondary)', borderRadius: '0.5rem' }}>
                    <strong>Ingelogd als:</strong> {user?.username} <br />
                    <span style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
                        Rol: {user?.is_admin ? 'Beheerder' : 'Gebruiker'}
                    </span>
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Lock size={18} /> Wachtwoord Wijzigen
                </h3>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="account-huidig-wachtwoord" className="form-label">Huidig wachtwoord</label>
                        <input id="account-huidig-wachtwoord"
                            type="password"
                            className="form-input"
                            value={oldPassword}
                            onChange={(e) => setOldPassword(e.target.value)}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="account-nieuw-wachtwoord" className="form-label">Nieuw wachtwoord</label>
                        <input id="account-nieuw-wachtwoord"
                            type="password"
                            className="form-input"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            minLength={6}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="account-bevestig-nieuw-wachtwoord" className="form-label">Bevestig nieuw wachtwoord</label>
                        <input id="account-bevestig-nieuw-wachtwoord"
                            type="password"
                            className="form-input"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            minLength={6}
                            required
                        />
                    </div>

                    {status === 'error' && (
                        <div style={{ color: 'var(--color-error)', fontSize: '0.875rem', marginBottom: '1rem', padding: '0.5rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.25rem' }}>
                            {message}
                        </div>
                    )}

                    {status === 'success' && (
                        <div style={{ color: 'var(--color-success)', fontSize: '0.875rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '0.25rem' }}>
                            <CheckCircle size={16} /> {message}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ width: '100%', justifyContent: 'center', marginTop: '1rem' }}
                        disabled={status === 'loading'}
                    >
                        {status === 'loading' ? (
                            <><Loader2 size={18} className="spin" /> Opslaan...</>
                        ) : (
                            <>Wijzigingen Opslaan <ArrowRight size={18} /></>
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
};
