import { useState, useEffect, JSX } from 'react';
import { QuestionnaireProvider, OpenQuestionnaire, SaveQuestionnaire } from './components/QuestionnaireComponents';
import { QuestionnaireDisplay } from './components/QuestionnaireDisplay';
import { QuestionnaireJson } from './components/QuestionnaireJson';

interface ApiResponse {
  message: string;
}

function App(): JSX.Element {
  const [apiStatus, setApiStatus] = useState<string>('Checking API status...');
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    // Check API health
    fetch('/api/health')
      .then(response => {
        if (!response.ok) throw new Error('API health check failed');
        return response.json();
      })
      .then((data) => {
        setIsApiConnected(true);
        
        // Now fetch the hello message
        return fetch('/api/hello')
          .then(response => response.json())
          .then((data: ApiResponse) => setApiStatus(`${data.message} ✅`));
      })
      .catch(error => {
        console.error('Error fetching API:', error);
        setIsApiConnected(false);
        setApiStatus('⚠️ API connection failed - working in offline mode');
      });
  }, []);

  return (
    <QuestionnaireProvider>
      <div className="app-container">
        <header className="app-header">
          <h1>Survaize</h1>
          <p>Survey Automation Tool</p>
          <div className={`api-status ${isApiConnected === false ? 'offline' : ''}`}>
            {isApiConnected === null ? (
              <span className="loading">Connecting to API...</span>
            ) : isApiConnected === true ? (
              <span className="online">{apiStatus}</span>
            ) : (
              <span className="offline">{apiStatus}</span>
            )}
          </div>
        </header>
        
        <div className="toolbar">
          <OpenQuestionnaire />
          <SaveQuestionnaire />
        </div>
        
        <div className="main-content">
          <QuestionnaireDisplay />
          <QuestionnaireJson />
        </div>
      </div>
    </QuestionnaireProvider>
  );
}

export default App;
