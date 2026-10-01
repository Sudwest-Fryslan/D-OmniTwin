import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { authAPI } from './services/api';

describe('App', () => {
  it('toont de inlogpagina als er geen sessie is', async () => {
    vi.spyOn(authAPI, 'getMe').mockRejectedValue(new Error('geen sessie'));
    window.history.pushState({}, '', '/admin/');

    render(<App />);

    expect(await screen.findByRole('button', { name: 'Aanmelden' })).toBeInTheDocument();
    expect(screen.getByLabelText('Gebruikersnaam')).toBeInTheDocument();
    expect(window.location.pathname).toBe('/admin/login');
  });
});
