import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
// @ts-ignore
import Loader from "../components/Loader";
import { store } from "../store";
import { analyzeFiles } from "../api/analysis";
import styles from "./Loading.module.css";

function Loading() {
  const navigate = useNavigate();
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const files = store.getPendingFiles();
    if (!files || files.length === 0) return;

    setAnalyzing(true);
    analyzeFiles(files)
      .then((result) => {
        store.setAnalysisResult(result);
        store.setPendingFiles(null);
        navigate("/flow");
      })
      .catch(() => {
        setAnalyzing(false);
        setError("Analysis failed. Please check your files and try again.");
      });
  }, [navigate]);

  return (
    <div className={styles.loading}>
      <h1>{analyzing ? "Analyzing" : "Loading"}</h1>
      <Loader />

      {error ? (
        <p className={styles.error}>{error}</p>
      ) : (
        <p className={styles.hint}>
          {analyzing ? "Processing your files..." : "Ready when you are."}
        </p>
      )}

      {error && (
        <button className={styles.continueBtn} onClick={() => navigate("/")}>
          Go Back
        </button>
      )}

      <button className={styles.debugBtn} onClick={() => navigate("/flow")}>
        DEBUG CONTINUE
      </button>
    </div>
  );
}

export default Loading;
