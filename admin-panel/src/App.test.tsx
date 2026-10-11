import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { authAPI } from './services/api';
import type { AuthConfig } from './services/api';
import { STANDAARD_AUTH_CONFIG, useAdminStore } from './hooks/useAdminStore';

const KEYCLOAK: AuthConfig = {
  oidc: true, lokaal: false, noodtoegang: false,
  gebruikersbeheer_url: 'http://localhost/auth/admin/omnitwin/console/',
  account_url: 'http://localhost/auth/realms/omnitwin/account',
};

function metConfig(config: AuthConfig | Error) {
  const spy = vi.spyOn(authAPI, 'getConfig');
  if (config instanceof Error) spy.mockRejectedValue(config);
  else spy.mockResolvedValue({ data: config } as never);
}

describe('App', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    useAdminStore.setState({ isAuthenticated: false, user: null, authConfig: STANDAARD_AUTH_CONFIG });
  });

  it('toont de inlogpagina als er geen sessie is', async () => {
    metConfig(new Error('geen backend'));
    vi.spyOn(authAPI, 'getMe').mockRejectedValue(new Error('geen sessie'));
    window.history.pushState({}, '', '/admin/');

    render(<App />);

    expect(await screen.findByRole('button', { name: 'Aanmelden' })).toBeInTheDocument();
    expect(screen.getByLabelText('Gebruikersnaam')).toBeInTheDocument();
    expect(screen.queryByText('Inloggen met Keycloak')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/admin/login');
  });

  it('met Keycloak: knop naar de OIDC-login en geen wachtwoordformulier', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({ data: { authenticated: false, user: null } } as never);
    window.history.pushState({}, '', '/admin/login');

    render(<App />);

    const knop = await screen.findByRole('link', { name: /Inloggen met Keycloak/ });
    expect(knop).toHaveAttribute('href', '/api/admin/auth/oidc/login?terug=%2Fadmin%2Fdashboard');
    expect(screen.queryByLabelText('Gebruikersnaam')).not.toBeInTheDocument();
  });

  it('noodtoegang: Keycloak én lokaal, met waarschuwing', async () => {
    metConfig({ ...KEYCLOAK, lokaal: true, noodtoegang: true });
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({ data: { authenticated: false, user: null } } as never);
    window.history.pushState({}, '', '/admin/login');

    render(<App />);

    expect(await screen.findByRole('link', { name: /Inloggen met Keycloak/ })).toBeInTheDocument();
    expect(screen.getByLabelText('Gebruikersnaam')).toBeInTheDocument();
    expect(screen.getByText(/Lokaal inloggen staat aan als noodtoegang/)).toBeInTheDocument();
  });

  it('meldt een mislukte Keycloak-login', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({ data: { authenticated: false, user: null } } as never);
    window.history.pushState({}, '', '/admin/login?fout=geweigerd');

    render(<App />);

    expect(await screen.findByRole('alert')).toHaveTextContent('Inloggen bij Keycloak is afgebroken.');
  });

  it('ingelogd via Keycloak zonder rol beheerder: melding en uitloggen', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({
      data: { authenticated: true, user: { id: 's', username: 'lezer1', is_admin: false, bron: 'oidc' } },
    } as never);
    window.history.pushState({}, '', '/admin/login');

    render(<App />);

    expect(await screen.findByText(/geen\s+beheerrechten/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Uitloggen' })).toBeInTheDocument();
  });

  it('demo-omgeving: demobalk, ook op de inlogpagina (#245)', async () => {
    metConfig({ ...KEYCLOAK, demo: true });
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({ data: { authenticated: false, user: null } } as never);
    window.history.pushState({}, '', '/admin/login');

    render(<App />);

    expect(await screen.findByText(/Demo-omgeving — standaardwachtwoorden, niet voor productie/)).toBeInTheDocument();
  });

  it('geen demobalk buiten de demo-omgeving', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({ data: { authenticated: false, user: null } } as never);
    window.history.pushState({}, '', '/admin/login');

    render(<App />);

    await screen.findByRole('link', { name: /Inloggen met Keycloak/ });
    expect(screen.queryByText(/Demo-omgeving/)).not.toBeInTheDocument();
  });

  it('beheerder via Keycloak: link naar gebruikers en rollen in Keycloak', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({
      data: { authenticated: true, user: { id: 's', username: 'beheer1', is_admin: true, bron: 'oidc' } },
    } as never);
    window.history.pushState({}, '', '/admin/llm');

    render(<App />);

    (await screen.findByRole('button', { name: /beheer1/ })).click();
    const link = await screen.findByRole('link', { name: /Gebruikers en rollen beheren/ });
    expect(link).toHaveAttribute('href', KEYCLOAK.gebruikersbeheer_url);
    expect(screen.queryByText(/Profiel & Wachtwoord/)).not.toBeInTheDocument();
  });

  it('standalone rapportage: toont terugknop en nooit de beheer-zijbalk (#290)', async () => {
    metConfig(new Error('geen backend'));
    vi.spyOn(authAPI, 'getMe').mockRejectedValue(new Error('geen sessie'));
    window.history.pushState({}, '', '/rapport/benchmark');

    render(<App />);

    expect(await screen.findByRole('link', { name: /Terug naar kaart/ })).toBeInTheDocument();
    expect(screen.queryByText('Beheerscherm')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Indicatoren' })).not.toBeInTheDocument();
  });

  it('standalone rapportage: toont ook geen beheer-zijbalk als beheerder is ingelogd (#290)', async () => {
    metConfig(KEYCLOAK);
    vi.spyOn(authAPI, 'getMe').mockResolvedValue({
      data: { authenticated: true, user: { id: 's', username: 'beheer1', is_admin: true, bron: 'oidc' } },
    } as never);
    window.history.pushState({}, '', '/rapport/benchmark');

    render(<App />);

    expect(await screen.findByRole('link', { name: /Terug naar kaart/ })).toBeInTheDocument();
    expect(screen.queryByText('Beheerscherm')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Indicatoren' })).not.toBeInTheDocument();
  });
});

