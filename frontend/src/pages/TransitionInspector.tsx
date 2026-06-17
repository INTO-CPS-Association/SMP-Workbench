import { useState, useMemo, useEffect, useRef } from 'react';
import styles from './TransitionInspector.module.css';

export type DistName = 'exponential' | 'gamma' | 'weibull' | 'normal' | 'lognormal';

export interface ChosenDistribution {
  name: DistName;
  params: Record<string, number>;
}

export const DIST_LABELS: Record<DistName, string> = {
  exponential: 'Exponential',
  gamma:       'Gamma',
  weibull:     'Weibull',
  normal:      'Normal',
  lognormal:   'Log-normal',
};

export const DIST_SHORT: Record<string, string> = {
  exponential: 'Exp',
  gamma:       'Gamma',
  weibull:     'Weibull',
  normal:      'Normal',
  lognormal:   'Log-N',
};

const PARAM_DEFS: Record<DistName, Array<{ key: string; label: string; step: number }>> = {
  exponential: [{ key: 'rate',  label: 'Rate (λ)',   step: 0.001 }],
  gamma:       [{ key: 'shape', label: 'Shape (k)',  step: 0.01  }, { key: 'scale', label: 'Scale (θ)', step: 0.01 }],
  weibull:     [{ key: 'shape', label: 'Shape (k)',  step: 0.01  }, { key: 'scale', label: 'Scale (λ)', step: 0.01 }],
  normal:      [{ key: 'mean',  label: 'Mean (μ)',   step: 0.01  }, { key: 'std',   label: 'Std (σ)',   step: 0.01 }],
  lognormal:   [{ key: 'mu',    label: 'μ (log)',    step: 0.01  }, { key: 'sigma', label: 'σ (log)',   step: 0.001 }],
};

// --- math helpers ---

function lgamma(z: number): number {
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - lgamma(1 - z);
  const C = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  const x = z - 1, t = x + 7.5;
  let a = C[0];
  for (let i = 1; i < 9; i++) a += C[i] / (x + i);
  return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
}
const gammaFn = (x: number) => Math.exp(lgamma(x));

function pdfAt(name: DistName, p: Record<string, number>, x: number): number {
  switch (name) {
    case 'exponential': {
      const r = p.rate ?? 1;
      return x >= 0 && r > 0 ? r * Math.exp(-r * x) : 0;
    }
    case 'gamma': {
      const k = p.shape ?? 1, th = p.scale ?? 1;
      return x > 0 && k > 0 && th > 0
        ? Math.exp((k - 1) * Math.log(x) - x / th - k * Math.log(th) - lgamma(k))
        : 0;
    }
    case 'weibull': {
      const k = p.shape ?? 1, lam = p.scale ?? 1;
      return x > 0 && k > 0 && lam > 0
        ? (k / lam) * Math.pow(x / lam, k - 1) * Math.exp(-Math.pow(x / lam, k))
        : 0;
    }
    case 'normal': {
      const mu = p.mean ?? 0, s = p.std ?? 1;
      return s > 0 ? Math.exp(-0.5 * ((x - mu) / s) ** 2) / (s * Math.sqrt(2 * Math.PI)) : 0;
    }
    case 'lognormal': {
      const mu = p.mu ?? 0, s = p.sigma ?? 1;
      return x > 0 && s > 0
        ? Math.exp(-0.5 * ((Math.log(x) - mu) / s) ** 2) / (x * s * Math.sqrt(2 * Math.PI))
        : 0;
    }
  }
}

function estimateParams(name: DistName, times: number[]): Record<string, number> {
  if (!times.length) {
    const defaults: Record<DistName, Record<string, number>> = {
      exponential: { rate: 1 },
      gamma:       { shape: 2, scale: 1 },
      weibull:     { shape: 2, scale: 1 },
      normal:      { mean: 0, std: 1 },
      lognormal:   { mu: 0, sigma: 1 },
    };
    return defaults[name];
  }
  const n = times.length;
  const mean = times.reduce((a, b) => a + b, 0) / n;
  const variance = times.reduce((a, b) => a + (b - mean) ** 2, 0) / Math.max(n - 1, 1);
  switch (name) {
    case 'exponential': return { rate: mean > 0 ? 1 / mean : 1 };
    case 'gamma': return {
      shape: Math.max(variance > 0 ? mean ** 2 / variance : 1, 0.01),
      scale: Math.max(variance > 0 ? variance / mean : 1, 0.01),
    };
    case 'weibull': {
      const k = 2;
      return { shape: k, scale: Math.max(mean / gammaFn(1 + 1 / k), 0.01) };
    }
    case 'normal': return { mean, std: Math.max(Math.sqrt(variance), 0.01) };
    case 'lognormal': {
      const logs = times.filter(t => t > 0).map(t => Math.log(t));
      const lm = logs.length ? logs.reduce((a, b) => a + b, 0) / logs.length : 0;
      const lv = logs.length > 1 ? logs.reduce((a, b) => a + (b - lm) ** 2, 0) / (logs.length - 1) : 1;
      return { mu: lm, sigma: Math.max(Math.sqrt(lv), 0.01) };
    }
  }
}

// --- SVG Histogram ---

const SVG_W = 528, SVG_H = 210;
const ML = 46, MR = 10, MT = 12, MB = 36;
const PW = SVG_W - ML - MR, PH = SVG_H - MT - MB;

function makeBins(times: number[], bw: number): Array<{ lo: number; count: number; bw: number }> {
  if (!times.length || bw <= 0) return [];
  const hi = times.reduce((a, b) => (b > a ? b : a), 0);
  // effectiveBw: never finer than 1 bar per plot pixel (prevents thousands of invisible bars)
  const effectiveBw = Math.max(bw, hi / PW);
  const n = Math.max(1, Math.ceil(hi / effectiveBw));
  const bins: { lo: number; count: number; bw: number }[] = Array.from(
    { length: n },
    (_, i) => ({ lo: i * effectiveBw, count: 0, bw: effectiveBw }),
  );
  for (const t of times) {
    const idx = Math.min(Math.floor(t / effectiveBw), n - 1);
    if (idx >= 0) bins[idx].count++;
  }
  return bins;
}

function HistogramChart({
  times,
  bw,
  distName,
  distParams,
}: {
  times: number[];
  bw: number;
  distName: DistName | null;
  distParams: Record<string, number>;
}) {
  const bins = useMemo(() => makeBins(times, bw), [times, bw]);

  if (!bins.length) {
    return <div className={styles.noData}>No sojourn-time data for this transition.</div>;
  }

  const effectiveBw = bins[0].bw;
  const maxCount = Math.max(1, bins.reduce((a, b) => (b.count > a ? b.count : a), 0));
  const xMax = bins.length * effectiveBw;
  const barW = PW / bins.length;

  const xs = (t: number) => ML + (t / xMax) * PW;
  const ys = (v: number) => MT + PH - (v / maxCount) * PH;

  // Distribution overlay: sample at 200 points, scale PDF → expected counts
  let overlayD = '';
  if (distName) {
    const N = 200;
    const pts = Array.from({ length: N + 1 }, (_, i) => {
      const t = (i / N) * xMax;
      const scaled = pdfAt(distName, distParams, t) * times.length * effectiveBw;
      return `${xs(t).toFixed(1)},${ys(scaled).toFixed(1)}`;
    });
    overlayD = `M ${pts.join(' L ')}`;
  }

  // Axis ticks
  const xTickEvery = Math.max(1, Math.ceil(bins.length / 7));
  const xTicks = Array.from(
    { length: Math.ceil(bins.length / xTickEvery) + 1 },
    (_, i) => i * xTickEvery,
  ).filter(i => i <= bins.length);
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map(f => Math.round(f * maxCount));

  return (
    <svg width={SVG_W} height={SVG_H} className={styles.histSvg}>
      <defs>
        <clipPath id="hist-clip">
          <rect x={ML} y={MT} width={PW} height={PH + 1} />
        </clipPath>
      </defs>

      {/* Horizontal grid lines */}
      {yTicks.map(v => (
        <line key={v} x1={ML} y1={ys(v)} x2={ML + PW} y2={ys(v)}
          stroke="currentColor" strokeOpacity={0.07} strokeWidth={1} />
      ))}

      {/* Bars + overlay clipped to plot area */}
      <g clipPath="url(#hist-clip)">
        {bins.map((b, i) => (
          <rect key={i}
            x={xs(b.lo) + 0.5}
            y={ys(b.count)}
            width={Math.max(barW - 1, 1)}
            height={ys(0) - ys(b.count)}
            fill="var(--accent)"
            opacity={0.55}
          >
            <title>{b.lo.toFixed(1)}–{(b.lo + effectiveBw).toFixed(1)}s · {b.count}</title>
          </rect>
        ))}
        {overlayD && (
          <path d={overlayD} fill="none" stroke="#ef4444" strokeWidth={2} />
        )}
      </g>

      {/* Axes */}
      <line x1={ML} y1={MT + PH} x2={ML + PW} y2={MT + PH}
        stroke="currentColor" strokeOpacity={0.3} strokeWidth={1} />
      <line x1={ML} y1={MT} x2={ML} y2={MT + PH}
        stroke="currentColor" strokeOpacity={0.3} strokeWidth={1} />

      {/* X ticks */}
      {xTicks.map(i => {
        const t = i * bw;
        const x = xs(t);
        return (
          <g key={i}>
            <line x1={x} y1={MT + PH} x2={x} y2={MT + PH + 4}
              stroke="currentColor" strokeOpacity={0.4} strokeWidth={1} />
            <text x={x} y={MT + PH + 15} fontSize={9}
              fill="currentColor" fillOpacity={0.55} textAnchor="middle">
              {t < 10 ? t.toFixed(1) : t.toFixed(0)}
            </text>
          </g>
        );
      })}
      <text x={ML + PW / 2} y={SVG_H - 2} fontSize={10}
        fill="currentColor" fillOpacity={0.45} textAnchor="middle">
        Sojourn Time (s)
      </text>

      {/* Y ticks */}
      {yTicks.map(v => (
        <g key={v}>
          <line x1={ML - 4} y1={ys(v)} x2={ML} y2={ys(v)}
            stroke="currentColor" strokeOpacity={0.4} strokeWidth={1} />
          <text x={ML - 6} y={ys(v) + 3} fontSize={9}
            fill="currentColor" fillOpacity={0.55} textAnchor="end">
            {v}
          </text>
        </g>
      ))}
      <text
        x={10} y={MT + PH / 2} fontSize={10}
        fill="currentColor" fillOpacity={0.45} textAnchor="middle"
        transform={`rotate(-90, 10, ${MT + PH / 2})`}
      >
        Occurrences
      </text>
    </svg>
  );
}

// --- Main modal ---

export interface SaveResult {
  distribution: ChosenDistribution | null;
  probability: number;
}

interface Props {
  fromLabel: string;
  toLabel: string;
  sojournTimes: number[];
  initial: ChosenDistribution | null;
  probability: number;
  onClose: () => void;
  onSave: (result: SaveResult) => void;
}

function numToStr(v: number) { return isFinite(v) ? String(v) : ''; }
function strToNum(s: string, fallback: number) {
  const v = parseFloat(s);
  return isFinite(v) ? v : fallback;
}

export function TransitionInspector({
  fromLabel,
  toLabel,
  sojournTimes,
  initial,
  probability,
  onClose,
  onSave,
}: Props) {
  const [bw, setBw] = useState(5);
  const [bwInput, setBwInput] = useState('5');
  const [distName, setDistName] = useState<DistName | null>(initial?.name ?? null);
  // params holds the last valid numeric values (used for live overlay preview)
  const [params, setParams] = useState<Record<string, number>>(initial?.params ?? {});
  // paramInputs holds raw strings so the user can freely clear/type partial values
  const [paramInputs, setParamInputs] = useState<Record<string, string>>(
    () => Object.fromEntries(Object.entries(initial?.params ?? {}).map(([k, v]) => [k, numToStr(v)])),
  );
  const [probInput, setProbInput] = useState(numToStr(probability));

  // Close on Escape
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') closeRef.current(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  const handleDistChange = (name: DistName | '') => {
    if (!name) { setDistName(null); setParamInputs({}); return; }
    setDistName(name);
    const estimated = estimateParams(name, sojournTimes);
    setParams(estimated);
    setParamInputs(Object.fromEntries(Object.entries(estimated).map(([k, v]) => [k, numToStr(v)])));
  };

  const handleParamInput = (key: string, raw: string) => {
    setParamInputs(prev => ({ ...prev, [key]: raw }));
    // Update live overlay only when the value is a valid finite number
    const v = parseFloat(raw);
    if (isFinite(v)) setParams(prev => ({ ...prev, [key]: v }));
  };

  const handleOk = () => {
    const finalProb = strToNum(probInput, probability);
    let distribution: ChosenDistribution | null = null;
    if (distName) {
      const finalParams: Record<string, number> = {};
      for (const { key } of PARAM_DEFS[distName]) {
        finalParams[key] = strToNum(paramInputs[key] ?? '', params[key] ?? 0);
      }
      distribution = { name: distName, params: finalParams };
    }
    onSave({ distribution, probability: finalProb });
    onClose();
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>

        <div className={styles.header}>
          <span className={styles.title}>{fromLabel} → {toLabel}</span>
          <button className={styles.closeBtn} onClick={onClose}>×</button>
        </div>

        <div className={styles.histSection}>
          <HistogramChart
            times={sojournTimes}
            bw={bw}
            distName={distName}
            distParams={params}
          />
          <div className={styles.binRow}>
            <label className={styles.binLabel}>Bin width</label>
            <input
              type="number"
              className={styles.binInput}
              value={bwInput}
              min={0.1}
              step={0.1}
              onChange={e => {
                setBwInput(e.target.value);
                const v = parseFloat(e.target.value);
                if (v >= 0.1) setBw(v);
              }}
              onBlur={() => {
                const v = parseFloat(bwInput);
                if (!isFinite(v) || v < 0.1) { setBwInput('5'); setBw(5); }
                else { setBwInput(String(v)); setBw(v); }
              }}
            />
            <span className={styles.binUnit}>s</span>
          </div>
        </div>

        <div className={styles.distSection}>
          <div className={styles.distRow}>
            <label className={styles.distLabel}>Probability</label>
            <input
              type="number"
              className={styles.paramInput}
              value={probInput}
              min={0}
              max={1}
              step={0.0001}
              onChange={e => setProbInput(e.target.value)}
            />
          </div>

          <div className={styles.distRow}>
            <label className={styles.distLabel}>Distribution</label>
            <select
              className={styles.distSelect}
              value={distName ?? ''}
              onChange={e => handleDistChange(e.target.value as DistName | '')}
            >
              <option value="">None</option>
              {(Object.keys(DIST_LABELS) as DistName[]).map(d => (
                <option key={d} value={d}>{DIST_LABELS[d]}</option>
              ))}
            </select>
          </div>

          {distName && (
            <div className={styles.paramsGrid}>
              {PARAM_DEFS[distName].map(({ key, label, step }) => (
                <div key={key} className={styles.paramRow}>
                  <label className={styles.paramLabel}>{label}</label>
                  <input
                    type="number"
                    className={styles.paramInput}
                    value={paramInputs[key] ?? ''}
                    step={step}
                    onChange={e => handleParamInput(key, e.target.value)}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.okBtn} onClick={handleOk}>Save</button>
        </div>

      </div>
    </div>
  );
}
