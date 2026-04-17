import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);

      const res = await axios.post("http://127.0.0.1:5000/upload", formData);

      setPreview(res.data.preview);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* HEADER */}
      <div className="app-header">
        <div className="header-inner">
          <h2 className="logo">📄 DocAI</h2>

          <div className="actions">
            <input 
              type="file" 
              onChange={(e) => setFile(e.target.files[0])} 
              className="file-input"
              accept=".pdf"
            />

            <button onClick={handleUpload} className="upload-button">
              {loading ? "Processing..." : "Upload"}
            </button>
          </div>
        </div>
      </div>

      {/* MAIN */}
      <div className="main-content">
        <div className="content-box">
          {preview ? (
            <div className="preview-text">{preview}</div>
          ) : (
            <div className="empty-state">Upload a PDF to start analyzing...</div>
          )}
        </div>
      </div>
    </div>
  );
}


export default App;
