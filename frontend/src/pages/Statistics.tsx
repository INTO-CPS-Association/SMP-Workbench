import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Edge, Node } from '@xyflow/react';
import styles from './Statistics.module.css';
import { store } from '../store';
import type { QuarantinedEntry, SuspiciousFile, SuspiciousTransition, NormalFile } from '../api/analysis';
import { analyzeSojournOutliers } from '../api/analysis';
import ThemeToggle from '../components/ThemeToggle';

interface EdgeData {
  probability?: number;
  avgSojournTime?: number;
  transitionCount?: number;
  cleanSojournTimes?: number[];
}

interface EffectiveStat {
  avg: number;
  probability: number;
  count: number;
  recalibrated: boolean;
}

interface DotData {
  value: number;
  color: 'blue' | 'orange' | 'red';
  onClick?: () => void;
  large?: boolean;
}

const DOT_FILL = { blue: '#3b82f6', orange: '#f59e0b', red: '#ef4444' } as const;

function computeEffectiveStats(
  edges: Edge[],
  quarantined: QuarantinedEntry[],
  included: Set<number>,
  includedFilePairs: Set<string>,
  fileOutlierData: Map<string, SuspiciousTransition[]>,
  includedFileEntries: Set<string>,
  excludedClean: Map<string, Set<number>>,
  normalFiles: NormalFile[],
  excludedNormalFiles: Set<string>,
): Map<string, EffectiveStat> {
  const sojournByEdge = new Map<string, number[]>();

  if (excludedNormalFiles.size > 0 && normalFiles.length > 0) {
    // Rebuild from per-file data, omitting excluded files entirely.
    // excludedClean indices are no longer valid in the rebuilt array, so they are skipped.
    for (const edge of edges) sojournByEdge.set(edge.id, []);
    for (const nf of normalFiles) {
      if (excludedNormalFiles.has(nf.filename)) continue;
      for (const [edgeId, times] of Object.entries(nf.edgeTimes)) {
        const arr = sojournByEdge.get(edgeId);
        if (arr) arr.push(...times);
      }
    }
  } else {
    // Normal path: use pre-aggregated cleanSojournTimes with per-dot exclusions.
    for (const edge of edges) {
      const allTimes = ((edge.data as EdgeData)?.cleanSojournTimes) ?? [];
      const excl = excludedClean.get(edge.id) ?? new Set<number>();
      sojournByEdge.set(edge.id, allTimes.filter((_, idx) => !excl.has(idx)));
    }
  }

  const anyIncluded = included.size > 0 || includedFilePairs.size > 0 ||
    excludedClean.size > 0 || excludedNormalFiles.size > 0;

  for (const [i, q] of quarantined.entries()) {
    if (!included.has(i)) continue;
    const times = sojournByEdge.get(`${q.fromState}-${q.toState}`);
    if (times) times.push(q.sojournTime);
  }

  // Only merge transitions whose (filename, from, to) pair is individually selected.
  for (const [filename, transitions] of fileOutlierData) {
    for (const [tIdx, t] of transitions.entries()) {
      const pairKey = `${filename}::${t.fromState}::${t.toState}`;
      if (!includedFilePairs.has(pairKey)) continue;
      if (t.isOutlier && !includedFileEntries.has(`${pairKey}::${tIdx}`)) continue;
      const times = sojournByEdge.get(`${t.fromState}-${t.toState}`);
      if (times !== undefined) times.push(t.sojournTime);
    }
  }

  const sourceTotals = new Map<string, number>();
  for (const edge of edges) {
    const times = sojournByEdge.get(edge.id) ?? [];
    sourceTotals.set(edge.source, (sourceTotals.get(edge.source) ?? 0) + times.length);
  }

  const result = new Map<string, EffectiveStat>();
  for (const edge of edges) {
    const times = sojournByEdge.get(edge.id) ?? [];
    const avg = times.length ? times.reduce((a, b) => a + b, 0) / times.length : 0;
    const sourceTotal = sourceTotals.get(edge.source) ?? 1;
    const probability = sourceTotal > 0 ? times.length / sourceTotal : 0;
    const baseData = (edge.data as EdgeData) ?? {};
    const recalibrated = anyIncluded && (
      times.length !== (baseData.transitionCount ?? 0) ||
      Math.abs(avg - (baseData.avgSojournTime ?? 0)) > 0.001
    );
    result.set(edge.id, { avg, probability, count: times.length, recalibrated });
  }
  return result;
}

function DotPlot({ dots, avg, unit = '', precision = 2 }: {
  dots: DotData[];
  avg: number;
  unit?: string;
  precision?: number;
}) {
  const W = 460, H = 44, PAD = 20;
  if (!dots.length) return null;
  const allVals = dots.map(d => d.value);
  const lo = Math.min(...allVals);
  const hi = Math.max(...allVals);
  const range = hi - lo || 1;
  const cx = (v: number) => PAD + ((v - lo) / range) * (W - 2 * PAD);
  const cy = H / 2;
  const layerOrder: Record<string, number> = { blue: 0, orange: 1, red: 2 };
  const sorted = [...dots].sort((a, b) => (layerOrder[a.color] ?? 0) - (layerOrder[b.color] ?? 0));
  const current = dots.find(d => d.color === 'red');
  return (
    <div className={styles.dotPlotWrap}>
      <div className={styles.dotPlotRight}>
        <div className={styles.dotPlotMeta}>
          <span className={styles.dotPlotAvg}>avg: {avg.toFixed(precision)}{unit}</span>
          {current && <span className={styles.dotPlotAvg}>outlier: {current.value.toFixed(precision)}{unit}</span>}
        </div>
        <svg width={W} height={H} className={styles.dotPlotSvg}>
          <line x1={PAD} y1={cy} x2={W - PAD} y2={cy} stroke="currentColor" strokeOpacity={0.2} strokeWidth={1} />
          <text x={PAD} y={cy - 10} fontSize={9} fill="currentColor" fillOpacity={0.45} textAnchor="middle">{lo.toFixed(precision)}</text>
          <text x={W - PAD} y={cy - 10} fontSize={9} fill="currentColor" fillOpacity={0.45} textAnchor="middle">{hi.toFixed(precision)}</text>
          {sorted.map((d, idx) => (
            <circle
              key={idx}
              cx={cx(d.value)}
              cy={cy}
              r={d.color === 'red' || d.large ? 5.5 : 4}
              fill={DOT_FILL[d.color]}
              opacity={d.color === 'red' ? 1 : 0.7}
              style={{ cursor: d.onClick ? 'pointer' : 'default' }}
              onClick={d.onClick}
            />
          ))}
        </svg>
      </div>
    </div>
  );
}

export default function Statistics() {
  const location = useLocation();
  const navigate = useNavigate();
  const { nodes, edges } = (location.state as { nodes: Node[]; edges: Edge[] }) ?? {};
  const quarantined = store.getQuarantinedEntries();
  const suspiciousFiles = store.getSuspiciousFiles();
  const normalFiles = store.getNormalFiles();

  const handleReset = () => {
    store.reset();
    navigate('/');
  };

  const [included, setIncluded] = useState<Set<number>>(new Set());
  // Keys: "filename::fromState::toState" — one per suspicious transition pair
  const [includedFilePairs, setIncludedFilePairs] = useState<Set<string>>(new Set());
  const [loadingFiles, setLoadingFiles] = useState<Set<string>>(new Set());
  const [fileOutlierData, setFileOutlierData] = useState<Map<string, SuspiciousTransition[]>>(new Map());
  // Keys: "filename::fromState::toState::transitionIndex"
  const [includedFileEntries, setIncludedFileEntries] = useState<Set<string>>(new Set());
  const [expandedQuarantined, setExpandedQuarantined] = useState<Set<number>>(new Set());
  const [expandedSuspicious, setExpandedSuspicious] = useState<Set<string>>(new Set());
  // Filenames of normal (non-suspicious) files manually flagged for exclusion via dot click
  const [manuallyExcludedNormalFiles, setManuallyExcludedNormalFiles] = useState<Set<string>>(new Set());

  const toggleEntry = (idx: number) => {
    setIncluded(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  const scoreFile = async (filename: string) => {
    setLoadingFiles(prev => new Set(prev).add(filename));
    const sf = suspiciousFiles.find((f: SuspiciousFile) => f.filename === filename);
    try {
      const scored = sf ? await analyzeSojournOutliers(sf.transitions, store.getOutlierMethod()) : [];
      setFileOutlierData(prev => new Map(prev).set(filename, scored));
    } catch {
      setFileOutlierData(prev => new Map(prev).set(filename, sf?.transitions ?? []));
    } finally {
      setLoadingFiles(prev => { const n = new Set(prev); n.delete(filename); return n; });
    }
  };

  const toggleFilePair = (filename: string, fromState: string, toState: string) => {
    const pairKey = `${filename}::${fromState}::${toState}`;
    if (includedFilePairs.has(pairKey)) {
      setIncludedFilePairs(prev => { const n = new Set(prev); n.delete(pairKey); return n; });
      setIncludedFileEntries(prev => {
        const n = new Set(prev);
        for (const k of [...n]) if (k.startsWith(`${pairKey}::`)) n.delete(k);
        return n;
      });
      const remainingPairs = [...includedFilePairs].filter(k => k !== pairKey && k.startsWith(`${filename}::`));
      if (remainingPairs.length === 0) {
        setFileOutlierData(prev => { const n = new Map(prev); n.delete(filename); return n; });
      }
    } else {
      setIncludedFilePairs(prev => new Set(prev).add(pairKey));
      if (!fileOutlierData.has(filename) && !loadingFiles.has(filename)) {
        scoreFile(filename);
      }
    }
  };

  const toggleFileEntry = (pairKey: string, idx: number) => {
    const key = `${pairKey}::${idx}`;
    setIncludedFileEntries(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const uniqueSuspiciousFilenames = useMemo(
    () => [...new Set(suspiciousFiles.map((sf: SuspiciousFile) => sf.filename))],
    [suspiciousFiles],
  );

  const sortedSuspiciousFiles = useMemo(
    () => [...suspiciousFiles].sort((a: SuspiciousFile, b: SuspiciousFile) => a.filename.localeCompare(b.filename)),
    [suspiciousFiles],
  );

  const allPairsSelected = sortedSuspiciousFiles.length > 0 &&
    sortedSuspiciousFiles.every((sf: SuspiciousFile) =>
      includedFilePairs.has(`${sf.filename}::${sf.fromState}::${sf.toState}`) || loadingFiles.has(sf.filename)
    );

  const toggleAllPairs = () => {
    if (allPairsSelected) {
      setIncludedFilePairs(new Set());
      setFileOutlierData(new Map());
      setIncludedFileEntries(new Set());
      setLoadingFiles(new Set());
    } else {
      setIncludedFilePairs(prev => {
        const n = new Set(prev);
        sortedSuspiciousFiles.forEach((sf: SuspiciousFile) => n.add(`${sf.filename}::${sf.fromState}::${sf.toState}`));
        return n;
      });
      const unscored = [...new Set(
        sortedSuspiciousFiles
          .filter((sf: SuspiciousFile) => !fileOutlierData.has(sf.filename) && !loadingFiles.has(sf.filename))
          .map((sf: SuspiciousFile) => sf.filename)
      )];
      unscored.forEach(scoreFile);
    }
  };

  const allSelected = quarantined.length > 0 && included.size === quarantined.length;
  const toggleAll = () => {
    setIncluded(allSelected ? new Set() : new Set(quarantined.map((_, i) => i)));
  };

  const reIncludedFileOutliers = useMemo(() => {
    const result: Array<{ filename: string; pairKey: string; transitionIdx: number } & SuspiciousTransition> = [];
    for (const [filename, transitions] of fileOutlierData) {
      transitions.forEach((t, idx) => {
        const pairKey = `${filename}::${t.fromState}::${t.toState}`;
        if (!t.isOutlier || !includedFilePairs.has(pairKey)) return;
        result.push({ filename, pairKey, transitionIdx: idx, ...t });
      });
    }
    return result;
  }, [fileOutlierData, includedFilePairs]);

  const allFileEntriesSelected = reIncludedFileOutliers.length > 0 &&
    reIncludedFileOutliers.every(o => includedFileEntries.has(`${o.pairKey}::${o.transitionIdx}`));
  const toggleAllFileEntries = () => {
    if (allFileEntriesSelected) {
      setIncludedFileEntries(new Set());
    } else {
      setIncludedFileEntries(new Set(reIncludedFileOutliers.map(o => `${o.pairKey}::${o.transitionIdx}`)));
    }
  };

  const edgeDetailsByPair = useMemo(() => {
    const map = new Map<string, { times: number[]; avg: number }>();
    for (const edge of edges ?? []) {
      const times = ((edge.data as EdgeData)?.cleanSojournTimes) ?? [];
      const avg = (edge.data as EdgeData)?.avgSojournTime ?? 0;
      map.set(edge.id, { times, avg });
    }
    return map;
  }, [edges]);

  const [excludedClean, setExcludedClean] = useState<Map<string, Set<number>>>(new Map());

  const edgeSourceTarget = useMemo(() => {
    const map = new Map<string, { source: string; target: string }>();
    for (const edge of edges ?? []) map.set(edge.id, { source: edge.source, target: edge.target });
    return map;
  }, [edges]);

  const toggleManualExcludeFile = (filename: string) => {
    // excludedClean indices reference the original cleanSojournTimes array;
    // when files are added/removed the rebuilt array has different indices, so reset it.
    setExcludedClean(new Map());
    setManuallyExcludedNormalFiles(prev => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename); else next.add(filename);
      return next;
    });
  };

  const toggleCleanEntry = (edgeId: string, idx: number) => {
    setExcludedClean(prev => {
      const next = new Map(prev);
      const set = new Set(next.get(edgeId) ?? []);
      if (set.has(idx)) set.delete(idx); else set.add(idx);
      if (set.size === 0) next.delete(edgeId); else next.set(edgeId, set);
      return next;
    });
  };

  const manuallyExcluded = useMemo(() => {
    const result: Array<{ edgeId: string; idx: number; source: string; target: string; sojournTime: number }> = [];
    for (const [edgeId, indices] of excludedClean) {
      const edgeData = edgeDetailsByPair.get(edgeId);
      const edgeST = edgeSourceTarget.get(edgeId);
      if (!edgeData || !edgeST) continue;
      for (const idx of indices) {
        if (idx < edgeData.times.length) {
          result.push({ edgeId, idx, source: edgeST.source, target: edgeST.target, sojournTime: edgeData.times[idx] });
        }
      }
    }
    return result;
  }, [excludedClean, edgeDetailsByPair, edgeSourceTarget]);

  const effectiveStats = useMemo(
    () => (edges
      ? computeEffectiveStats(edges, quarantined, included, includedFilePairs, fileOutlierData, includedFileEntries, excludedClean, normalFiles, manuallyExcludedNormalFiles)
      : new Map<string, EffectiveStat>()),
    [included, includedFilePairs, fileOutlierData, includedFileEntries, edges, quarantined, excludedClean, normalFiles, manuallyExcludedNormalFiles],
  );

  if (!edges || edges.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Statistics</h1>
          <div className={styles.headerActions}>
            <ThemeToggle />
            <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
            <button className={`${styles.navBtn} ${styles.resetBtn}`} onClick={handleReset}>New Analysis</button>
          </div>
        </div>
        <p className={styles.empty}>No transition data available. Run an analysis first.</p>
      </div>
    );
  }

  const nodeLabel: Record<string, string> = {};
  (nodes ?? []).forEach((n) => {
    nodeLabel[n.id] = (n.data?.label as string) ?? n.id;
  });

  const grouped: Record<string, Edge[]> = {};
  edges.forEach((e) => {
    if (!grouped[e.source]) grouped[e.source] = [];
    grouped[e.source].push(e);
  });
  const fromStates = Object.keys(grouped).sort();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Transition Statistics</h1>
        <div className={styles.headerActions}>
          <ThemeToggle />
          <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
          <button className={`${styles.navBtn} ${styles.resetBtn}`} onClick={handleReset}>New Analysis</button>
        </div>
      </div>

      {suspiciousFiles.length > 0 && (
        <div className={styles.suspiciousSection}>
          <div className={styles.quarantineHeader}>
            <div>
              <h2 className={styles.suspiciousTitle}>Quarantined Files</h2>
              <p className={styles.suspiciousDesc}>
                {uniqueSuspiciousFilenames.length === 1 ? '1 file was' : `${uniqueSuspiciousFilenames.length} files were`} quarantined
                for containing an anomalously high number of a particular transition.
                Check individual transitions to re-include them — statistics update automatically.
              </p>
            </div>
            <button className={styles.selectAllBtn} onClick={toggleAllPairs}>
              {allPairsSelected ? 'Deselect all' : 'Select all'}
            </button>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th className={styles.checkTh}></th>
                  <th>File</th>
                  <th>Transition</th>
                  <th>Count</th>
                  <th>Expected (avg)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedSuspiciousFiles.map((sf: SuspiciousFile, i: number) => {
                  const isFirstInGroup = i === 0 || sortedSuspiciousFiles[i - 1].filename !== sf.filename;
                  const isLoading = loadingFiles.has(sf.filename);
                  const pairKey = `${sf.filename}::${sf.fromState}::${sf.toState}`;
                  const isIncluded = includedFilePairs.has(pairKey);
                  return (
                    <>
                    <tr
                      key={i}
                      className={[
                        isIncluded ? styles.includedRow : '',
                        !isFirstInGroup ? styles.fileGroupContinuation : '',
                      ].filter(Boolean).join(' ') || undefined}
                      onClick={() => !isLoading && toggleFilePair(sf.filename, sf.fromState, sf.toState)}
                      style={{ cursor: isLoading ? 'wait' : 'pointer' }}
                    >
                      <td className={styles.checkTd}>
                        <input
                          type="checkbox"
                          checked={isIncluded}
                          disabled={isLoading}
                          onChange={() => toggleFilePair(sf.filename, sf.fromState, sf.toState)}
                          onClick={(e) => e.stopPropagation()}
                          className={styles.checkbox}
                        />
                      </td>
                      <td className={styles.suspiciousFilename}>
                        {isFirstInGroup && (
                          <>
                            {sf.filename}
                            {isLoading && <span className={styles.loadingBadge}>scoring…</span>}
                          </>
                        )}
                      </td>
                      <td>{sf.fromState} → {sf.toState}</td>
                      <td className={styles.suspiciousCount}>{sf.count}</td>
                      <td>{sf.avgCount.toFixed(1)}</td>
                      <td>
                        <button
                          className={styles.detailsBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedSuspicious(prev => {
                              const n = new Set(prev);
                              n.has(pairKey) ? n.delete(pairKey) : n.add(pairKey);
                              return n;
                            });
                          }}
                        >
                          {expandedSuspicious.has(pairKey) ? 'Hide Details' : 'Details'}
                        </button>
                      </td>
                    </tr>
                    {expandedSuspicious.has(pairKey) && (() => {
                      // Other suspicious files for the same transition pair (not this file)
                      const otherSusp = sortedSuspiciousFiles.filter(
                        (other: SuspiciousFile) =>
                          other.filename !== sf.filename &&
                          other.fromState === sf.fromState &&
                          other.toState === sf.toState,
                      );
                      // Map count value → list of suspicious files sharing that count
                      const otherCountMap = new Map<number, SuspiciousFile[]>();
                      for (const other of otherSusp) {
                        const arr = otherCountMap.get(other.count) ?? [];
                        arr.push(other);
                        otherCountMap.set(other.count, arr);
                      }
                      let currentMarked = false;
                      const usedIdx = new Map<number, number>();
                      const dots: DotData[] = (sf.allCounts ?? []).map((c, dotIdx) => {
                        const dotFilename: string | undefined = (sf.allFilenames ?? [])[dotIdx];
                        if (c === sf.count && !currentMarked) {
                          currentMarked = true;
                          return { value: c, color: includedFilePairs.has(pairKey) ? 'blue' : 'red', onClick: () => toggleFilePair(sf.filename, sf.fromState, sf.toState), large: true };
                        }
                        if (otherCountMap.has(c)) {
                          const candidates = otherCountMap.get(c)!;
                          const idx = usedIdx.get(c) ?? 0;
                          const other = candidates[idx % candidates.length];
                          usedIdx.set(c, idx + 1);
                          const otherKey = `${other.filename}::${other.fromState}::${other.toState}`;
                          const isReIncluded = includedFilePairs.has(otherKey);
                          return {
                            value: c,
                            color: isReIncluded ? 'blue' as const : 'orange' as const,
                            onClick: () => toggleFilePair(other.filename, other.fromState, other.toState),
                          };
                        }
                        // Normal file dot — clickable to manually flag for exclusion
                        const isExcluded = dotFilename ? manuallyExcludedNormalFiles.has(dotFilename) : false;
                        return {
                          value: c,
                          color: isExcluded ? 'orange' as const : 'blue' as const,
                          onClick: dotFilename ? () => toggleManualExcludeFile(dotFilename) : undefined,
                        };
                      });
                      return (
                        <tr key={`detail-sf-${i}`} className={styles.detailRow}>
                          <td colSpan={6}>
                            <DotPlot dots={dots} avg={sf.avgCount} precision={0} />
                          </td>
                        </tr>
                      );
                    })()}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className={styles.tableWrapper}>
        <table>
          <thead>
            <tr>
              <th>From State</th>
              <th>To State</th>
              <th>Probability</th>
              <th>Avg. Sojourn Time (s)</th>
              <th>Based on (transitions)</th>
            </tr>
          </thead>
          <tbody>
            {fromStates.map((fromId) =>
              grouped[fromId]
                .sort((a, b) => a.target.localeCompare(b.target))
                .map((edge, i) => {
                  const eff = effectiveStats.get(edge.id);
                  const prob = eff?.probability ?? ((edge.data as EdgeData)?.probability ?? 0);
                  const avg = eff?.avg ?? ((edge.data as EdgeData)?.avgSojournTime ?? 0);
                  const count = eff?.count ?? ((edge.data as EdgeData)?.transitionCount ?? 0);
                  return (
                    <tr key={edge.id} className={i === 0 ? styles.fromGroup : undefined}>
                      <td>
                        {i === 0 ? (
                          <span className={styles.pill}>{nodeLabel[fromId] ?? fromId}</span>
                        ) : null}
                      </td>
                      <td>{nodeLabel[edge.target] ?? edge.target}</td>
                      <td>
                        {(prob * 100).toFixed(2)}%
                        {eff?.recalibrated && <span className={styles.recalibBadge}>recalibrated</span>}
                      </td>
                      <td>{avg.toFixed(2)}</td>
                      <td>{count}</td>
                    </tr>
                  );
                })
            )}
          </tbody>
        </table>
      </div>

      {quarantined.length > 0 && (
        <div className={styles.quarantineSection}>
          <div className={styles.quarantineHeader}>
            <div>
              <h2 className={styles.quarantineTitle}>Quarantined Log Entries</h2>
              <p className={styles.quarantineDesc}>
                {quarantined.length} {quarantined.length === 1 ? 'entry was' : 'entries were'} flagged as
                outliers and excluded from the statistics above. Check entries to re-include them —
                values update automatically.
              </p>
            </div>
            <button className={styles.selectAllBtn} onClick={toggleAll}>
              {allSelected ? 'Deselect all' : 'Select all'}
            </button>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th className={styles.checkTh}></th>
                  <th>From State</th>
                  <th>To State</th>
                  <th>Sojourn Time (s)</th>
                  <th>Outlier Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {quarantined.map((q, i) => {
                  const edgeKey = `${q.fromState}-${q.toState}`;
                  const edgeDetail = edgeDetailsByPair.get(edgeKey);
                  return (
                  <>
                  <tr
                    key={i}
                    className={included.has(i) ? styles.includedRow : undefined}
                    onClick={() => toggleEntry(i)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td className={styles.checkTd}>
                      <input
                        type="checkbox"
                        checked={included.has(i)}
                        onChange={() => toggleEntry(i)}
                        onClick={(e) => e.stopPropagation()}
                        className={styles.checkbox}
                      />
                    </td>
                    <td>{nodeLabel[q.fromState] ?? q.fromState}</td>
                    <td>{nodeLabel[q.toState] ?? q.toState}</td>
                    <td>{q.sojournTime.toFixed(2)}</td>
                    <td>
                      <div className={styles.scoreCell}>
                        <div className={styles.scoreBar}>
                          <div
                            className={styles.scoreFill}
                            style={{ width: `${q.outlierScore * 100}%` }}
                          />
                        </div>
                        <span className={styles.scoreNum}>{q.outlierScore.toFixed(2)}</span>
                      </div>
                    </td>
                    <td>
                      <button
                        className={styles.detailsBtn}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedQuarantined(prev => {
                            const n = new Set(prev);
                            n.has(i) ? n.delete(i) : n.add(i);
                            return n;
                          });
                        }}
                      >
                        {expandedQuarantined.has(i) ? 'Hide Details' : 'Details'}
                      </button>
                    </td>
                  </tr>
                  {expandedQuarantined.has(i) && edgeDetail && (() => {
                    const excl = excludedClean.get(edgeKey) ?? new Set<number>();
                    const dots: DotData[] = [
                      ...edgeDetail.times.map((v, idx) => ({
                        value: v,
                        color: excl.has(idx) ? 'orange' as const : 'blue' as const,
                        onClick: () => toggleCleanEntry(edgeKey, idx),
                      })),
                      ...quarantined
                        .map((oq, oi) => ({ oq, oi }))
                        .filter(({ oq, oi }) => oi !== i && oq.fromState === q.fromState && oq.toState === q.toState)
                        .map(({ oq, oi }) => ({
                          value: oq.sojournTime,
                          color: included.has(oi) ? 'blue' as const : 'orange' as const,
                          onClick: () => toggleEntry(oi),
                        })),
                      { value: q.sojournTime, color: included.has(i) ? 'blue' : 'red', onClick: () => toggleEntry(i), large: true },
                    ];
                    return (
                      <tr key={`detail-q-${i}`} className={styles.detailRow}>
                        <td colSpan={6}>
                          <DotPlot dots={dots} avg={edgeDetail.avg} unit="s" />
                        </td>
                      </tr>
                    );
                  })()}
                  </>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {manuallyExcluded.length > 0 && (
        <div className={styles.quarantineSection}>
          <div className={styles.quarantineHeader}>
            <div>
              <h2 className={styles.quarantineTitle}>Manually Excluded Clean Entries</h2>
              <p className={styles.quarantineDesc}>
                {manuallyExcluded.length} {manuallyExcluded.length === 1 ? 'entry was' : 'entries were'} manually
                excluded from statistics. Click an entry to re-include it.
              </p>
            </div>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>From State</th>
                  <th>To State</th>
                  <th>Sojourn Time (s)</th>
                </tr>
              </thead>
              <tbody>
                {manuallyExcluded.map((e, i) => (
                  <tr
                    key={i}
                    onClick={() => toggleCleanEntry(e.edgeId, e.idx)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>{nodeLabel[e.source] ?? e.source}</td>
                    <td>{nodeLabel[e.target] ?? e.target}</td>
                    <td>{e.sojournTime.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {manuallyExcludedNormalFiles.size > 0 && (
        <div className={styles.quarantineSection}>
          <div className={styles.quarantineHeader}>
            <div>
              <h2 className={styles.quarantineTitle}>Manually Flagged Files</h2>
              <p className={styles.quarantineDesc}>
                {manuallyExcludedNormalFiles.size}{' '}
                {manuallyExcludedNormalFiles.size === 1 ? 'file was' : 'files were'} manually excluded
                from the distribution plot. Statistics update automatically. Click a row to re-include it.
              </p>
            </div>
            <button
              className={styles.selectAllBtn}
              onClick={() => setManuallyExcludedNormalFiles(new Set())}
            >
              Clear all
            </button>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                </tr>
              </thead>
              <tbody>
                {[...manuallyExcludedNormalFiles].sort().map(fn => (
                  <tr
                    key={fn}
                    onClick={() => toggleManualExcludeFile(fn)}
                    style={{ cursor: 'pointer' }}
                    className={styles.includedRow}
                  >
                    <td>{fn}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {reIncludedFileOutliers.length > 0 && (
        <div className={styles.fileOutliersSection}>
          <div className={styles.quarantineHeader}>
            <div>
              <h2 className={styles.quarantineTitle}>Outliers in Re-included Transitions</h2>
              <p className={styles.quarantineDesc}>
                {reIncludedFileOutliers.length} {reIncludedFileOutliers.length === 1 ? 'entry was' : 'entries were'} flagged
                as sojourn time outliers within the re-included transitions and excluded from the statistics above.
                Check entries to include them — values update automatically.
              </p>
            </div>
            <button className={styles.selectAllBtn} onClick={toggleAllFileEntries}>
              {allFileEntriesSelected ? 'Deselect all' : 'Select all'}
            </button>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th className={styles.checkTh}></th>
                  <th>File</th>
                  <th>From State</th>
                  <th>To State</th>
                  <th>Sojourn Time (s)</th>
                  <th>Outlier Score</th>
                </tr>
              </thead>
              <tbody>
                {reIncludedFileOutliers.map((o, i) => {
                  const key = `${o.pairKey}::${o.transitionIdx}`;
                  const isIncluded = includedFileEntries.has(key);
                  return (
                    <tr
                      key={i}
                      className={isIncluded ? styles.includedRow : undefined}
                      onClick={() => toggleFileEntry(o.pairKey, o.transitionIdx)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className={styles.checkTd}>
                        <input
                          type="checkbox"
                          checked={isIncluded}
                          onChange={() => toggleFileEntry(o.pairKey, o.transitionIdx)}
                          onClick={(e) => e.stopPropagation()}
                          className={styles.checkbox}
                        />
                      </td>
                      <td className={styles.suspiciousFilename}>{o.filename}</td>
                      <td>{nodeLabel[o.fromState] ?? o.fromState}</td>
                      <td>{nodeLabel[o.toState] ?? o.toState}</td>
                      <td>{o.sojournTime.toFixed(2)}</td>
                      <td>
                        <div className={styles.scoreCell}>
                          <div className={styles.scoreBar}>
                            <div className={styles.scoreFill} style={{ width: `${o.outlierScore * 100}%` }} />
                          </div>
                          <span className={styles.scoreNum}>{o.outlierScore.toFixed(2)}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
