import { useEffect, useRef } from 'react';
import styles from './ConfirmDialog.module.css';

interface Props {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  message,
  confirmLabel = 'OK',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: Props) {
  const cancelRef = useRef(onCancel);
  cancelRef.current = onCancel;

  const cancelBtnRef = useRef<HTMLButtonElement | null>(null);
  const titleId = 'confirm-dialog-title';
  const bodyId = 'confirm-dialog-body';

  useEffect(() => {
    cancelBtnRef.current?.focus();
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') cancelRef.current(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        onClick={e => e.stopPropagation()}
      >
        <div className={styles.header}>
          <span id={titleId} className={styles.title}>{title}</span>
        </div>
        <div id={bodyId} className={styles.body}>{message}</div>
        <div className={styles.footer}>
          <button ref={cancelBtnRef} className={styles.cancelBtn} onClick={onCancel}>{cancelLabel}</button>
          <button className={styles.okBtn} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
