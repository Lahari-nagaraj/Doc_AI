import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [documentUploaded, setDocumentUploaded] = useState(false);

  // 🔥 NEW STATES
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [showSources, setShowSources] = useState(false);

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

      setDocumentUploaded(true);
      setAnswer(""); // reset
      setSources([]);
      setShowSources(false);
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

    if (!documentUploaded) {
      alert("Please upload a document first");
      return;
    }

    try {
      const res = await axios.post("http://127.0.0.1:5000/ask", { query });

      setAnswer(res.data.answer);
      setSources(res.data.sources);
      setShowSources(false); // hide sources initially
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
          {documentUploaded ? (
            <>
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

              {/* 📌 ANSWER */}
              {answer && (
                <div className="answer-section">
                  <h3>Answer</h3>
                  <p>{answer}</p>
                  <button onClick={() => setShowSources(!showSources)} className="sources-button">
                    {showSources ? "Hide Sources" : "Show Sources"}
                  </button>
                </div>
              )}

              {/* 📌 SOURCES */}
              {showSources && sources.length > 0 && (
                <div className="sources-section">
                  <h3>Sources</h3>
                  {sources.map((item, index) => (
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
