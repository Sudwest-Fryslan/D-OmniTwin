import React, { useState } from 'react';
import { useAdminStore } from '../hooks/useAdminStore';
import { authAPI } from '../services/api';
import { User, KeyRound, Loader2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { setAuthenticated } = useAdminStore();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await authAPI.login(formData);

            // Login success, update global state
            // The HttpOnly cookie is automatically set by the browser here
            setAuthenticated(true, {
                id: response.data.user.id,
                username: response.data.user.username,
                is_admin: true
            });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Inloggen mislukt. Controleer gegevens.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container">
            <div className="login-card card">
                <div className="login-logo">
                    <h1>D-OmniTwin</h1>
                    <p style={{ color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>
                        Beheerscherm
                    </p>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="login-username">Gebruikersnaam</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                id="login-username"
                                type="text"
                                className="form-input"
                                autoComplete="username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Gebruikersnaam"
                                required
                                style={{ paddingLeft: '2.5rem' }}
                            />
                            <User
                                aria-hidden="true"
                                size={18}
                                style={{
                                    position: 'absolute',
                                    left: '0.75rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--color-text-muted)'
                                }}
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label" htmlFor="login-password">Wachtwoord</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                id="login-password"
                                type="password"
                                className="form-input"
                                autoComplete="current-password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Wachtwoord"
                                required
                                style={{ paddingLeft: '2.5rem' }}
                            />
                            <KeyRound
                                aria-hidden="true"
                                size={18}
                                style={{
                                    position: 'absolute',
                                    left: '0.75rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--color-text-muted)'
                                }}
                            />
                        </div>
                    </div>

                    {error && (
                        <div style={{
                            color: 'var(--color-error)',
                            fontSize: '0.875rem',
                            marginBottom: '1rem'
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary"
                        style={{ width: '100%', justifyContent: 'center' }}
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <Loader2 size={18} className="spin" />
                                Inloggen...
                            </>
                        ) : (
                            'Aanmelden'
                        )}
                    </button>
                </form>

                <p style={{
                    textAlign: 'center',
                    marginTop: '1.5rem',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)'
                }}>
                    Beveiligde d-OmniTwin Omgeving
                </p>
            </div>
        </div>
    );
};
