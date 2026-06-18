import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { store } from "../store";
import styles from "./Home.module.css";
import ThemeToggle from "../components/ThemeToggle";

function Home() {
  const navigate = useNavigate();
  const [analyzeFiles, setAnalyzeFiles] = useState<FileList | null>(null);
  const [projectFile, setProjectFile] = useState<File | null>(null);
  const analyzeRef = useRef<HTMLInputElement>(null);
  const projectRef = useRef<HTMLInputElement>(null);

  const handleAnalyze = () => {
    if (!analyzeFiles || analyzeFiles.length === 0) return;
    store.setPendingFiles(analyzeFiles);
    store.setAnalysisResult(null);
    navigate("/loading");
  };

  const handleLoadProject = () => {
    if (!projectFile) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const graph = JSON.parse(e.target?.result as string);
        navigate("/flow", { state: { graph } });
      } catch {
        alert("Invalid project file.");
      }
    };
    reader.readAsText(projectFile);
  };

  return (
    <div className={styles.page}>
      <div style={{ position: 'absolute', top: 20, right: 24 }}>
        <ThemeToggle />
      </div>
      <header className={styles.header}>
        <h1 className={styles.title}>SMP Workbench</h1>
        <p className={styles.subtitle}>
          Analyze and visualize your state machine protocols
        </p>
      </header>

      <main className={styles.main}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Analyze Files</h2>
          <p className={styles.cardDescription}>
            Upload one or more JSON log files to generate a visual flow diagram.
          </p>

          <div
            className={`${styles.dropZone} ${analyzeFiles && analyzeFiles.length > 0 ? styles.dropZoneActive : ""}`}
            onClick={() => analyzeRef.current?.click()}
          >
            {analyzeFiles && analyzeFiles.length > 0 ? (
              <>
                <span className={styles.fileCount}>
                  {analyzeFiles.length} file{analyzeFiles.length > 1 ? "s" : ""} selected
                </span>
                <span className={styles.fileHint}>Click to change selection</span>
              </>
            ) : (
              <>
                <span className={styles.fileCount}>Click to select files</span>
                <span className={styles.fileHint}>Accepts .json</span>
              </>
            )}
            <input
              ref={analyzeRef}
              type="file"
              accept=".json"
              multiple
              onChange={(e) => setAnalyzeFiles(e.target.files)}
              style={{ display: "none" }}
            />
          </div>
          <button
            className={`${styles.btn} ${analyzeFiles && analyzeFiles.length > 0 ? styles.btnPrimary : styles.btnDisabled}`}
            onClick={handleAnalyze}
            disabled={!analyzeFiles || analyzeFiles.length === 0}
          >
            Start Analysis
          </button>
        </div>

        <div className={styles.divider}>
          <div className={styles.dividerLine} />
          <span>or</span>
          <div className={styles.dividerLine} />
        </div>

        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Load Project</h2>
          <p className={styles.cardDescription}>
            Open a previously saved project to continue where you left off.
          </p>
          <div
            className={`${styles.dropZone} ${projectFile ? styles.dropZoneActive : ""}`}
            onClick={() => projectRef.current?.click()}
          >
            {projectFile ? (
              <>
                <span className={styles.fileCount}>{projectFile.name}</span>
                <span className={styles.fileHint}>Click to change file</span>
              </>
            ) : (
              <>
                <span className={styles.fileCount}>Click to select file</span>
                <span className={styles.fileHint}>Accepts .json</span>
              </>
            )}
            <input
              ref={projectRef}
              type="file"
              accept=".json"
              onChange={(e) => setProjectFile(e.target.files?.[0] ?? null)}
              style={{ display: "none" }}
            />
          </div>
          <button
            className={`${styles.btn} ${projectFile ? styles.btnPrimary : styles.btnDisabled}`}
            onClick={handleLoadProject}
            disabled={!projectFile}
          >
            Load Project
          </button>
        </div>
      </main>

    </div>
  );
}

export default Home;
