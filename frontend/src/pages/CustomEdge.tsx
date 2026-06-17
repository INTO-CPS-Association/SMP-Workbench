import { useState } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  useNodes,
  useEdges,
  Position,
} from '@xyflow/react';
import type { EdgeProps, Node } from '@xyflow/react';
import styles from './CustomEdge.module.css';
import { DIST_SHORT } from './TransitionInspector';
import type { ChosenDistribution } from './TransitionInspector';
import { useOpenInspector } from './InspectorContext';

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
  const openInspector = useOpenInspector();
  const nodes = useNodes<Node>();
  const allEdges = useEdges();
  const [hovered, setHovered] = useState(false);

  const sourceSum = allEdges
    .filter(e => e.source === source)
    .reduce((sum, e) => sum + ((e.data?.probability ?? 0) as number), 0);
  const isSourceInvalid = sourceSum > 0 && (sourceSum > 1.0 || sourceSum < 0.99);

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
    const r = NODE_RADIUS;
    const lw = 50, lh = 45;
    const sx = srcCx + r * 0.7, sy = srcCy - r * 0.7;
    const ex = srcCx + r * 0.7, ey = srcCy + r * 0.7;
    edgePath = `M ${sx} ${sy} C ${sx + lw} ${sy - lh} ${ex + lw} ${ey + lh} ${ex} ${ey}`;
    labelX = srcCx + r + lw + 8;
    labelY = srcCy;
  } else {
    const dx = tgtCx - srcCx;
    const dy = tgtCy - srcCy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const angle = Math.atan2(dy, dx);
    const perpX = -dy / dist;
    const perpY =  dx / dist;
    const EDGE_OFFSET = 12;

    const [bsx, bsy] = circleEdgePoint(srcCx, srcCy, tgtCx, tgtCy);
    const [btx, bty] = circleEdgePoint(tgtCx, tgtCy, srcCx, srcCy);
    const sx = bsx + perpX * EDGE_OFFSET, sy = bsy + perpY * EDGE_OFFSET;
    const tx = btx + perpX * EDGE_OFFSET, ty = bty + perpY * EDGE_OFFSET;
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

  const probability  = (data?.probability        ?? 0.0) as number;
  const sojournTimes = (data?.cleanSojournTimes  ?? []) as number[];
  const chosenDist   = (data?.chosenDistribution ?? null) as ChosenDistribution | null;

  const displayDist = chosenDist?.name ? (DIST_SHORT[chosenDist.name] ?? chosenDist.name) : null;

  const fromLabel = (sourceNode.data?.label as string) ?? source;
  const toLabel   = (targetNode.data?.label as string) ?? target;

  const handleDoubleClick = (e: { stopPropagation(): void }) => {
    e.stopPropagation();
    openInspector({ edgeId: id, fromLabel, toLabel, sojournTimes, initial: chosenDist, probability });
  };

  return (
    <>
      <g
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onDoubleClick={handleDoubleClick}
        style={{ cursor: 'pointer' }}
      >
        <path d={edgePath} fill="none" stroke="rgba(0,0,0,0)" strokeWidth={20} />
        <BaseEdge
          path={edgePath}
          markerEnd={markerEnd}
          style={{
            ...style,
            stroke: isSourceInvalid
              ? '#ef4444'
              : hovered ? '#facc15' : 'var(--edge-stroke)',
            filter: isSourceInvalid
              ? 'drop-shadow(0 0 5px rgba(239,68,68,0.55))'
              : hovered ? 'drop-shadow(0 0 8px #facc15) drop-shadow(0 0 16px #fbbf24)' : undefined,
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
          onDoubleClick={handleDoubleClick}
        >
          <div
            className={styles.label}
            style={hovered ? { borderColor: '#facc15', boxShadow: '0 0 8px #facc15, 0 0 16px #fbbf2466' } : undefined}
          >
            <div className={styles.row}>
              <span className={styles.key}>P</span>
              <span className={styles.value}>{probability.toFixed(4)}</span>
            </div>
            {displayDist && (
              <div className={styles.row}>
                <span className={styles.key}>D</span>
                <span className={styles.distValue}>{displayDist}</span>
              </div>
            )}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
