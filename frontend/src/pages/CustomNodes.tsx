import { useState, useEffect, useRef } from 'react';
import { Handle, Position, useReactFlow } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import styles from './CustomNodes.module.css';

export function RoundDefaultNode({ id, data }: NodeProps) {
  const { updateNodeData } = useReactFlow();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(data.label as string);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  useEffect(() => {
    if (!editing) setDraft(data.label as string);
  }, [data.label, editing]);

  const commit = () => {
    updateNodeData(id, { label: draft || 'Node' });
    setEditing(false);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') commit();
    if (e.key === 'Escape') { setDraft(data.label as string); setEditing(false); }
  };

  return (
    <div className={`${styles.node} ${styles.default}`}>
      <Handle id="top" type="source" position={Position.Top} />
      <Handle id="left" type="source" position={Position.Left} />
      {editing ? (
        <input
          ref={inputRef}
          className={`${styles.label} nodrag`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={onKeyDown}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span
          className={styles.labelText}
          onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); }}
        >
          {data.label as string}
        </span>
      )}
      <Handle id="right" type="source" position={Position.Right} />
      <Handle id="bottom" type="source" position={Position.Bottom} />
    </div>
  );
}
