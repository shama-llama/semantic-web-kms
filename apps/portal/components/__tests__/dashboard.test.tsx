import { render, screen } from '@testing-library/react';
import { Dashboard } from '../dashboard';
import { OrganizationProvider } from '../organization-provider';
import { describe, it, expect } from 'vitest';

describe('Dashboard', () => {
  it('renders the dashboard heading', () => {
    render(
      <OrganizationProvider>
        <Dashboard />
      </OrganizationProvider>
    );
    const heading = screen.getByRole('heading');
    expect(heading).toBeInTheDocument();
  });
}); 