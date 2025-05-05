import React, { useState } from "react";
import "./CreateCategoryForm.css";

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
    <div className="form-container">
      <h2 className="form-title">📄 Create New Document Category</h2>

      {/* Category Name */}
      <div className="form-group">
        <label className="form-label">Category Name:</label>
        <input
          type="text"
          value={categoryName}
          onChange={(e) => {
            setCategoryName(e.target.value);
            setTouched(true);
          }}
          placeholder="e.g. Pay Stub"
          className={`form-input ${!nameValid && touched ? "form-input-error" : ""}`}
        />
        {!nameValid && touched && (
          <p className="error-text">Category name is required.</p>
        )}
      </div>

      {/* Fields */}
      <div className="form-group">
        <label className="form-label">Fields (at least 2):</label>
        {fields.map((field, index) => (
          <div key={index} className="field-row">
            <input
              type="text"
              value={field}
              onChange={(e) => handleFieldChange(index, e.target.value)}
              className="form-input"
            />
            {fields.length > 1 && (
              <button onClick={() => removeField(index)} className="remove-btn">
                ✕
              </button>
            )}
          </div>
        ))}
        {!fieldsValid && touched && (
          <p className="error-text">Please enter at least two fields.</p>
        )}
        <button onClick={addField} className="add-field-btn">➕ Add Field</button>
      </div>

      {/* Number of files */}
      <div className="form-group">
        <label className="form-label">Number of synthetic files to generate:</label>
        <input
          type="number"
          value={numFiles}
          onChange={(e) => setNumFiles(Math.min(Number(e.target.value), 10))}
          min={1}
          max={10}
          className="form-number"
        />
      </div>

      {/* Submit button */}
      <button
        onClick={handleSubmit}
        disabled={loading || !formValid}
        className="submit-btn"
      >
        {loading ? "Creating..." : "Create Category"}
      </button>

      {/* Status message */}
      {status && (
        <div
          className={`status-box ${
            status.startsWith("✅") ? "status-success" : "status-error"
          }`}
        >
          {status}
        </div>
      )}
    </div>
  );
}
