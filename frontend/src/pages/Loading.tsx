import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { store } from "../store";
import { analyzeFilesStreaming } from "../api/analysis";
import styles from "./Loading.module.css";
import ThemeToggle from "../components/ThemeToggle";

function Loading() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("Starting…");
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const files = store.getPendingFiles();
    if (!files || files.length === 0) return;

    analyzeFilesStreaming(files, (pct, msg) => {
      setProgress(pct);
      setMessage(msg);
    }, store.getOutlierMethod(), store.getFileDetectionMethod())
      .then((result) => {
        store.setAnalysisResult(result);
        store.setPendingFiles(null);
        navigate("/flow");
      })
      .catch((err: Error) => {
        setError(err.message || "Analysis failed. Please check your files and try again.");
      });
  }, [navigate]);

  return (
    <div className={styles.loading}>
      <div style={{ position: 'absolute', top: 20, right: 24 }}>
        <ThemeToggle />
      </div>
      <h1 className={styles.title}>{error ? "Error" : "Analyzing"}</h1>

      {!error && (
        <>
          <div className={styles.progressWrapper}>
            <div className={styles.progressBar}>
              <div className={styles.progressFill} style={{ width: `${progress}%` }} />
            </div>
            <span className={styles.progressPct}>{progress}%</span>
          </div>
          <p className={styles.hint}>{message}</p>
        </>
      )}

      {error && (
        <>
          <p className={styles.error}>{error}</p>
          <button className={styles.continueBtn} onClick={() => navigate("/")}>
            Go Back
          </button>
        </>
      )}

    </div>
  );
}

export default Loading;
