import React, { useState } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  useNodes,
  useReactFlow,
  Position,
} from '@xyflow/react';
import type { EdgeProps, Node } from '@xyflow/react';
import styles from './CustomEdge.module.css';

const NODE_RADIUS = 40;

function getHandlePositions(angle: number): [Position, Position] {
  const P = Math.PI;
  if (angle > -P / 4 && angle <= P / 4)  return [Position.Right,  Position.Left];
  if (angle > P / 4  && angle <= 3*P/4)  return [Position.Bottom, Position.Top];
  if (angle > 3*P/4  || angle <= -3*P/4) return [Position.Left,   Position.Right];
  return [Position.Top, Position.Bottom];
}

function circleEdgePoint(cx: number, cy: number, toX: number, toY: number): [number, number] {
  const dx = toX - cx;
  const dy = toY - cy;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  return [cx + (dx / dist) * NODE_RADIUS, cy + (dy / dist) * NODE_RADIUS];
}

export function LabeledEdge({ id, source, target, data, markerEnd, style }: EdgeProps) {
  const { setEdges } = useReactFlow();
  const nodes = useNodes<Node>();
  const [editingField, setEditingField] = useState<'probability' | 'avgSojournTime' | null>(null);
  const [draft, setDraft] = useState('');
  const [hovered, setHovered] = useState(false);

  const sourceNode = nodes.find(n => n.id === source);
  const targetNode = nodes.find(n => n.id === target);
  if (!sourceNode || !targetNode) return null;

  const srcCx = sourceNode.position.x + NODE_RADIUS;
  const srcCy = sourceNode.position.y + NODE_RADIUS;
  const tgtCx = targetNode.position.x + NODE_RADIUS;
  const tgtCy = targetNode.position.y + NODE_RADIUS;

  let edgePath: string;
  let labelX: number;
  let labelY: number;

  if (source === target) {
    // Self-loop: exits top-right, arcs out, re-enters bottom-right
    const r = NODE_RADIUS;
    const lw = 50;
    const lh = 45;
    const sx = srcCx + r * 0.7;
    const sy = srcCy - r * 0.7;
    const ex = srcCx + r * 0.7;
    const ey = srcCy + r * 0.7;
    edgePath = `M ${sx} ${sy} C ${sx + lw} ${sy - lh} ${ex + lw} ${ey + lh} ${ex} ${ey}`;
    labelX = srcCx + r + lw + 8;
    labelY = srcCy;
  } else {
    const dx = tgtCx - srcCx;
    const dy = tgtCy - srcCy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const angle = Math.atan2(dy, dx);

    // Perpendicular direction (left of travel). Bidirectional edges travel
    // in opposite directions so their perpendiculars point to opposite sides,
    // giving each edge its own clearly separated path and label.
    const perpX = -dy / dist;
    const perpY =  dx / dist;
    const EDGE_OFFSET = 12;

    const [bsx, bsy] = circleEdgePoint(srcCx, srcCy, tgtCx, tgtCy);
    const [btx, bty] = circleEdgePoint(tgtCx, tgtCy, srcCx, srcCy);

    const sx = bsx + perpX * EDGE_OFFSET;
    const sy = bsy + perpY * EDGE_OFFSET;
    const tx = btx + perpX * EDGE_OFFSET;
    const ty = bty + perpY * EDGE_OFFSET;

    const [srcPos, tgtPos] = getHandlePositions(angle);

    const result = getBezierPath({
      sourceX: sx, sourceY: sy, sourcePosition: srcPos,
      targetX: tx, targetY: ty, targetPosition: tgtPos,
    });
    edgePath = result[0];

    const LABEL_OFFSET = 28;
    labelX = result[1] + perpX * LABEL_OFFSET;
    labelY = result[2] + perpY * LABEL_OFFSET;
  }

  const probability     = (data?.probability     ?? 0.0) as number;
  const avgSojournTime  = (data?.avgSojournTime   ?? 0.0) as number;

  const startEdit = (field: 'probability' | 'avgSojournTime', value: number) => {
    setEditingField(field);
    setDraft(String(value));
  };

  const commit = () => {
    if (!editingField) return;
    const num = parseFloat(draft);
    setEdges(eds =>
      eds.map(e =>
        e.id === id
          ? { ...e, data: { ...e.data, [editingField]: isNaN(num) ? 0.0 : num } }
          : e
      )
    );
    setEditingField(null);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter')  commit();
    if (e.key === 'Escape') setEditingField(null);
  };

  return (
    <>
      <g
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{ cursor: 'pointer' }}
      >
        {/* Wide invisible stroke for reliable hover detection */}
        <path d={edgePath} fill="none" stroke="rgba(0,0,0,0)" strokeWidth={20} />
        <BaseEdge
          path={edgePath}
          markerEnd={markerEnd}
          style={{
            ...style,
            stroke:  hovered ? '#facc15' : (style as React.CSSProperties | undefined)?.stroke,
            filter:  hovered ? 'drop-shadow(0 0 8px #facc15) drop-shadow(0 0 16px #fbbf24)' : undefined,
            transition: 'stroke 0.15s, filter 0.15s',
          }}
        />
      </g>
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
            zIndex: hovered ? 1000 : 1,
          }}
          className="nodrag nopan"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <div
            className={styles.label}
            style={hovered ? { borderColor: '#facc15', boxShadow: '0 0 8px #facc15, 0 0 16px #fbbf2466' } : undefined}
          >
            <div className={styles.row}>
              <span className={styles.key}>P</span>
              {editingField === 'probability' ? (
                <input
                  className={styles.input}
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onBlur={commit}
                  onKeyDown={onKeyDown}
                  autoFocus
                />
              ) : (
                <span className={styles.value} onClick={() => startEdit('probability', probability)}>
                  {probability.toFixed(4)}
                </span>
              )}
            </div>
            <div className={styles.row}>
              <span className={styles.key}>T</span>
              {editingField === 'avgSojournTime' ? (
                <input
                  className={styles.input}
                  value={draft}
                  onChange={e => setDraft(e.target.value)}
                  onBlur={commit}
                  onKeyDown={onKeyDown}
                  autoFocus
                />
              ) : (
                <span className={styles.value} onClick={() => startEdit('avgSojournTime', avgSojournTime)}>
                  {avgSojournTime.toFixed(4)}s
                </span>
              )}
            </div>
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
