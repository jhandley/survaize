import { Questionnaire } from '../models/questionnaire';

// Mock questionnaire data for development (fallback if API fails)
export const mockQuestionnaire: Questionnaire = {
  title: "Household Survey",
  description: "A survey about household composition and characteristics",
  id_fields: ["household_id", "region_code"],
  sections: [
    {
      id: "section_a",
      number: "A",
      title: "Household Identification",
      description: "Information to identify the household",
      universe: null,
      questions: [
        {
          number: "A1",
          id: "household_id",
          text: "Household ID",
          type: "text",
          max_length: 10,
        },
        {
          number: "A2",
          id: "region_code",
          text: "Region Code",
          type: "single_select",
          options: [
            { code: "1", label: "North" },
            { code: "2", label: "South" },
            { code: "3", label: "East" },
            { code: "4", label: "West" },
          ],
        }
      ],
      occurrences: 1,
    },
    {
      id: "section_b",
      number: "B",
      title: "Household Member Information",
      description: "Details about each household member",
      universe: null,
      questions: [
        {
          number: "B1",
          id: "name",
          text: "Name of household member",
          type: "text",
          max_length: 50,
        },
        {
          number: "B2",
          id: "age",
          text: "Age in completed years",
          type: "numeric",
          min_value: 0,
          max_value: 120,
        },
        {
          number: "B3",
          id: "gender",
          text: "Gender",
          type: "single_select",
          options: [
            { code: "1", label: "Male" },
            { code: "2", label: "Female" },
            { code: "3", label: "Other" },
          ],
        }
      ],
      occurrences: 10,
    }
  ]
};

// API service for interacting with the backend
export class SurvaizeApiService {
  private baseUrl = '/api';
  private useMockData = false;

  constructor(useMockData = false) {
    this.useMockData = useMockData;
  }

  // Read a questionnaire file (PDF or JSON)
  async readQuestionnaire(file: File): Promise<Questionnaire> {
    console.log(`Reading file: ${file.name}`);
    
    if (this.useMockData) {
      // For development/offline mode, return mock data
      const delay = file.name.endsWith('.pdf') ? 3000 : 500; // Longer delay for PDFs
      await new Promise(resolve => setTimeout(resolve, delay));
      return mockQuestionnaire;
    }
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('format', file.name.endsWith('.pdf') ? 'pdf' : 'json');
      
      // Set a longer timeout for PDF files as they require AI processing
      // TODO: use a better API that supports long operations with progress
      const timeoutMs = file.name.endsWith('.pdf') ? 600000 : 10000; // 60s for PDFs, 10s for JSON
      
      // Create a promise that rejects after the timeout
      const timeoutPromise = new Promise<Response>((_, reject) => {
        setTimeout(() => reject(new Error('Request timed out')), timeoutMs);
      });
      
      // Create the actual fetch promise
      const fetchPromise = fetch(`${this.baseUrl}/questionnaire/read`, {
        method: 'POST',
        body: formData,
      });
      
      // Race the fetch against the timeout
      const response = await Promise.race([fetchPromise, timeoutPromise]) as Response;
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to read questionnaire');
      }
      
      const data = await response.json();
      return data.questionnaire;
    } catch (error) {
      console.error('Error reading questionnaire:', error);
      throw error;
    }
  }

  // Save a questionnaire in specified format
  async saveQuestionnaire(questionnaire: Questionnaire, format: 'json' | 'cspro'): Promise<Blob> {
    console.log(`Saving questionnaire in ${format} format`);
    
    if (this.useMockData) {
      // For development/offline mode, return mock data
      await new Promise(resolve => setTimeout(resolve, 500));
      
      if (format === 'json') {
        const json = JSON.stringify(questionnaire, null, 2);
        return new Blob([json], { type: 'application/json' });
      } else {
        const message = `This would be a CSPro format file for "${questionnaire.title}"`;
        return new Blob([message], { type: 'text/plain' });
      }
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/questionnaire/save/${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(questionnaire),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to save questionnaire in ${format} format`);
      }
      
      return await response.blob();
    } catch (error) {
      console.error(`Error saving questionnaire in ${format} format:`, error);
      
      // Fallback to client-side generation for JSON
      if (format === 'json') {
        console.log('Falling back to client-side JSON generation');
        const json = JSON.stringify(questionnaire, null, 2);
        return new Blob([json], { type: 'application/json' });
      }
      
      throw error;
    }
  }
}
