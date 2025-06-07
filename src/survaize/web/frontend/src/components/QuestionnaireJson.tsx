import React, { useState } from 'react';
import { useQuestionnaire } from './QuestionnaireComponents';

export const QuestionnaireJson: React.FC = () => {
  const { questionnaire } = useQuestionnaire();
  const [showRaw, setShowRaw] = useState(false);
  
  if (!questionnaire) {
    return null;
  }

  const toggleRaw = () => {
    setShowRaw(prev => !prev);
  };

  return (
    <div className="questionnaire-json">
      <button 
        onClick={toggleRaw}
        className="toggle-button"
      >
        {showRaw ? 'Hide Raw JSON' : 'Show Raw JSON'}
      </button>
      
      {showRaw && (
        <pre className="json-display">
          {JSON.stringify(questionnaire, null, 2)}
        </pre>
      )}
    </div>
  );
};
