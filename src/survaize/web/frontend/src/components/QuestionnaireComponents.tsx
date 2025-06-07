import React, { useState, useRef, useEffect } from 'react';
import { Questionnaire } from '../models/questionnaire';
import { SurvaizeApiService } from '../services/api';

interface QuestionnaireContextType {
  questionnaire: Questionnaire | null;
  setQuestionnaire: (questionnaire: Questionnaire | null) => void;
  isSaving: boolean;
  isLoading: boolean;
  errorMessage: string | null;
}

// Create context with default values
export const QuestionnaireContext = React.createContext<QuestionnaireContextType>({
  questionnaire: null,
  setQuestionnaire: () => {},
  isSaving: false,
  isLoading: false,
  errorMessage: null
});

interface QuestionnaireProviderProps {
  children: React.ReactNode;
}

export const QuestionnaireProvider: React.FC<QuestionnaireProviderProps> = ({ children }) => {
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const value = {
    questionnaire,
    setQuestionnaire,
    isSaving,
    isLoading,
    errorMessage
  };

  return (
    <QuestionnaireContext.Provider value={value}>
      {children}
    </QuestionnaireContext.Provider>
  );
};

// Custom hook to use the questionnaire context
export const useQuestionnaire = () => {
  const context = React.useContext(QuestionnaireContext);
  if (context === undefined) {
    throw new Error('useQuestionnaire must be used within a QuestionnaireProvider');
  }
  return context;
};

// Component for opening a questionnaire
export const OpenQuestionnaire: React.FC = () => {
  const { setQuestionnaire } = useQuestionnaire();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Check if the API is available or if we're working in offline mode
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const apiService = useRef(new SurvaizeApiService(isOfflineMode));

  // Check API connectivity on mount
  useEffect(() => {
    const checkApiConnection = async () => {
      try {
        const response = await fetch('/api/health');
        const isOffline = !response.ok;
        setIsOfflineMode(isOffline);
        apiService.current = new SurvaizeApiService(isOffline);
      } catch (error) {
        console.warn('API connection failed, using mock data');
        setIsOfflineMode(true);
        apiService.current = new SurvaizeApiService(true);
      }
    };
    
    checkApiConnection();
  }, []);

  const [processingPdf, setProcessingPdf] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      return;
    }

    const file = files[0];
    const fileExt = file.name.split('.').pop()?.toLowerCase();

    if (fileExt !== 'pdf' && fileExt !== 'json') {
      setError('Unsupported file format. Please select a PDF or JSON file.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    // For PDFs, show extended processing feedback since they take longer
    if (fileExt === 'pdf') {
      setProcessingPdf(true);
      // Simulate progress for PDF processing (in a real app, this would come from the server)
      const interval = setInterval(() => {
        setProgress(prev => {
          // Max out at 90% until we get real completion
          const newProgress = prev + (90 - prev) * 0.1;
          return Math.min(newProgress, 90);
        });
      }, 500);
      
      try {
        const loadedQuestionnaire = await apiService.current.readQuestionnaire(file);
        setProgress(100); // Complete the progress
        setTimeout(() => {
          setQuestionnaire(loadedQuestionnaire);
          setProcessingPdf(false);
          setProgress(0);
          setIsLoading(false);
        }, 500);
      } catch (err) {
        setError(`Failed to load questionnaire: ${err instanceof Error ? err.message : 'Unknown error'}`);
        setProcessingPdf(false);
        setProgress(0);
        setIsLoading(false);
      } finally {
        clearInterval(interval);
        // Reset the file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    } else {
      // For JSON files, use the standard loading
      try {
        const loadedQuestionnaire = await apiService.current.readQuestionnaire(file);
        setQuestionnaire(loadedQuestionnaire);
      } catch (err) {
        setError(`Failed to load questionnaire: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setIsLoading(false);
        // Reset the file input
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    }
  };

  const handleOpenClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileChange}
        accept=".pdf,.json"
      />
      <button 
        onClick={handleOpenClick} 
        disabled={isLoading}
        className="action-button"
      >
        {isLoading ? (
          processingPdf ? `Processing PDF (${Math.round(progress)}%)` : 'Opening...'
        ) : 'Open Questionnaire'}
      </button>
      {processingPdf && (
        <div className="progress-bar-container">
          <div 
            className="progress-bar" 
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

// Component for saving a questionnaire
export const SaveQuestionnaire: React.FC = () => {
  const { questionnaire } = useQuestionnaire();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Check if the API is available or if we're working in offline mode
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const apiService = useRef(new SurvaizeApiService(isOfflineMode));

  // Check API connectivity on mount
  useEffect(() => {
    const checkApiConnection = async () => {
      try {
        const response = await fetch('/api/health');
        const isOffline = !response.ok;
        setIsOfflineMode(isOffline);
        apiService.current = new SurvaizeApiService(isOffline);
      } catch (error) {
        console.warn('API connection failed, using mock data');
        setIsOfflineMode(true);
        apiService.current = new SurvaizeApiService(true);
      }
    };
    
    checkApiConnection();
  }, []);

  const handleSave = async (format: 'json' | 'cspro') => {
    if (!questionnaire) {
      setError('No questionnaire to save. Please open a questionnaire first.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Show a warning if in offline mode and trying to save as CSPro
      if (isOfflineMode && format === 'cspro') {
        const confirmOffline = window.confirm(
          'You are in offline mode. CSPro conversion requires a server connection. Continue with a simplified version?'
        );
        if (!confirmOffline) {
          setIsLoading(false);
          return;
        }
      }

      const blob = await apiService.current.saveQuestionnaire(questionnaire, format);
      
      // Create a download link and trigger download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const fileExtension = format === 'json' ? 'json' : (isOfflineMode ? 'txt' : 'zip');
      a.download = `${questionnaire.title.replace(/\s+/g, '_')}.${fileExtension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(`Failed to save questionnaire: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="save-actions">
      <button 
        onClick={() => handleSave('json')} 
        disabled={isLoading || !questionnaire}
        className="action-button"
      >
        {isLoading ? 'Saving...' : 'Save as JSON'}
      </button>
      <button 
        onClick={() => handleSave('cspro')} 
        disabled={isLoading || !questionnaire}
        className="action-button"
      >
        {isLoading ? 'Saving...' : 'Save as CSPro'}
      </button>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};
