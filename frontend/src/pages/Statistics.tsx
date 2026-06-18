import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
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
  color: 'blue' | 'orange' | 'red' | 'green';
  onClick?: () => void;
  large?: boolean;
}

const DOT_FILL = { blue: '#3b82f6', orange: '#f59e0b', red: '#ef4444', green: '#22c55e' } as const;

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
  const layerOrder: Record<string, number> = { blue: 0, orange: 1, green: 2, red: 3 };
  const sorted = [...dots].sort((a, b) => (layerOrder[a.color] ?? 0) - (layerOrder[b.color] ?? 0));
  return (
    <div className={styles.dotPlotWrap}>
      <div className={styles.dotPlotRight}>
        <div className={styles.dotPlotMeta}>
          <span className={styles.dotPlotAvg}>avg: {avg.toFixed(precision)}{unit}</span>
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
              r={d.color === 'red' || d.color === 'green' || d.large ? 5.5 : 4}
              fill={DOT_FILL[d.color]}
              opacity={d.color === 'red' || d.color === 'green' ? 1 : 0.7}
              style={{ cursor: d.onClick ? 'pointer' : 'default' }}
              onClick={d.onClick}
            >
              <title>{d.value.toFixed(precision)}{unit}</title>
            </circle>
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
  const [expandedQuarantinedFiles, setExpandedQuarantinedFiles] = useState<Set<string>>(new Set());
  const [expandedFilesSection, setExpandedFilesSection] = useState(false);
  const [expandedLogSection, setExpandedLogSection] = useState(false);
  // Filenames of normal (non-suspicious) files manually flagged for exclusion via dot click
  const [manuallyExcludedNormalFiles, setManuallyExcludedNormalFiles] = useState<Set<string>>(new Set());

  const filesSectionRef = useRef<HTMLDivElement>(null);
  const logSectionRef = useRef<HTMLDivElement>(null);
  const fileCardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const scrollToTop = () => document.getElementById('stats-page-top')?.scrollIntoView({ behavior: 'smooth' });
  const closeFilesSection = () => { setExpandedFilesSection(false); filesSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const closeLogSection   = () => { setExpandedLogSection(false);   logSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const closeFileCard = (name: string) => {
    setExpandedQuarantinedFiles(prev => { const n = new Set(prev); n.delete(name); return n; });
    fileCardRefs.current.get(name)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

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
      const scored = sf ? await analyzeSojournOutliers(sf.transitions) : [];
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

  const sortedSuspiciousFiles = useMemo(
    () => [...suspiciousFiles].sort((a: SuspiciousFile, b: SuspiciousFile) => a.filename.localeCompare(b.filename)),
    [suspiciousFiles],
  );

  // Groups all sojourn-time records by filename → (fromState::toState) → sojourn times.
  // flaggedPairs tracks which (from::to) keys triggered the file exclusion.
  const filesByName = useMemo(() => {
    const map = new Map<string, {
      flaggedPairs: Map<string, SuspiciousFile>;
      pairTimes: Map<string, number[]>;
    }>();
    for (const sf of sortedSuspiciousFiles) {
      if (!map.has(sf.filename)) {
        const pairTimes = new Map<string, number[]>();
        for (const t of sf.transitions) {
          const k = `${t.fromState}::${t.toState}`;
          const arr = pairTimes.get(k);
          if (arr) arr.push(t.sojournTime);
          else pairTimes.set(k, [t.sojournTime]);
        }
        map.set(sf.filename, { flaggedPairs: new Map(), pairTimes });
      }
      const entry = map.get(sf.filename)!;
      const flaggedKey = `${sf.fromState}::${sf.toState}`;
      entry.flaggedPairs.set(flaggedKey, sf);
      // Ensure the flagged pair appears even when sf.transitions is empty
      if (!entry.pairTimes.has(flaggedKey)) entry.pairTimes.set(flaggedKey, []);
    }
    return map;
  }, [sortedSuspiciousFiles]);

  const sortedFilenames = useMemo(() => [...filesByName.keys()].sort(), [filesByName]);

  const quarantinedByPair = useMemo(() => {
    const map = new Map<string, { fromState: string; toState: string; indices: number[] }>();
    quarantined.forEach((q, i) => {
      const key = `${q.fromState}-${q.toState}`;
      if (!map.has(key)) map.set(key, { fromState: q.fromState, toState: q.toState, indices: [] });
      map.get(key)!.indices.push(i);
    });
    return map;
  }, [quarantined]);

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

  const fileOutliersByEdgeKey = useMemo(() => {
    const map = new Map<string, Array<{ pairKey: string; transitionIdx: number; sojournTime: number; fromState: string; toState: string }>>();
    for (const o of reIncludedFileOutliers) {
      const edgeKey = `${o.fromState}-${o.toState}`;
      const arr = map.get(edgeKey) ?? [];
      arr.push({ pairKey: o.pairKey, transitionIdx: o.transitionIdx, sojournTime: o.sojournTime, fromState: o.fromState, toState: o.toState });
      map.set(edgeKey, arr);
    }
    return map;
  }, [reIncludedFileOutliers]);

  const allOutlierEdgeKeys = useMemo(() => {
    const keys = new Set([...quarantinedByPair.keys(), ...fileOutliersByEdgeKey.keys()]);
    return [...keys];
  }, [quarantinedByPair, fileOutliersByEdgeKey]);

  const allSelected = useMemo(() =>
    allOutlierEdgeKeys.length > 0 && allOutlierEdgeKeys.every(edgeKey => {
      const pd = quarantinedByPair.get(edgeKey);
      const fo = fileOutliersByEdgeKey.get(edgeKey) ?? [];
      return (!pd || pd.indices.every(i => included.has(i))) &&
        fo.every(o => includedFileEntries.has(`${o.pairKey}::${o.transitionIdx}`));
    }),
  [allOutlierEdgeKeys, quarantinedByPair, fileOutliersByEdgeKey, included, includedFileEntries]);

  const toggleAll = () => {
    if (allSelected) {
      setIncluded(new Set());
      setIncludedFileEntries(prev => {
        const next = new Set(prev);
        for (const o of reIncludedFileOutliers) next.delete(`${o.pairKey}::${o.transitionIdx}`);
        return next;
      });
    } else {
      setIncluded(new Set(quarantined.map((_, i) => i)));
      setIncludedFileEntries(prev => {
        const next = new Set(prev);
        for (const o of reIncludedFileOutliers) next.add(`${o.pairKey}::${o.transitionIdx}`);
        return next;
      });
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

  const skipFirstSave = useRef(true);

  // Restore UI state saved before navigating away
  useEffect(() => {
    const saved = store.getStatsUIState();
    if (saved) {
      setIncluded(new Set(saved.included));
      setIncludedFilePairs(new Set(saved.includedFilePairs));
      setFileOutlierData(new Map(saved.fileOutlierData));
      setIncludedFileEntries(new Set(saved.includedFileEntries));
      setExcludedClean(new Map(saved.excludedClean));
      setManuallyExcludedNormalFiles(new Set(saved.manuallyExcludedNormalFiles));
    }
  }, []);

  // Persist UI state on every relevant change.
  // Skip the first firing (mount) because it runs with the empty initial state,
  // before the restore effect's setState calls have propagated.
  useEffect(() => {
    if (skipFirstSave.current) { skipFirstSave.current = false; return; }
    store.setStatsUIState({ included, includedFilePairs, fileOutlierData, includedFileEntries, excludedClean, manuallyExcludedNormalFiles });
  }, [included, includedFilePairs, fileOutlierData, includedFileEntries, excludedClean, manuallyExcludedNormalFiles]);

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
    <div id="stats-page-top" className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Transition Statistics</h1>
        <div className={styles.headerActions}>
          <ThemeToggle />
          <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
          <button className={`${styles.navBtn} ${styles.resetBtn}`} onClick={handleReset}>New Analysis</button>
        </div>
      </div>

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

      {sortedFilenames.length > 0 && (
        <div ref={filesSectionRef} className={styles.sectionDropdown}>
          <div
            className={`${styles.sectionDropdownHeader} ${!expandedFilesSection ? styles.sectionDropdownCollapsed : ''}`}
            onClick={() => setExpandedFilesSection(p => !p)}
          >
            <h2>Quarantined Files</h2>
            <span className={styles.sectionDropdownCount}>{sortedFilenames.length} {sortedFilenames.length === 1 ? 'file' : 'files'}</span>
            <span className={styles.fileBlockChevron}>{expandedFilesSection ? '▼' : '▶'}</span>
          </div>
          {expandedFilesSection && (
            <div className={styles.sectionDropdownBody}>
              <p className={styles.sectionDropdownDesc}>
                {sortedFilenames.length === 1 ? '1 file was' : `${sortedFilenames.length} files were`} excluded
                for having an anomalously high transition count. All transitions from each file are listed —
                the transition that triggered exclusion is highlighted. Check a transition to re-include its data.
              </p>

          {sortedFilenames.map(filename => {
            const fileData = filesByName.get(filename)!;
            const isLoading = loadingFiles.has(filename);
            const isExpanded = expandedQuarantinedFiles.has(filename);
            const isModified = [...includedFilePairs].some(k => k.startsWith(`${filename}::`));
            const sortedPairs = [...fileData.pairTimes.entries()].sort(([a], [b]) => a.localeCompare(b));
            const nonFlaggedPairs = sortedPairs.filter(([pairKey]) => !fileData.flaggedPairs.has(pairKey));
            const allNonFlaggedIncluded = nonFlaggedPairs.length > 0 && nonFlaggedPairs.every(([pairKey]) => {
              const sep = pairKey.indexOf('::');
              return includedFilePairs.has(`${filename}::${pairKey.slice(0, sep)}::${pairKey.slice(sep + 2)}`);
            });
            const toggleNonFlagged = (e: React.MouseEvent) => {
              e.stopPropagation();
              const keys = nonFlaggedPairs.map(([pairKey]) => {
                const sep = pairKey.indexOf('::');
                return `${filename}::${pairKey.slice(0, sep)}::${pairKey.slice(sep + 2)}`;
              });
              if (allNonFlaggedIncluded) {
                const next = new Set(includedFilePairs);
                keys.forEach(k => next.delete(k));
                setIncludedFilePairs(next);
                const nextEntries = new Set(includedFileEntries);
                for (const k of keys) for (const ek of [...nextEntries]) if (ek.startsWith(`${k}::`)) nextEntries.delete(ek);
                setIncludedFileEntries(nextEntries);
                if (![...next].some(k => k.startsWith(`${filename}::`)))
                  setFileOutlierData(prev => { const n = new Map(prev); n.delete(filename); return n; });
              } else {
                const next = new Set(includedFilePairs);
                keys.forEach(k => next.add(k));
                setIncludedFilePairs(next);
                if (!fileOutlierData.has(filename) && !loadingFiles.has(filename)) scoreFile(filename);
              }
            };
            const toggleFileExpand = () => setExpandedQuarantinedFiles(prev => {
              const n = new Set(prev);
              n.has(filename) ? n.delete(filename) : n.add(filename);
              return n;
            });

            return (
              <div key={filename} className={styles.fileBlock} ref={el => { if (el) fileCardRefs.current.set(filename, el); else fileCardRefs.current.delete(filename); }}>
                <div
                  className={`${styles.fileBlockHeader} ${!isExpanded ? styles.fileBlockHeaderCollapsed : ''}`}
                  onClick={toggleFileExpand}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  <span className={styles.suspiciousFilename}>{filename}</span>
                  {isLoading && <span className={styles.loadingBadge}>scoring…</span>}
                  {isModified && !isLoading && <span className={styles.modifiedBadge}>modified</span>}
                  <span className={styles.fileBlockChevron}>{isExpanded ? '▼' : '▶'}</span>
                </div>
                {isExpanded && <>
                <div className={styles.tableWrapper}>
                  <table>
                    {nonFlaggedPairs.length > 0 && (
                      <thead>
                        <tr>
                          <th colSpan={3} className={styles.selectBarCell}>
                            <button className={styles.selectNonFlaggedBtn} onClick={toggleNonFlagged}>
                              {allNonFlaggedIncluded ? 'Deselect non-flagged' : 'Include non-flagged'}
                            </button>
                          </th>
                        </tr>
                      </thead>
                    )}
                    <tbody>
                      {sortedPairs.map(([pairKey, pairTimes]) => {
                        const sep = pairKey.indexOf('::');
                        const fromState = pairKey.slice(0, sep);
                        const toState = pairKey.slice(sep + 2);
                        const fullPairKey = `${filename}::${fromState}::${toState}`;
                        const isIncluded = includedFilePairs.has(fullPairKey);
                        const isFlagged = fileData.flaggedPairs.has(pairKey);
                        const sfInfo = fileData.flaggedPairs.get(pairKey);
                        return (
                          <Fragment key={pairKey}>
                            <tr
                              className={
                                isIncluded ? styles.includedRow
                                : isFlagged ? styles.flaggedRow
                                : undefined
                              }
                              onClick={() => !isLoading && toggleFilePair(filename, fromState, toState)}
                              style={{ cursor: isLoading ? 'wait' : 'pointer' }}
                            >
                              <td className={styles.checkTd}>
                                <input
                                  type="checkbox"
                                  checked={isIncluded}
                                  disabled={isLoading}
                                  onChange={() => toggleFilePair(filename, fromState, toState)}
                                  onClick={(e) => e.stopPropagation()}
                                  className={styles.checkbox}
                                />
                              </td>
                              <td>{fromState} → {toState}</td>
                              <td>
                                {isFlagged && sfInfo && (
                                  <span className={styles.causeBadge}>
                                    cause · {sfInfo.count} vs avg {sfInfo.avgCount.toFixed(1)}
                                  </span>
                                )}
                              </td>
                            </tr>
                            {(() => {
                              if (isFlagged && sfInfo) {
                                // Count distribution — shows how many times each file has this transition
                                const otherSusp = sortedSuspiciousFiles.filter(
                                  (other: SuspiciousFile) =>
                                    other.filename !== filename &&
                                    other.fromState === fromState &&
                                    other.toState === toState,
                                );
                                const otherCountMap = new Map<number, SuspiciousFile[]>();
                                for (const other of otherSusp) {
                                  const arr = otherCountMap.get(other.count) ?? [];
                                  arr.push(other);
                                  otherCountMap.set(other.count, arr);
                                }
                                let currentMarked = false;
                                const usedIdx = new Map<number, number>();
                                const dots: DotData[] = (sfInfo.allCounts ?? []).map((c, dotIdx) => {
                                  const dotFilename: string | undefined = (sfInfo.allFilenames ?? [])[dotIdx];
                                  if (c === sfInfo.count && !currentMarked) {
                                    currentMarked = true;
                                    return { value: c, color: isIncluded ? 'green' as const : 'red' as const, onClick: () => toggleFilePair(filename, fromState, toState), large: true };
                                  }
                                  if (otherCountMap.has(c)) {
                                    const candidates = otherCountMap.get(c)!;
                                    const idx = usedIdx.get(c) ?? 0;
                                    const other = candidates[idx % candidates.length];
                                    usedIdx.set(c, idx + 1);
                                    const otherKey = `${other.filename}::${other.fromState}::${other.toState}`;
                                    return {
                                      value: c,
                                      color: includedFilePairs.has(otherKey) ? 'green' as const : 'orange' as const,
                                      onClick: () => toggleFilePair(other.filename, other.fromState, other.toState),
                                    };
                                  }
                                  const isExcluded = dotFilename ? manuallyExcludedNormalFiles.has(dotFilename) : false;
                                  return {
                                    value: c,
                                    color: isExcluded ? 'orange' as const : 'blue' as const,
                                    onClick: dotFilename ? () => toggleManualExcludeFile(dotFilename) : undefined,
                                  };
                                });
                                return dots.length > 0 ? (
                                  <tr className={styles.detailRow}>
                                    <td colSpan={3}>
                                      <DotPlot dots={dots} avg={sfInfo.avgCount} precision={0} />
                                    </td>
                                  </tr>
                                ) : null;
                              }

                              // Sojourn time distribution for non-flagged transitions
                              const edgeId = `${fromState}-${toState}`;
                              const edgeDetail = edgeDetailsByPair.get(edgeId);
                              const cleanTimes = edgeDetail?.times ?? [];
                              const cleanAvg = edgeDetail?.avg ?? 0;
                              const excl = excludedClean.get(edgeId) ?? new Set<number>();
                              const dots: DotData[] = [
                                ...cleanTimes.map((v, idx) => ({
                                  value: v,
                                  color: excl.has(idx) ? 'orange' as const : 'blue' as const,
                                  onClick: () => toggleCleanEntry(edgeId, idx),
                                })),
                                ...pairTimes.map(v => ({
                                  value: v,
                                  color: isIncluded ? 'green' as const : 'red' as const,
                                  onClick: () => toggleFilePair(filename, fromState, toState),
                                })),
                              ];
                              const avg = cleanTimes.length > 0
                                ? cleanAvg
                                : pairTimes.length > 0
                                  ? pairTimes.reduce((a, b) => a + b, 0) / pairTimes.length
                                  : 0;
                              return dots.length > 0 ? (
                                <tr className={styles.detailRow}>
                                  <td colSpan={3}>
                                    <DotPlot dots={dots} avg={avg} unit="s" />
                                  </td>
                                </tr>
                              ) : null;
                            })()}
                          </Fragment>
                        );
                      })}
                    </tbody>
                    {nonFlaggedPairs.length > 0 && (
                      <tfoot>
                        <tr>
                          <td colSpan={3} className={styles.selectBarCell}>
                            <button className={styles.selectNonFlaggedBtn} onClick={toggleNonFlagged}>
                              {allNonFlaggedIncluded ? 'Deselect non-flagged' : 'Include non-flagged'}
                            </button>
                          </td>
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>
                <div className={styles.fileBlockFooter}>
                  <button className={styles.sectionCloseBtn} onClick={() => closeFileCard(filename)}>
                    Close ▲
                  </button>
                </div>
                </>}
              </div>
            );
          })}

              <div className={styles.sectionDropdownFooter}>
                <button className={styles.sectionCloseBtn} onClick={closeFilesSection}>Close ▲</button>
                <button className={styles.backToTopBtn} onClick={scrollToTop}>↑ Back to top</button>
              </div>
            </div>
          )}
        </div>
      )}

      {allOutlierEdgeKeys.length > 0 && (
        <div ref={logSectionRef} className={styles.sectionDropdown}>
          <div
            className={`${styles.sectionDropdownHeader} ${!expandedLogSection ? styles.sectionDropdownCollapsed : ''}`}
            onClick={() => setExpandedLogSection(p => !p)}
          >
            <h2>Quarantined Log Entries</h2>
            <span className={styles.sectionDropdownCount}>
              {quarantined.length + reIncludedFileOutliers.length} {quarantined.length + reIncludedFileOutliers.length === 1 ? 'entry' : 'entries'}
            </span>
            <span className={styles.fileBlockChevron}>{expandedLogSection ? '▼' : '▶'}</span>
          </div>
          {expandedLogSection && (
            <div className={styles.sectionDropdownBody}>
              <div className={styles.sectionLogHeader}>
                <p className={styles.sectionDropdownDesc}>
                  {quarantined.length + reIncludedFileOutliers.length}{' '}
                  {quarantined.length + reIncludedFileOutliers.length === 1 ? 'entry' : 'entries'} excluded
                  across {allOutlierEdgeKeys.length}{' '}
                  {allOutlierEdgeKeys.length === 1 ? 'transition' : 'transitions'}.
                  Click a row to include all outliers for that transition, or click individual dots.
                </p>
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
                  <th>Outliers</th>
                </tr>
              </thead>
              <tbody>
                {allOutlierEdgeKeys.map(edgeKey => {
                  const pairData = quarantinedByPair.get(edgeKey);
                  const fileOuts = fileOutliersByEdgeKey.get(edgeKey) ?? [];
                  const edgeDetail = edgeDetailsByPair.get(edgeKey);
                  const fromState = pairData?.fromState ?? fileOuts[0]?.fromState ?? '';
                  const toState = pairData?.toState ?? fileOuts[0]?.toState ?? '';
                  const totalCount = (pairData?.indices.length ?? 0) + fileOuts.length;
                  const allQuarantinedOk = !pairData || pairData.indices.every(i => included.has(i));
                  const allFileOutsOk = fileOuts.every(o => includedFileEntries.has(`${o.pairKey}::${o.transitionIdx}`));
                  const allPairIncluded = totalCount > 0 && allQuarantinedOk && allFileOutsOk;

                  const togglePair = () => {
                    if (pairData) {
                      setIncluded(prev => {
                        const next = new Set(prev);
                        if (allPairIncluded) pairData.indices.forEach(i => next.delete(i));
                        else pairData.indices.forEach(i => next.add(i));
                        return next;
                      });
                    }
                    if (fileOuts.length > 0) {
                      setIncludedFileEntries(prev => {
                        const next = new Set(prev);
                        if (allPairIncluded) fileOuts.forEach(o => next.delete(`${o.pairKey}::${o.transitionIdx}`));
                        else fileOuts.forEach(o => next.add(`${o.pairKey}::${o.transitionIdx}`));
                        return next;
                      });
                    }
                  };

                  const excl = excludedClean.get(edgeKey) ?? new Set<number>();
                  const dots: DotData[] = [
                    ...(edgeDetail?.times ?? []).map((v, idx) => ({
                      value: v,
                      color: excl.has(idx) ? 'orange' as const : 'blue' as const,
                      onClick: () => toggleCleanEntry(edgeKey, idx),
                    })),
                    ...(pairData?.indices ?? []).map(i => ({
                      value: quarantined[i].sojournTime,
                      color: included.has(i) ? 'green' as const : 'red' as const,
                      onClick: () => toggleEntry(i),
                      large: true,
                    })),
                    ...fileOuts.map(o => ({
                      value: o.sojournTime,
                      color: includedFileEntries.has(`${o.pairKey}::${o.transitionIdx}`) ? 'green' as const : 'red' as const,
                      onClick: () => toggleFileEntry(o.pairKey, o.transitionIdx),
                      large: true,
                    })),
                  ];

                  return (
                    <Fragment key={edgeKey}>
                      <tr
                        className={allPairIncluded ? styles.includedRow : undefined}
                        onClick={togglePair}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className={styles.checkTd}>
                          <input
                            type="checkbox"
                            checked={allPairIncluded}
                            onChange={togglePair}
                            onClick={(e) => e.stopPropagation()}
                            className={styles.checkbox}
                          />
                        </td>
                        <td>{nodeLabel[fromState] ?? fromState}</td>
                        <td>{nodeLabel[toState] ?? toState}</td>
                        <td>{totalCount}</td>
                      </tr>
                      {dots.length > 0 && (
                        <tr className={styles.detailRow}>
                          <td colSpan={4}>
                            <DotPlot dots={dots} avg={edgeDetail?.avg ?? 0} unit="s" />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
              <div className={styles.sectionDropdownFooter}>
                <button className={styles.sectionCloseBtn} onClick={closeLogSection}>Close ▲</button>
                <button className={styles.backToTopBtn} onClick={scrollToTop}>↑ Back to top</button>
              </div>
            </div>
          )}
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

    </div>
  );
}
