import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);

  // 🔥 NEW STATES
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState([]);

  // 📂 Upload PDF
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

      // ⚠️ Backend now returns full text
      setPreview(res.data.preview || "");
      setResponse([]); // reset old results
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  // 🔍 Ask Question
  const handleAsk = async () => {
    if (!query) {
      alert("Enter a question");
      return;
    }

    try {
      const res = await axios.post("http://127.0.0.1:5000/ask", { query });

      setResponse(res.data.retrieved_chunks);
    } catch (err) {
      console.error(err);
      alert("Query failed");
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
          {/* 📄 DOCUMENT VIEW */}
          {preview ? (
            <>
              <div className="preview-text">{preview}</div>

              {/* 🔍 QUERY SECTION */}
              <div className="query-section">
                <input
                  type="text"
                  placeholder="Ask something about the document..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="query-input"
                />

                <button onClick={handleAsk} className="ask-button">
                  Ask
                </button>
              </div>

              {/* 📌 RESULTS */}
              {response.length > 0 && (
                <div className="results-section">
                  <h3>Relevant Sections</h3>

                  {response.map((item, index) => (
                    <div key={index} className="chunk-box">
                      {item}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              Upload a PDF to start analyzing...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
