import React, { useState } from "react";

const API = process.env.REACT_APP_API_URL || "http://localhost:5050";

export default function CreateCategoryForm({ onCategoryCreated }) {
  const [categoryName, setCategoryName] = useState("");
  const [fields, setFields] = useState([""]);
  const [numFiles, setNumFiles] = useState(5);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);

  const handleFieldChange = (index, value) => {
    const updated = [...fields];
    updated[index] = value;
    setFields(updated);
    setTouched(true);
  };

  const addField = () => {
    setFields([...fields, ""]);
    setTouched(true);
  };

  const removeField = (index) => {
    setFields(fields.filter((_, i) => i !== index));
    setTouched(true);
  };

  const trimmedFields = fields.map((f) => f.trim()).filter(Boolean);
  const nameValid = categoryName.trim().length > 0;
  const fieldsValid = trimmedFields.length >= 2;
  const formValid = nameValid && fieldsValid;

  const handleSubmit = async () => {
    if (!formValid) return;

    setLoading(true);
    setStatus("");

    try {
      const res = await fetch(`${API}/generate_category`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: categoryName.trim().toLowerCase().replace(/\s+/g, "_"),
          fields: trimmedFields,
          num: Number(numFiles),
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create category");

      setStatus(`✅ Category '${categoryName}' created with ${numFiles} files.`);
      setCategoryName("");
      setFields([""]);
      setTouched(false);
      if (onCategoryCreated) onCategoryCreated();
    } catch (err) {
      console.error(err);
      setStatus("❌ " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "600px",
        margin: "0 auto",
        padding: "2rem",
        borderRadius: "10px",
        backgroundColor: "#fff",
        boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
        fontFamily: "sans-serif",
      }}
    >
      <h2 style={{ marginBottom: "1.5rem", color: "#333" }}>📄 Create New Document Category</h2>

      {/* Category Name */}
      <div style={{ marginBottom: "1.5rem" }}>
        <label style={{ fontWeight: "bold" }}>Category Name:</label>
        <input
          type="text"
          value={categoryName}
          onChange={(e) => {
            setCategoryName(e.target.value);
            setTouched(true);
          }}
          placeholder="e.g. Pay Stub"
          style={{
            width: "100%",
            padding: "0.5rem",
            marginTop: "0.5rem",
            borderRadius: "4px",
            border: `1px solid ${!nameValid && touched ? "#f44336" : "#ccc"}`,
          }}
        />
        {!nameValid && touched && (
          <p style={{ color: "#f44336", marginTop: "0.25rem", fontSize: "0.875rem" }}>
            Category name is required.
          </p>
        )}
      </div>

      {/* Fields */}
      <div style={{ marginBottom: "1.5rem" }}>
        <label style={{ fontWeight: "bold" }}>Fields (at least 2):</label>
        {fields.map((field, index) => (
          <div key={index} style={{ display: "flex", marginTop: "0.5rem" }}>
            <input
              type="text"
              value={field}
              onChange={(e) => handleFieldChange(index, e.target.value)}
              style={{
                flexGrow: 1,
                padding: "0.5rem",
                borderRadius: "4px",
                border: "1px solid #ccc",
              }}
            />
            {fields.length > 1 && (
              <button
                onClick={() => removeField(index)}
                style={{
                  marginLeft: "0.5rem",
                  padding: "0.5rem",
                  background: "#f44336",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            )}
          </div>
        ))}

        {!fieldsValid && touched && (
          <p style={{ color: "#f44336", marginTop: "0.5rem", fontSize: "0.875rem" }}>
            Please enter at least two fields.
          </p>
        )}

        <button
          onClick={addField}
          style={{
            marginTop: "0.75rem",
            background: "#eee",
            border: "none",
            padding: "0.5rem 1rem",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          ➕ Add Field
        </button>
      </div>

      {/* Number of files */}
      <div style={{ marginBottom: "1.5rem" }}>
        <label style={{ fontWeight: "bold" }}>
          Number of synthetic files to generate:
        </label>
        <input
          type="number"
          value={numFiles}
          onChange={(e) => setNumFiles(e.target.value)}
          min={1}
          max={10}
          style={{
            display: "block",
            width: "100%",
            padding: "0.5rem",
            marginTop: "0.5rem",
            borderRadius: "4px",
            border: "1px solid #ccc",
          }}
        />
      </div>

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={loading || !formValid}
        style={{
          padding: "0.6rem 1.2rem",
          fontSize: "1rem",
          backgroundColor: "#2196f3",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: loading || !formValid ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Creating..." : "Create Category"}
      </button>

      {/* Status message */}
      {status && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "#f9f9f9",
            borderRadius: "6px",
            borderLeft: status.startsWith("✅")
              ? "4px solid #4caf50"
              : "4px solid red",
          }}
        >
          {status}
        </div>
      )}
    </div>
  );
}
