import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Edge, Node } from '@xyflow/react';
import styles from './Statistics.module.css';
import { store } from '../store';
import type { QuarantinedEntry, SuspiciousFile, SuspiciousTransition } from '../api/analysis';
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

function computeEffectiveStats(
  edges: Edge[],
  quarantined: QuarantinedEntry[],
  included: Set<number>,
  includedFiles: Set<string>,
  fileOutlierData: Map<string, SuspiciousTransition[]>,
  includedFileEntries: Set<string>,
): Map<string, EffectiveStat> {
  const sojournByEdge = new Map<string, number[]>();
  for (const edge of edges) {
    const times = ((edge.data as EdgeData)?.cleanSojournTimes) ?? [];
    sojournByEdge.set(edge.id, [...times]);
  }

  const anyIncluded = included.size > 0 || includedFiles.size > 0;

  // Merge included quarantined entries
  for (const [i, q] of quarantined.entries()) {
    if (!included.has(i)) continue;
    const times = sojournByEdge.get(`${q.fromState}-${q.toState}`);
    if (times) times.push(q.sojournTime);
  }

  // Merge transitions from re-included suspicious files.
  // Sojourn-time outliers within those files are skipped unless individually checked.
  for (const [filename, transitions] of fileOutlierData) {
    if (!includedFiles.has(filename)) continue;
    for (const [tIdx, t] of transitions.entries()) {
      if (t.isOutlier && !includedFileEntries.has(`${filename}::${tIdx}`)) continue;
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

export default function Statistics() {
  const location = useLocation();
  const navigate = useNavigate();
  const { nodes, edges } = (location.state as { nodes: Node[]; edges: Edge[] }) ?? {};
  const quarantined = store.getQuarantinedEntries();
  const suspiciousFiles = store.getSuspiciousFiles();

  const [included, setIncluded] = useState<Set<number>>(new Set());
  const [includedFiles, setIncludedFiles] = useState<Set<string>>(new Set());
  const [loadingFiles, setLoadingFiles] = useState<Set<string>>(new Set());
  // Scored transitions per re-included file, populated after the backend call returns
  const [fileOutlierData, setFileOutlierData] = useState<Map<string, SuspiciousTransition[]>>(new Map());
  // "filename::transitionIndex" keys for individual outlier entries the user wants to include
  const [includedFileEntries, setIncludedFileEntries] = useState<Set<string>>(new Set());

  const toggleEntry = (idx: number) => {
    setIncluded(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  const toggleFile = async (filename: string) => {
    if (includedFiles.has(filename)) {
      setIncludedFiles(prev => { const n = new Set(prev); n.delete(filename); return n; });
      setFileOutlierData(prev => { const n = new Map(prev); n.delete(filename); return n; });
      setIncludedFileEntries(prev => {
        const n = new Set(prev);
        for (const k of [...n]) if (k.startsWith(`${filename}::`)) n.delete(k);
        return n;
      });
    } else {
      setLoadingFiles(prev => new Set(prev).add(filename));
      const sf = suspiciousFiles.find(f => f.filename === filename);
      try {
        const scored = sf ? await analyzeSojournOutliers(sf.transitions) : [];
        setFileOutlierData(prev => new Map(prev).set(filename, scored));
        setIncludedFiles(prev => new Set(prev).add(filename));
      } catch {
        // On error fall back to raw transitions without outlier scores
        setFileOutlierData(prev => new Map(prev).set(filename, sf?.transitions ?? []));
        setIncludedFiles(prev => new Set(prev).add(filename));
      } finally {
        setLoadingFiles(prev => { const n = new Set(prev); n.delete(filename); return n; });
      }
    }
  };

  const toggleFileEntry = (filename: string, idx: number) => {
    const key = `${filename}::${idx}`;
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
  const allFilesSelected = uniqueSuspiciousFilenames.length > 0 &&
    uniqueSuspiciousFilenames.every(fn => includedFiles.has(fn) || loadingFiles.has(fn));

  const toggleAllFiles = () => {
    if (allFilesSelected) {
      setIncludedFiles(new Set());
      setLoadingFiles(new Set());
      setFileOutlierData(new Map());
      setIncludedFileEntries(new Set());
    } else {
      uniqueSuspiciousFilenames
        .filter(fn => !includedFiles.has(fn) && !loadingFiles.has(fn))
        .forEach(fn => toggleFile(fn));
    }
  };

  const sortedSuspiciousFiles = useMemo(
    () => [...suspiciousFiles].sort((a: SuspiciousFile, b: SuspiciousFile) => a.filename.localeCompare(b.filename)),
    [suspiciousFiles],
  );

  const allSelected = quarantined.length > 0 && included.size === quarantined.length;
  const toggleAll = () => {
    setIncluded(allSelected ? new Set() : new Set(quarantined.map((_, i) => i)));
  };

  const reIncludedFileOutliers = useMemo(() => {
    const result: Array<{ filename: string; transitionIdx: number } & SuspiciousTransition> = [];
    for (const [filename, transitions] of fileOutlierData) {
      if (!includedFiles.has(filename)) continue;
      transitions.forEach((t, idx) => {
        if (t.isOutlier) result.push({ filename, transitionIdx: idx, ...t });
      });
    }
    return result;
  }, [fileOutlierData, includedFiles]);

  const allFileEntriesSelected = reIncludedFileOutliers.length > 0 &&
    reIncludedFileOutliers.every(o => includedFileEntries.has(`${o.filename}::${o.transitionIdx}`));
  const toggleAllFileEntries = () => {
    if (allFileEntriesSelected) {
      setIncludedFileEntries(new Set());
    } else {
      setIncludedFileEntries(new Set(reIncludedFileOutliers.map(o => `${o.filename}::${o.transitionIdx}`)));
    }
  };

  const effectiveStats = useMemo(
    () => (edges
      ? computeEffectiveStats(edges, quarantined, included, includedFiles, fileOutlierData, includedFileEntries)
      : new Map<string, EffectiveStat>()),
    [included, includedFiles, fileOutlierData, includedFileEntries, edges, quarantined],
  );

  if (!edges || edges.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Statistics</h1>
          <div className={styles.headerActions}>
            <ThemeToggle />
            <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
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
                Check files to re-include them — statistics update automatically.
              </p>
            </div>
            <button className={styles.selectAllBtn} onClick={toggleAllFiles}>
              {allFilesSelected ? 'Deselect all' : 'Select all'}
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
                  <th>Outlier Score</th>
                </tr>
              </thead>
              <tbody>
                {sortedSuspiciousFiles.map((sf: SuspiciousFile, i: number) => {
                  const isFirstInGroup = i === 0 || sortedSuspiciousFiles[i - 1].filename !== sf.filename;
                  const isLoading = loadingFiles.has(sf.filename);
                  const isIncluded = includedFiles.has(sf.filename);
                  return (
                    <tr
                      key={i}
                      className={[
                        isIncluded ? styles.includedRow : '',
                        !isFirstInGroup ? styles.fileGroupContinuation : '',
                      ].filter(Boolean).join(' ') || undefined}
                      onClick={() => !isLoading && toggleFile(sf.filename)}
                      style={{ cursor: isLoading ? 'wait' : 'pointer' }}
                    >
                      <td className={styles.checkTd}>
                        {isFirstInGroup && (
                          <input
                            type="checkbox"
                            checked={isIncluded}
                            disabled={isLoading}
                            onChange={() => toggleFile(sf.filename)}
                            onClick={(e) => e.stopPropagation()}
                            className={styles.checkbox}
                          />
                        )}
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
                        <div className={styles.scoreCell}>
                          <div className={styles.scoreBar}>
                            <div className={styles.scoreFill} style={{ width: `${sf.outlierScore * 100}%` }} />
                          </div>
                          <span className={styles.scoreNum}>{sf.outlierScore.toFixed(2)}</span>
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
                </tr>
              </thead>
              <tbody>
                {quarantined.map((q, i) => (
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
              <h2 className={styles.quarantineTitle}>Outliers in Re-included Files</h2>
              <p className={styles.quarantineDesc}>
                {reIncludedFileOutliers.length} {reIncludedFileOutliers.length === 1 ? 'entry was' : 'entries were'} flagged
                as sojourn time outliers within the re-included files and excluded from the statistics above.
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
                  const key = `${o.filename}::${o.transitionIdx}`;
                  const isIncluded = includedFileEntries.has(key);
                  return (
                    <tr
                      key={i}
                      className={isIncluded ? styles.includedRow : undefined}
                      onClick={() => toggleFileEntry(o.filename, o.transitionIdx)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className={styles.checkTd}>
                        <input
                          type="checkbox"
                          checked={isIncluded}
                          onChange={() => toggleFileEntry(o.filename, o.transitionIdx)}
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
