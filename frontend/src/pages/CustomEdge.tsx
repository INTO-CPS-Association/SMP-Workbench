import React, { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import styles from './CustomEdge.module.css';

export function LabeledEdge({
  id,
  sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition,
  data, markerEnd, style,
}: EdgeProps) {
  const { setEdges } = useReactFlow();
  const [editingField, setEditingField] = useState<'probability' | 'avgSojournTime' | null>(null);
  const [draft, setDraft] = useState('');

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const probability = (data?.probability ?? 0.0) as number;
  const avgSojournTime = (data?.avgSojournTime ?? 0.0) as number;

  const startEdit = (field: 'probability' | 'avgSojournTime', value: number) => {
    setEditingField(field);
    setDraft(String(value));
  };

  const commit = () => {
    if (!editingField) return;
    const num = parseFloat(draft);
    setEdges((eds) =>
      eds.map((e) =>
        e.id === id
          ? { ...e, data: { ...e.data, [editingField]: isNaN(num) ? 0.0 : num } }
          : e
      )
    );
    setEditingField(null);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') setEditingField(null);
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <div className={styles.label}>
            <div className={styles.row}>
              <span className={styles.key}>P:</span>
              {editingField === 'probability' ? (
                <input
                  className={styles.input}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commit}
                  onKeyDown={onKeyDown}
                  autoFocus
                />
              ) : (
                <span className={styles.value} onClick={() => startEdit('probability', probability)}>
                  {probability.toFixed(1)}
                </span>
              )}
            </div>
            <div className={styles.row}>
              <span className={styles.key}>AST:</span>
              {editingField === 'avgSojournTime' ? (
                <input
                  className={styles.input}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={commit}
                  onKeyDown={onKeyDown}
                  autoFocus
                />
              ) : (
                <span className={styles.value} onClick={() => startEdit('avgSojournTime', avgSojournTime)}>
                  {avgSojournTime.toFixed(1)}
                </span>
              )}
            </div>
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
