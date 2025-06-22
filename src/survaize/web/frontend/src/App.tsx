import { useState, useEffect, useRef } from "react";
import {
  QuestionnaireProvider,
  OpenQuestionnaire,
  SaveQuestionnaire,
} from "./components/QuestionnaireComponents";
import { QuestionnaireDisplay } from "./components/QuestionnaireDisplay";

const App: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<string>("");
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null);
  const [showRaw, setShowRaw] = useState<boolean>(false);
  const mainContentRef = useRef<HTMLDivElement>(null);

  const toggleShowRaw = (): void => {
    setShowRaw((prev) => !prev);
  };

  useEffect(() => {
    // Check API health
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) throw new Error("API health check failed");
        setIsApiConnected(true);
        setApiStatus("");
      })
      .catch((error) => {
        console.error("Error fetching API:", error);
        setIsApiConnected(false);
        setApiStatus("⚠️ API connection failed");
      });
  }, []);

  return (
    <QuestionnaireProvider>
      <div className="app-container">
        <div className="top-bar">
          <header className="app-header">
            <h1>Survaize</h1>
            <div
              className={`api-status ${
                isApiConnected === false ? "offline" : ""
              }`}
              style={{ display: isApiConnected === true ? "none" : "block" }}
            >
              {isApiConnected === null ? (
                <span className="loading">Connecting to API...</span>
              ) : isApiConnected === false ? (
                <span className="offline">{apiStatus}</span>
              ) : null}
            </div>
          </header>
          <div className="toolbar">
            <div className="toolbar-left">
              <OpenQuestionnaire />
              <SaveQuestionnaire />
            </div>
            <button
              className="icon-button"
              onClick={toggleShowRaw}
              title={showRaw ? "Show formatted view" : "Show raw JSON"}
            >
              {"{}"}
            </button>
          </div>
        </div>
        <div className="main-content" ref={mainContentRef}>
          <QuestionnaireDisplay
            showRaw={showRaw}
            containerRef={mainContentRef}
          />
        </div>
      </div>
    </QuestionnaireProvider>
  );
};

export default App;
