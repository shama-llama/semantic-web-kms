import { cn } from '../utils';
import { describe, it, expect } from 'vitest';

describe('cn', () => {
  it('merges class names and filters falsy values', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
    expect(cn('foo', 'foo', 'bar')).toBe('foo foo bar');
    expect(cn('foo', false && 'bar', undefined, 'baz')).toBe('foo baz');
    expect(cn('foo', null, '', 'bar')).toBe('foo bar');
  });
}); 