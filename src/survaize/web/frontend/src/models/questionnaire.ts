// Questionnaire model types based on the Python models
export enum QuestionType {
  SINGLE_SELECT = "single_select",
  MULTI_SELECT = "multi_select",
  NUMERIC = "numeric",
  TEXT = "text",
  DATE = "date",
  LOCATION = "location",
}

export interface Option {
  code: string;
  label: string;
}

// Base question interface with common properties
export interface BaseQuestion {
  number: string;
  id: string;
  text: string;
  instructions?: string | null;
  universe?: string | null;
  type: QuestionType;
}

export interface NumericQuestion extends BaseQuestion {
  type: QuestionType.NUMERIC;
  min_value?: number | null;
  max_value?: number | null;
  decimal_places?: number | null;
}

export interface TextQuestion extends BaseQuestion {
  type: QuestionType.TEXT;
  max_length?: number | null;
}

export interface SingleChoiceQuestion extends BaseQuestion {
  type: QuestionType.SINGLE_SELECT;
  options: Option[];
}

export interface MultipleChoiceQuestion extends BaseQuestion {
  type: QuestionType.MULTI_SELECT;
  options: Option[];
  min_selections?: number | null;
  max_selections?: number | null;
}

export interface DateQuestion extends BaseQuestion {
  type: QuestionType.DATE;
  min_date?: string | null;
  max_date?: string | null;
}

export interface LocationQuestion extends BaseQuestion {
  type: QuestionType.LOCATION;
  latitude?: number | null;
  longitude?: number | null;
}

// Union type for all question types
export type Question =
  | NumericQuestion
  | TextQuestion
  | SingleChoiceQuestion
  | MultipleChoiceQuestion
  | DateQuestion
  | LocationQuestion;

export interface Section {
  id: string;
  number: string;
  title: string;
  description?: string | null;
  universe?: string | null;
  questions: Question[];
  occurrences: number;
}

export interface Questionnaire {
  title: string;
  description?: string | null;
  id_fields: string[];
  sections: Section[];
}

export interface PartialQuestionnaire {
  sections: Section[];
}
