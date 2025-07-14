import React, { useState, useRef } from "react";
import { Questionnaire } from "../models/questionnaire";
import { useApiService } from "../hooks/useApiService";

interface QuestionnaireContextType {
  questionnaire: Questionnaire | null;
  setQuestionnaire: (questionnaire: Questionnaire | null) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  loadProgress: number;
  setLoadProgress: (progress: number) => void;
  loadMessage: string;
  setLoadMessage: (message: string) => void;
}

// Create context with default values
export const QuestionnaireContext =
  React.createContext<QuestionnaireContextType>({
    questionnaire: null,
    setQuestionnaire: () => {},
    isLoading: false,
    setIsLoading: () => {},
    loadProgress: 0,
    setLoadProgress: () => {},
    loadMessage: "",
    setLoadMessage: () => {},
  });

interface QuestionnaireProviderProps {
  children: React.ReactNode;
}

export const QuestionnaireProvider: React.FC<QuestionnaireProviderProps> = ({
  children,
}) => {
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadMessage, setLoadMessage] = useState("");

  const value = {
    questionnaire,
    setQuestionnaire,
    isLoading,
    setIsLoading,
    loadProgress,
    setLoadProgress,
    loadMessage,
    setLoadMessage,
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
    throw new Error(
      "useQuestionnaire must be used within a QuestionnaireProvider",
    );
  }
  return context;
};

// Component for opening a questionnaire
export const OpenQuestionnaire: React.FC = () => {
  const {
    setQuestionnaire,
    isLoading,
    setIsLoading,
    setLoadProgress,
    setLoadMessage,
  } = useQuestionnaire();
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const apiService = useApiService();

  const [processingPdf, setProcessingPdf] = useState(false);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      return;
    }

    const file = files[0];
    const fileExt = file.name.split(".").pop()?.toLowerCase();

    if (fileExt !== "pdf" && fileExt !== "json") {
      setError("Unsupported file format. Please select a PDF or JSON file.");
      return;
    }

    setIsLoading(true);
    setError(null);

    setProcessingPdf(fileExt === "pdf");

    try {
      const loadedQuestionnaire = await apiService.readQuestionnaire(
        file,
        (progress, message) => {
          setLoadProgress(progress);
          setLoadMessage(message);
        },
      );
      setLoadProgress(100);
      setQuestionnaire(loadedQuestionnaire);
    } catch (err) {
      setError(
        `Failed to load questionnaire: ${err instanceof Error ? err.message : "Unknown error"}`,
      );
    } finally {
      setProcessingPdf(false);
      setLoadProgress(0);
      setLoadMessage("");
      setIsLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
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
        style={{ display: "none" }}
        onChange={handleFileChange}
        accept=".pdf,.json"
      />
      <button
        onClick={handleOpenClick}
        disabled={isLoading}
        className="action-button"
      >
        {isLoading
          ? processingPdf
            ? "Processing PDF..."
            : "Opening..."
          : "Open Questionnaire"}
      </button>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

// Component for saving a questionnaire
export const SaveQuestionnaire: React.FC = () => {
  const { questionnaire } = useQuestionnaire();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const downloadRef = useRef<HTMLAnchorElement>(null);

  const apiService = useApiService();

  const handleSave = async (format: "json" | "cspro" | "surveysolutions") => {
    if (!questionnaire) {
      setError("No questionnaire to save. Please open a questionnaire first.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const blob = await apiService.saveQuestionnaire(questionnaire, format);

      const url = URL.createObjectURL(blob);
      if (downloadRef.current) {
        const fileExtension = format === "json" ? "json" : "zip";
        downloadRef.current.href = url;
        downloadRef.current.download = `${questionnaire.title.replace(/\s+/g, "_")}.${fileExtension}`;
        downloadRef.current.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setError(
        `Failed to save questionnaire: ${err instanceof Error ? err.message : "Unknown error"}`,
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="save-actions">
      <button
        onClick={() => handleSave("json")}
        disabled={isLoading || !questionnaire}
        className="action-button"
      >
        {isLoading ? "Saving..." : "Save as JSON"}
      </button>
      <button
        onClick={() => handleSave("cspro")}
        disabled={isLoading || !questionnaire}
        className="action-button"
      >
        {isLoading ? "Saving..." : "Save as CSPro"}
      </button>
      <button
        onClick={() => handleSave("surveysolutions")}
        disabled={isLoading || !questionnaire}
        className="action-button"
      >
        {isLoading ? "Saving..." : "Save as Survey Solutions"}
      </button>
      <a ref={downloadRef} style={{ display: "none" }} />
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};
