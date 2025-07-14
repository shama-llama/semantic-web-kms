import { render, screen } from '@testing-library/react';
import { LandingPage } from '../landing-page';
import { OrganizationProvider } from '../organization-provider';
import { describe, it, expect } from 'vitest';

describe('LandingPage', () => {
  const renderWithProvider = () =>
    render(
      <OrganizationProvider>
        <LandingPage />
      </OrganizationProvider>
    );

  it('renders the main heading', () => {
    renderWithProvider();
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toBeInTheDocument();
  });

  it('renders at least one knowledge graph section', () => {
    renderWithProvider();
    const matches = screen.getAllByText(/knowledge graph/i);
    expect(matches.length).toBeGreaterThan(0);
  });
}); 