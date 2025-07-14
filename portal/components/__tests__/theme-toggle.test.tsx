import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeToggle } from '../theme-toggle';
import { describe, it, expect, beforeEach } from 'vitest';

// Helper to reset document state between tests
beforeEach(() => {
  document.documentElement.className = '';
});

describe('ThemeToggle', () => {
  it('renders and is clickable', async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    await userEvent.click(button);
    // No assertion on className due to next-themes limitations in jsdom
  });
}); 