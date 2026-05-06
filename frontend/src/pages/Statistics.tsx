import { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Edge, Node } from '@xyflow/react';
import styles from './Statistics.module.css';
import { store } from '../store';
import type { QuarantinedEntry } from '../api/analysis';

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
): Map<string, EffectiveStat> {
  // Build sojourn time lists starting from clean times
  const sojournByEdge = new Map<string, number[]>();
  for (const edge of edges) {
    const times = ((edge.data as EdgeData)?.cleanSojournTimes) ?? [];
    sojournByEdge.set(edge.id, [...times]);
  }

  // Merge in any included quarantined entries
  const anyIncluded = included.size > 0;
  for (const [i, q] of quarantined.entries()) {
    if (!included.has(i)) continue;
    const edgeId = `${q.fromState}-${q.toState}`;
    const times = sojournByEdge.get(edgeId);
    if (times) times.push(q.sojournTime);
  }

  // Per-source totals for probability recomputation
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

  const toggleEntry = (idx: number) => {
    setIncluded(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  const allSelected = quarantined.length > 0 && included.size === quarantined.length;
  const toggleAll = () => {
    setIncluded(allSelected ? new Set() : new Set(quarantined.map((_, i) => i)));
  };

  const effectiveStats = useMemo(
    () => (edges ? computeEffectiveStats(edges, quarantined, included) : new Map<string, EffectiveStat>()),
    [included, edges, quarantined],
  );

  if (!edges || edges.length === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Statistics</h1>
          <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
        </div>
        <p className={styles.empty}>No transition data available. Run an analysis first.</p>
      </div>
    );
  }

  // Build node label lookup
  const nodeLabel: Record<string, string> = {};
  (nodes ?? []).forEach((n) => {
    nodeLabel[n.id] = (n.data?.label as string) ?? n.id;
  });

  // Group edges by source state
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
        <button className={styles.navBtn} onClick={() => navigate('/flow')}>Flow page</button>
      </div>

      {suspiciousFiles.length > 0 && (
        <div className={styles.suspiciousSection}>
          <div className={styles.suspiciousHeader}>
            <h2 className={styles.suspiciousTitle}>Suspicious Files</h2>
            <p className={styles.suspiciousDesc}>
              {suspiciousFiles.length === 1 ? '1 file was' : `${suspiciousFiles.length} files were`} flagged
              for containing an unusually high count of a particular transition compared to the rest of the
              uploaded files. This may indicate an unresolved error propagating through the log.
            </p>
          </div>
          <div className={styles.tableWrapper}>
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Transition</th>
                  <th>Count</th>
                  <th>Expected (avg)</th>
                  <th>Outlier Score</th>
                </tr>
              </thead>
              <tbody>
                {suspiciousFiles.map((sf, i) => (
                  <tr key={i}>
                    <td className={styles.suspiciousFilename}>{sf.filename}</td>
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
                ))}
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
                      <td>
                        {avg.toFixed(2)}
                        {eff?.recalibrated && !eff?.recalibrated ? null : null}
                      </td>
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
    </div>
  );
}
