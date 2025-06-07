import React from 'react';
import { useQuestionnaire } from './QuestionnaireComponents';
import { Question, QuestionType } from '../models/questionnaire';

// Helper function to render different question types
const renderQuestion = (question: Question) => {
  let details = null;

  switch (question.type) {
    case QuestionType.SINGLE_SELECT:
    case QuestionType.MULTI_SELECT:
      details = (
        <div className="question-options">
          <span className="option-label">Options:</span>
          <ul>
            {question.options.map(option => (
              <li key={option.code}>
                <code>{option.code}</code>: {option.label}
              </li>
            ))}
          </ul>
        </div>
      );
      break;
      
    case QuestionType.NUMERIC:
      details = (
        <div className="question-constraints">
          {question.min_value !== null && <div>Min: {question.min_value}</div>}
          {question.max_value !== null && <div>Max: {question.max_value}</div>}
          {question.decimal_places !== null && <div>Decimal places: {question.decimal_places}</div>}
        </div>
      );
      break;
      
    case QuestionType.TEXT:
      details = question.max_length ? 
        <div className="question-constraints">Max length: {question.max_length}</div> : null;
      break;
      
    case QuestionType.DATE:
      details = (
        <div className="question-constraints">
          {question.min_date && <div>Min date: {question.min_date}</div>}
          {question.max_date && <div>Max date: {question.max_date}</div>}
        </div>
      );
      break;
      
    case QuestionType.LOCATION:
      details = (
        <div className="question-constraints">
          <div>Geographic coordinates (latitude, longitude)</div>
        </div>
      );
      break;
  }

  return (
    <div className="question-item" key={question.id}>
      <div className="question-header">
        <span className="question-number">{question.number}</span>
        <span className="question-id">[{question.id}]</span>
        <span className="question-type">{question.type}</span>
      </div>
      
      <div className="question-text">{question.text}</div>
      
      {question.instructions && (
        <div className="question-instructions">
          <em>Instructions: {question.instructions}</em>
        </div>
      )}
      
      {question.universe && (
        <div className="question-universe">
          <strong>Universe:</strong> {question.universe}
        </div>
      )}
      
      {details}
    </div>
  );
};

export const QuestionnaireDisplay: React.FC = () => {
  const { questionnaire } = useQuestionnaire();

  if (!questionnaire) {
    return (
      <div className="questionnaire-placeholder">
        <p>No questionnaire loaded. Please open a questionnaire file.</p>
      </div>
    );
  }

  return (
    <div className="questionnaire-display">
      <div className="questionnaire-header">
        <h2>{questionnaire.title}</h2>
        {questionnaire.description && <p>{questionnaire.description}</p>}
        <div className="id-fields">
          <strong>ID Fields:</strong> {questionnaire.id_fields.join(', ')}
        </div>
      </div>
      
      <div className="sections-container">
        {questionnaire.sections.map(section => (
          <div key={section.id} className="section">
            <div className="section-header">
              <h3>{section.number}: {section.title}</h3>
              {section.description && <p>{section.description}</p>}
              {section.universe && (
                <div className="section-universe">
                  <strong>Universe:</strong> {section.universe}
                </div>
              )}
              {section.occurrences > 1 && (
                <div className="section-occurrences">
                  <strong>Repeats:</strong> up to {section.occurrences} times
                </div>
              )}
            </div>
            
            <div className="questions-list">
              {section.questions.map(question => renderQuestion(question))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
