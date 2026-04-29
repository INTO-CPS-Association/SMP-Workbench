import { useLocation, useNavigate } from 'react-router-dom';
import type { Edge, Node } from '@xyflow/react';
import styles from './Statistics.module.css';

interface EdgeData {
  probability?: number;
  avgSojournTime?: number;
  transitionCount?: number;
}

export default function Statistics() {
  const location = useLocation();
  const navigate = useNavigate();
  const { nodes, edges } = (location.state as { nodes: Node[]; edges: Edge[] }) ?? {};

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
                  const data = (edge.data ?? {}) as EdgeData;
                  return (
                    <tr key={edge.id} className={i === 0 ? styles.fromGroup : undefined}>
                      <td>
                        {i === 0 ? (
                          <span className={styles.pill}>{nodeLabel[fromId] ?? fromId}</span>
                        ) : null}
                      </td>
                      <td>{nodeLabel[edge.target] ?? edge.target}</td>
                      <td>{data.probability != null ? (data.probability * 100).toFixed(2) + '%' : <span className={styles.na}>—</span>}</td>
                      <td>{data.avgSojournTime != null ? data.avgSojournTime.toFixed(2) : <span className={styles.na}>—</span>}</td>
                      <td>{data.transitionCount != null ? data.transitionCount : <span className={styles.na}>—</span>}</td>
                    </tr>
                  );
                })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
