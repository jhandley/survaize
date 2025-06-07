import { useState, useEffect, JSX } from 'react';

interface ApiResponse {
  message: string;
}

function App(): JSX.Element {
  const [message, setMessage] = useState<string>('Loading...');

  useEffect(() => {
    // Fetch the hello message from the API
    fetch('/api/hello')
      .then(response => response.json())
      .then((data: ApiResponse) => setMessage(data.message))
      .catch(error => {
        console.error('Error fetching API:', error);
        setMessage('Failed to connect to API');
      });
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Survaize</h1>
        <p>Survey Automation Tool</p>
      </header>
      
      <div className="card">
        <h2>API Response</h2>
        <p>{message}</p>
      </div>
    </div>
  );
}

export default App;
