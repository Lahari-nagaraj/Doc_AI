import { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const BASE_URL = "http://127.0.0.1:5000";

const DIFFICULTY_CONFIG = {
  easy: {
    label: "Easy",
    emoji: "🟢",
    color: "#16a34a",
    bg: "#f0fdf4",
    border: "#86efac",
    activeBg: "#dcfce7",
    description: "Direct facts, obvious answers, clearly wrong options",
  },
  medium: {
    label: "Medium",
    emoji: "🟡",
    color: "#b45309",
    bg: "#fffbeb",
    border: "#fde68a",
    activeBg: "#fef3c7",
    description: "Specific details, plausible distractors, requires attention",
  },
  hard: {
    label: "Hard",
    emoji: "🔴",
    color: "#dc2626",
    bg: "#fef2f2",
    border: "#fca5a5",
    activeBg: "#fee2e2",
    description: "Nuanced, tricky distractors, synthesis required",
  },
};

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [documentUploaded, setDocumentUploaded] = useState(false);
  const [activeTab, setActiveTab] = useState("ask");

  // Q&A
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [showSources, setShowSources] = useState(false);
  const [askLoading, setAskLoading] = useState(false);

  // Summary
  const [summary, setSummary] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Quiz
  const [quiz, setQuiz] = useState([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizLoadingMsg, setQuizLoadingMsg] = useState("");
  const [numQuestions, setNumQuestions] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [userAnswers, setUserAnswers] = useState({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [score, setScore] = useState(null);
  const [activeDifficulty, setActiveDifficulty] = useState(null);

  // Rate limit state
  const [rateLimited, setRateLimited] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const countdownRef = useRef(null);

  // Countdown timer for rate limit
  const startCountdown = (seconds) => {
    setRateLimited(true);
    setCountdown(seconds);
    clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownRef.current);
          setRateLimited(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  useEffect(() => () => clearInterval(countdownRef.current), []);

  const handleUpload = async () => {
    if (!file) {
      alert("Please select a file");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      setLoading(true);
      await axios.post(`${BASE_URL}/upload`, formData);
      setDocumentUploaded(true);
      setAnswer("");
      setSources([]);
      setSummary("");
      setQuiz([]);
      setUserAnswers({});
      setQuizSubmitted(false);
      setScore(null);
      setRateLimited(false);
      setCountdown(0);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    } finally {
      setLoading(false);
    }
  };

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
      setAskLoading(true);
      setAnswer("");
      setSources([]);
      setShowSources(false);
      const res = await axios.post(`${BASE_URL}/ask`, { query });
      setAnswer(res.data.answer);
      setSources(res.data.sources);
    } catch (err) {
      console.error(err);
      alert("Query failed");
    } finally {
      setAskLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!documentUploaded) return;
    if (summary) return;
    try {
      setSummaryLoading(true);
      const res = await axios.post(`${BASE_URL}/summarize`);
      setSummary(res.data.summary);
    } catch (err) {
      console.error(err);
      alert("Summarization failed");
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleGenerateQuiz = async () => {
    if (!documentUploaded) {
      alert("Please upload a document first");
      return;
    }
    if (rateLimited) return;

    try {
      setQuizLoading(true);
      setQuiz([]);
      setUserAnswers({});
      setQuizSubmitted(false);
      setScore(null);
      setQuizLoadingMsg("Analyzing document size...");

      // Small delay so user sees the first message
      await new Promise((r) => setTimeout(r, 600));
      setQuizLoadingMsg("Building context from document...");

      const res = await axios.post(`${BASE_URL}/quiz`, {
        num_questions: numQuestions,
        difficulty: difficulty,
      });

      setQuiz(res.data.quiz);
      setActiveDifficulty(res.data.difficulty);
    } catch (err) {
      console.error(err);
      const data = err.response?.data;

      if (err.response?.status === 429 || data?.error === "rate_limited") {
        // Start a 65-second countdown
        startCountdown(65);
      } else {
        alert(
          data?.message || data?.error || "Quiz generation failed. Try again.",
        );
      }
    } finally {
      setQuizLoading(false);
      setQuizLoadingMsg("");
    }
  };

  const handleOptionSelect = (qIndex, option) => {
    if (quizSubmitted) return;
    setUserAnswers((prev) => ({ ...prev, [qIndex]: option }));
  };

  const handleSubmitQuiz = () => {
    let correct = 0;
    quiz.forEach((q, i) => {
      if (userAnswers[i] === q.answer) correct++;
    });
    setScore(correct);
    setQuizSubmitted(true);
  };

  const handleRetakeQuiz = () => {
    setUserAnswers({});
    setQuizSubmitted(false);
    setScore(null);
    setQuiz([]);
    setActiveDifficulty(null);
  };

  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    if (tab === "summary" && !summary && documentUploaded) handleSummarize();
  };

  const renderSummary = (text) =>
    text.split("\n").map((line, i) => {
      if (line.startsWith("## "))
        return (
          <h3 key={i} className="summary-heading">
            {line.replace("## ", "")}
          </h3>
        );
      if (line.startsWith("- "))
        return (
          <li key={i} className="summary-bullet">
            {line.replace("- ", "")}
          </li>
        );
      if (line.trim() === "") return <br key={i} />;
      return (
        <p key={i} className="summary-para">
          {line}
        </p>
      );
    });

  const cfg = activeDifficulty ? DIFFICULTY_CONFIG[activeDifficulty] : null;
  const answeredCount = Object.keys(userAnswers).length;

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
            <button
              onClick={handleUpload}
              className="upload-button"
              disabled={loading}
            >
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
              <div className="tabs">
                <button
                  className={`tab-btn ${activeTab === "ask" ? "active" : ""}`}
                  onClick={() => handleTabSwitch("ask")}
                >
                  💬 Ask
                </button>
                <button
                  className={`tab-btn ${activeTab === "summary" ? "active" : ""}`}
                  onClick={() => handleTabSwitch("summary")}
                >
                  📝 Summary
                </button>
                <button
                  className={`tab-btn ${activeTab === "quiz" ? "active" : ""}`}
                  onClick={() => handleTabSwitch("quiz")}
                >
                  🧠 Quiz
                </button>
              </div>

              {/* ASK TAB */}
              {activeTab === "ask" && (
                <div className="tab-content">
                  <div className="query-section">
                    <input
                      type="text"
                      placeholder="Ask something about the document..."
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                      className="query-input"
                    />
                    <button
                      onClick={handleAsk}
                      className="ask-button"
                      disabled={askLoading}
                    >
                      {askLoading ? "Thinking..." : "Ask"}
                    </button>
                  </div>
                  {askLoading && (
                    <div className="loading-indicator">
                      🔍 Searching document...
                    </div>
                  )}
                  {answer && (
                    <div className="answer-section">
                      <h3>Answer</h3>
                      <p>{answer}</p>
                      <button
                        onClick={() => setShowSources(!showSources)}
                        className="sources-button"
                      >
                        {showSources ? "Hide Sources" : "Show Sources"}
                      </button>
                    </div>
                  )}
                  {showSources && sources.length > 0 && (
                    <div className="sources-section">
                      <h3>Sources</h3>
                      {sources.map((item, i) => (
                        <div key={i} className="chunk-box">
                          {item}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* SUMMARY TAB */}
              {activeTab === "summary" && (
                <div className="tab-content">
                  {summaryLoading && (
                    <div className="loading-indicator">
                      📝 Summarizing document...
                    </div>
                  )}
                  {summary && !summaryLoading && (
                    <div className="summary-container">
                      {renderSummary(summary)}
                    </div>
                  )}
                  {!summary && !summaryLoading && (
                    <div className="empty-state">
                      Something went wrong.{" "}
                      <button className="ask-button" onClick={handleSummarize}>
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* QUIZ TAB */}
              {activeTab === "quiz" && (
                <div className="tab-content">
                  {/* RATE LIMIT BANNER */}
                  {rateLimited && (
                    <div className="rate-limit-banner">
                      <div className="rate-limit-icon">⏳</div>
                      <div className="rate-limit-text">
                        <strong>API rate limit reached</strong>
                        <p>
                          Groq allows ~6,000 tokens/minute on the free tier.
                          Your document needed compression which used up the
                          quota.
                        </p>
                      </div>
                      <div className="rate-limit-countdown">
                        <span className="countdown-number">{countdown}</span>
                        <span className="countdown-label">seconds</span>
                      </div>
                      <button
                        className="ask-button"
                        onClick={handleGenerateQuiz}
                        disabled={countdown > 0}
                        style={{ marginLeft: "auto" }}
                      >
                        {countdown > 0 ? `Wait ${countdown}s` : "Try Now →"}
                      </button>
                    </div>
                  )}

                  {/* SETUP SCREEN */}
                  {quiz.length === 0 && !quizLoading && (
                    <div className="quiz-setup">
                      <p className="quiz-intro">
                        Test your understanding of the document.
                      </p>

                      <div className="difficulty-section">
                        <p className="difficulty-label">Select Difficulty</p>
                        <div className="difficulty-cards">
                          {Object.entries(DIFFICULTY_CONFIG).map(
                            ([key, cfg]) => (
                              <button
                                key={key}
                                className={`difficulty-card ${difficulty === key ? "selected" : ""}`}
                                style={{
                                  "--card-color": cfg.color,
                                  "--card-border":
                                    difficulty === key ? cfg.color : cfg.border,
                                  "--card-bg":
                                    difficulty === key ? cfg.activeBg : cfg.bg,
                                }}
                                onClick={() => setDifficulty(key)}
                              >
                                <span className="diff-emoji">{cfg.emoji}</span>
                                <span className="diff-name">{cfg.label}</span>
                                <span className="diff-desc">
                                  {cfg.description}
                                </span>
                                {difficulty === key && (
                                  <span className="diff-check">✓</span>
                                )}
                              </button>
                            ),
                          )}
                        </div>
                      </div>

                      <div className="quiz-controls">
                        <label>Questions:</label>
                        <select
                          value={numQuestions}
                          onChange={(e) =>
                            setNumQuestions(Number(e.target.value))
                          }
                          className="quiz-select"
                        >
                          <option value={3}>3</option>
                          <option value={5}>5</option>
                          <option value={7}>7</option>
                          <option value={10}>10</option>
                        </select>
                        <button
                          onClick={handleGenerateQuiz}
                          className="ask-button generate-btn"
                          disabled={rateLimited}
                        >
                          {rateLimited
                            ? `Wait ${countdown}s...`
                            : "Generate Quiz →"}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* LOADING */}
                  {quizLoading && (
                    <div className="quiz-loading-block">
                      <div className="loading-indicator">
                        🧠{" "}
                        {quizLoadingMsg ||
                          `Generating ${numQuestions} ${difficulty} questions...`}
                      </div>
                      <p className="loading-hint">
                        Large documents are compressed automatically — this may
                        take a moment.
                      </p>
                    </div>
                  )}

                  {/* ACTIVE QUIZ */}
                  {quiz.length > 0 && !quizLoading && (
                    <>
                      {cfg && (
                        <div
                          className="quiz-difficulty-badge"
                          style={{
                            background: cfg.activeBg,
                            borderColor: cfg.border,
                            color: cfg.color,
                          }}
                        >
                          {cfg.emoji} {cfg.label} Mode — {quiz.length} Questions
                        </div>
                      )}

                      {quizSubmitted && (
                        <div
                          className={`score-banner ${score === quiz.length ? "perfect" : score >= Math.ceil(quiz.length * 0.6) ? "good" : "retry"}`}
                        >
                          {score === quiz.length
                            ? `🎉 Perfect! ${score}/${quiz.length} — You nailed it!`
                            : score >= Math.ceil(quiz.length * 0.6)
                              ? `✅ Nice work! ${score}/${quiz.length}`
                              : `📚 ${score}/${quiz.length} — Review and try again!`}
                        </div>
                      )}

                      <div className="quiz-list">
                        {quiz.map((q, qIndex) => {
                          const isCorrect =
                            quizSubmitted && userAnswers[qIndex] === q.answer;
                          return (
                            <div
                              key={qIndex}
                              className={`quiz-card ${quizSubmitted ? (isCorrect ? "correct" : "incorrect") : ""}`}
                            >
                              <p className="quiz-question">
                                <span className="q-number">Q{qIndex + 1}</span>
                                {q.question}
                              </p>
                              <div className="quiz-options">
                                {q.options.map((opt, oIndex) => {
                                  let cls = "quiz-option";
                                  if (quizSubmitted) {
                                    if (opt === q.answer) cls += " correct-opt";
                                    else if (opt === userAnswers[qIndex])
                                      cls += " wrong-opt";
                                  } else if (userAnswers[qIndex] === opt) {
                                    cls += " selected-opt";
                                  }
                                  return (
                                    <button
                                      key={oIndex}
                                      className={cls}
                                      onClick={() =>
                                        handleOptionSelect(qIndex, opt)
                                      }
                                    >
                                      {opt}
                                    </button>
                                  );
                                })}
                              </div>
                              {quizSubmitted && (
                                <div className="quiz-explanation">
                                  💡 {q.explanation}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>

                      {!quizSubmitted ? (
                        <div className="submit-row">
                          <span className="answered-count">
                            {answeredCount}/{quiz.length} answered
                          </span>
                          <button
                            onClick={handleSubmitQuiz}
                            className="ask-button submit-btn"
                            disabled={answeredCount < quiz.length}
                          >
                            Submit Quiz
                          </button>
                        </div>
                      ) : (
                        <div className="retake-row">
                          <button
                            onClick={handleRetakeQuiz}
                            className="retake-btn"
                          >
                            🔄 Try Again / Change Difficulty
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              📤 Upload a PDF to start analyzing...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
