import React, { useEffect, useState } from "react";
import FileClassifier from "./components/FileClassifier";
import CreateCategoryForm from "./components/CreateCategoryForm";

const API = process.env.REACT_APP_API_URL || "http://localhost:5050";

export default function App() {
  const [files, setFiles] = useState([]);

  const fetchFiles = () => {
    fetch(`${API}/list_files`)
      .then((res) => res.json())
      .then((data) => setFiles(data.files || []))
      .catch((err) => console.error("Failed to fetch files", err));
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <h1 style={{ textAlign: "center", marginBottom: "2rem" }}>
        🧠 Heron Data Document Classifier
      </h1>
      
      <div style={{ 
        display: "flex", 
        justifyContent: "center",
        gap: "2rem",
        alignItems: "flex-start"
      }}>
        <div style={{ width: "600px" }}>
          <FileClassifier files={files} />
        </div>
        <div style={{ width: "600px" }}>
          <CreateCategoryForm onCategoryCreated={()=> {setTimeout(fetchFiles, 500)}} />
        </div>
      </div>
    </div>
  );
}
  
