import React, { useState, useEffect, useRef } from "react";
import "./FileClassifier.css";

const API = process.env.REACT_APP_API_URL;

export default function FileClassifier({ files }) {
  const [selectedPath, setSelectedPath] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dots, setDots] = useState("");
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!loading) return;
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);
    return () => clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    if (!uploadedFile && fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [uploadedFile]);

  const handleFileUpload = (e) => {
    setUploadedFile(e.target.files[0]);
    setSelectedPath("");
  };

  const handleDropdownChange = (e) => {
    setSelectedPath(e.target.value);
    setUploadedFile(null);
  };

  const handleClassify = async () => {
    setLoading(true);
    setResult(null);
    setError("");

    try {
      let res;

      if (uploadedFile) {
        const formData = new FormData();
        formData.append("file", uploadedFile);
        formData.append("method", "llm");

        res = await fetch(`${API}/classify_file`, {
          method: "POST",
          body: formData,
        });
      } else if (selectedPath) {
        res = await fetch(`${API}/classify_by_path`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: `files/${selectedPath}`, method: "llm" }),
        });
      } else {
        alert("Please select or upload a file.");
        setLoading(false);
        return;
      }

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Classification failed.");

      setResult(data.file_class || data);
    } catch (err) {
      console.error("❌ Classification error:", err);
      setError("Classification failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h2 className="form-title">📂 File Classifier</h2>

      <div className="form-group">
        <label className="form-label">Select a file from list:</label>
        <select
          value={selectedPath}
          onChange={handleDropdownChange}
          className="form-input"
        >
          <option value="">-- Choose a file --</option>
          {Array.isArray(files) && files.length > 0 ? (
            files.map((file, idx) => (
              <option key={idx} value={file.relative_path}>
                {file.filename}
              </option>
            ))
          ) : (
            <option>No files available</option>
          )}
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">Or upload a new file:</label>
        <input
          type="file"
          onChange={handleFileUpload}
          ref={fileInputRef}
          className="form-input"
        />
      </div>

      <div className="form-group form-actions">
        <button
          onClick={handleClassify}
          disabled={loading}
          className="form-button"
        >
          {loading ? "Classifying..." : "Classify File"}
        </button>
      </div>

      {loading && <div className="loading-text">⏳ Classifying{dots}</div>}
      {error && <div className="error-text">{error}</div>}

      {!loading && result && (
        <div className="result-card">
          <h3 className="result-title">🔍 Classification Result</h3>
          <p className="result-text">
            <strong>Label:</strong>{" "}
            {result.label
              .split("_")
              .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
              .join(" ")}
          </p>
        </div>
      )}
    </div>
  );
}
