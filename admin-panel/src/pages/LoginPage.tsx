import React, { useEffect, useState } from 'react';
import { useAdminStore } from '../hooks/useAdminStore';
import { authAPI, oidcInlogUrl } from '../services/api';
import type { AuthUser } from '../services/api';
import Beeldmerk from '../components/Beeldmerk';
import { User, KeyRound, Loader2, LogIn, AlertTriangle } from 'lucide-react';

// ?fout= van de backend na een mislukte Keycloak-login (routers/auth.py, oidc_login.py)
const FOUTEN: Record<string, string> = {
    'geweigerd': 'Inloggen bij Keycloak is afgebroken.',
    'onvolledig': 'Inloggen bij Keycloak is niet afgerond. Probeer het opnieuw.',
    'state': 'Inloggen is niet gelukt (ongeldige terugkoppeling). Probeer het opnieuw.',
    'sessie-verlopen': 'Het inloggen duurde te lang. Probeer het opnieuw.',
    'code-geweigerd': 'Keycloak heeft het inloggen geweigerd. Probeer het opnieuw.',
    'token-ongeldig': 'Het antwoord van Keycloak is niet geldig. Neem contact op met de beheerder.',
    'provider-onbereikbaar': 'Keycloak is niet bereikbaar. Probeer het later opnieuw.',
    'oidc-uit': 'Inloggen via Keycloak staat niet aan.',
};

export const LoginPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(() => {
        const fout = new URLSearchParams(window.location.search).get('fout');
        return fout ? (FOUTEN[fout] || 'Inloggen is niet gelukt.') : '';
    });
    const [loading, setLoading] = useState(false);
    // Ingelogd (bijv. via Keycloak) maar zonder beheerrechten
    const [zonderRechten, setZonderRechten] = useState<AuthUser | null>(null);
    const { setAuthenticated, authConfig } = useAdminStore();

    useEffect(() => {
        authAPI.getMe().then((me) => {
            if (me.data.authenticated && me.data.user && !me.data.user.is_admin) {
                setZonderRechten(me.data.user);
            }
        }).catch(() => { /* niet ingelogd */ });
    }, []);

    const uitloggen = async () => {
        try {
            const res = await authAPI.logout();
            if (res.data.uitlog_url) {
                window.location.assign(res.data.uitlog_url);
                return;
            }
        } catch (e) {
            console.error(e);
        }
        setZonderRechten(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            await authAPI.login(formData);

            // De browser heeft nu het HttpOnly-cookie; rol ophalen bij de backend
            const me = await authAPI.getMe();
            if (!me.data.authenticated || !me.data.user?.is_admin) {
                await authAPI.logout();
                setError('Dit account heeft geen beheerrechten.');
                return;
            }
            setAuthenticated(true, me.data.user);
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
                    <Beeldmerk size={56} />
                    <h1>D-OmniTwin</h1>
                    <p style={{ color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>
                        Beheerscherm
                    </p>
                </div>

                {zonderRechten && (
                    <div className="login-melding login-melding-waarschuwing" role="status">
                        <p>
                            Je bent ingelogd als <strong>{zonderRechten.username}</strong>, maar je hebt geen
                            beheerrechten (rol <code>beheerder</code>). Vraag een beheerder om je die rol te geven.
                        </p>
                        <button type="button" className="btn btn-secondary" style={{ marginTop: '0.75rem' }} onClick={uitloggen}>
                            Uitloggen
                        </button>
                    </div>
                )}

                {error && (
                    <div className="login-melding login-melding-fout" role="alert">
                        {error}
                    </div>
                )}

                {authConfig.oidc && (
                    <a
                        className="btn btn-primary"
                        style={{ width: '100%', justifyContent: 'center', textDecoration: 'none' }}
                        href={oidcInlogUrl()}
                    >
                        <LogIn size={18} aria-hidden="true" />
                        Inloggen met Keycloak
                    </a>
                )}

                {authConfig.lokaal && authConfig.oidc && (
                    <>
                        <div className="login-scheiding">Noodtoegang: lokaal account</div>
                        <div className="login-melding login-melding-waarschuwing" role="note">
                            <AlertTriangle size={16} aria-hidden="true" style={{ verticalAlign: 'text-bottom', marginRight: '0.375rem' }} />
                            Lokaal inloggen staat aan als noodtoegang (<code>LOKAAL_INLOGGEN=true</code>).
                            Gebruik dit alleen als Keycloak niet werkt, en zet het daarna weer uit.
                        </div>
                    </>
                )}

                {authConfig.lokaal && (
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

                    <button
                        type="submit"
                        className={authConfig.oidc ? 'btn btn-secondary' : 'btn btn-primary'}
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
                )}

                <p style={{
                    textAlign: 'center',
                    marginTop: '1.5rem',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-secondary)'
                }}>
                    Beveiligde d-OmniTwin Omgeving
                </p>
            </div>
        </div>
    );
};
