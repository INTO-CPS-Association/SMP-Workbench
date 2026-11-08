// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TransitionInspector, DIST_SHORT } from '../src/pages/TransitionInspector';
import type { ChosenDistribution } from '../src/pages/TransitionInspector';

afterEach(cleanup);

function openInspector(sojournTimes = [2, 5, 10, 20], initial: ChosenDistribution | null = null) {
  const onSave = vi.fn();
  const onClose = vi.fn();
  const view = render(
    <TransitionInspector fromLabel="Idle" toLabel="Running" sojournTimes={sojournTimes}
      initial={initial} probability={0.75} onSave={onSave} onClose={onClose} />,
  );
  return { ...view, onSave, onClose };
}

function chooseUniform() {
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'uniform' } });
}

function setBound(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe('Uniform transition distributions', () => {
  it('offers Uniform and estimates its bounds from the observed times', () => {
    const { onSave, onClose } = openInspector();
    chooseUniform();
    expect((screen.getByLabelText('Min (s)') as HTMLInputElement).value).toBe('2');
    expect((screen.getByLabelText('Max (s)') as HTMLInputElement).value).toBe('20');
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith({
      distribution: { name: 'uniform', params: { min: 2, max: 20 } }, probability: 0.75,
    });
    expect(onClose).toHaveBeenCalledOnce();
    expect(DIST_SHORT.uniform).toBe('Uniform');
  });

  it.each([
    { times: [], min: 0, max: 1 },
    { times: [5], min: 5, max: 6 },
    { times: [5, 5, 5], min: 5, max: 6 },
    { times: [0, 0], min: 0, max: 1 },
  ])('provides valid default bounds for $times', ({ times, min, max }) => {
    const { onSave } = openInspector(times);
    chooseUniform();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith({
      distribution: { name: 'uniform', params: { min, max } }, probability: 0.75,
    });
  });

  it('saves edited decimal bounds including a zero minimum and restores them when reopened', () => {
    const { onSave, unmount } = openInspector();
    chooseUniform();
    setBound('Min (s)', '0');
    setBound('Max (s)', '12.5');
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith({
      distribution: { name: 'uniform', params: { min: 0, max: 12.5 } }, probability: 0.75,
    });
    const saved = JSON.parse(JSON.stringify(onSave.mock.calls[0][0]));
    unmount();
    openInspector([], saved.distribution);
    expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('uniform');
    expect((screen.getByLabelText('Min (s)') as HTMLInputElement).value).toBe('0');
    expect((screen.getByLabelText('Max (s)') as HTMLInputElement).value).toBe('12.5');
  });

  it('previews a constant density within the bounds and zero outside, updating after edits', () => {
    const { container } = openInspector([2, 5, 10, 20]);
    chooseUniform();
    setBound('Min (s)', '5');
    setBound('Max (s)', '15');
    const points = () => container.querySelector('svg path')!.getAttribute('d')!
      .slice(2).split(' L ').map(point => point.split(',').map(Number));
    // On the 0–20 second plot, bounds 5 and 15 map to x=164 and x=400.
    expect(points()[0][1]).toBe(174);
    expect(points()[1]).toEqual([164, 174]);
    const densityY = points()[2][1];
    expect(densityY).toBeGreaterThanOrEqual(12);
    expect(densityY).toBeLessThan(174);
    expect(points()[3]).toEqual([400, densityY]);
    expect(points()[4]).toEqual([400, 174]);
    expect(points()[5][1]).toBe(174);
    setBound('Max (s)', '10');
    expect(points()[3][0]).toBe(282);
    expect(points()[4]).toEqual([282, 174]);
    setBound('Max (s)', '5.01');
    expect(points()[3][0]).toBeGreaterThan(points()[2][0]);
    expect(points()[3][1]).toBe(points()[2][1]);
  });

  it.each([
    ['2', '2'], ['3', '2'], ['-1', '2'], ['', '2'], ['0', ''], ['0', '1e999'],
  ])('blocks invalid bounds min=%s, max=%s until corrected', (min, max) => {
    const { onSave, onClose } = openInspector();
    chooseUniform();
    setBound('Min (s)', min);
    setBound('Max (s)', max);
    expect(screen.getByRole('alert').textContent).toContain('maximum greater than the minimum');
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    setBound('Min (s)', '0');
    setBound('Max (s)', '3');
    expect(screen.queryByRole('alert')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it('does not save changes when cancelled', () => {
    const { onSave, onClose } = openInspector();
    chooseUniform();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('still saves existing distribution types after switching away from invalid Uniform bounds', () => {
    const { onSave } = openInspector([2, 4, 6]);
    chooseUniform();
    setBound('Max (s)', '0');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'normal' } });
    expect(screen.queryByRole('alert')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onSave).toHaveBeenCalledWith({
      distribution: { name: 'normal', params: { mean: 4, std: 2 } }, probability: 0.75,
    });
  });
});
