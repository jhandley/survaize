import { render } from "@testing-library/react";
import React from "react";
import { vi } from "vitest";
import { QuestionnaireDisplay } from "../components/QuestionnaireDisplay";
import { QuestionnaireContext } from "../components/QuestionnaireComponents";
import { Questionnaire } from "../models/questionnaire";

const sample: Questionnaire = {
  title: "Test",
  description: null,
  id_fields: [],
  sections: [],
};

const contextValue: React.ContextType<typeof QuestionnaireContext> = {
  questionnaire: sample,
  setQuestionnaire: vi.fn(),
  isLoading: false,
  setIsLoading: vi.fn(),
  loadProgress: 0,
  setLoadProgress: vi.fn(),
  loadMessage: "",
  setLoadMessage: vi.fn(),
};

test("shows editor when showRaw is true", () => {
  const ref = React.createRef<HTMLDivElement>();
  render(
    <div ref={ref}>
      <QuestionnaireContext.Provider value={contextValue}>
        <QuestionnaireDisplay showRaw={true} containerRef={ref} />
      </QuestionnaireContext.Provider>
    </div>,
  );
  expect(document.querySelector(".cm-editor")).toBeInTheDocument();
  expect(
    document.querySelector(".questionnaire-header"),
  ).not.toBeInTheDocument();
});
