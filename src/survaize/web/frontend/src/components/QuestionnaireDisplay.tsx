import React, { useState, useEffect, useRef, useLayoutEffect } from "react";
import CodeMirror, {
  drawSelection,
  gutter,
  highlightActiveLineGutter,
  lineNumbers,
} from "@uiw/react-codemirror";
import { json as jsonMode } from "@codemirror/lang-json";
import { jsonSchema } from "codemirror-json-schema";
import questionnaireCompletionSchema from "../models/questionnaire.schema.json";

import { oneDark } from "@codemirror/theme-one-dark";
import { useQuestionnaire } from "./QuestionnaireComponents";
import RobotReadingAnimation from "./RobotReadingAnimation";
import QuestionItem from "./QuestionItem";
import {
  bracketMatching,
  foldGutter,
  indentOnInput,
} from "@codemirror/language";
import { lintGutter } from "@codemirror/lint";
import {
  autocompletion,
  closeBrackets,
  completionKeymap,
  startCompletion,
} from "@codemirror/autocomplete";
import { EditorView, keymap } from "@codemirror/view";

interface QuestionnaireDisplayProps {
  showRaw: boolean;
  /**
   * Reference to the scrolling container wrapping this component.
   * Used to synchronize scroll position between views.
   */
  containerRef: React.RefObject<HTMLDivElement>;
}

export const QuestionnaireDisplay: React.FC<QuestionnaireDisplayProps> = ({
  showRaw,
  containerRef,
}) => {
  const [editorValue, setEditorValue] = useState<string>("");
  const [parseError, setParseError] = useState<string | null>(null);

  const editorRef = useRef<EditorView | null>(null);
  const questionLineMap = useRef<Array<{ line: number; id: string }>>([]);
  const scrollQuestionRef = useRef<string | null>(null);

  const {
    questionnaire,
    isLoading,
    loadProgress,
    loadMessage,
    setQuestionnaire,
  } = useQuestionnaire();

  useEffect(() => {
    if (questionnaire) {
      const json = JSON.stringify(questionnaire, null, 2);
      setEditorValue(json);
      const lines = json.split("\n");
      const entries: Array<{ line: number; id: string }> = [];
      lines.forEach((line, idx) => {
        const match = line.match(/"id":\s*"([^"]+)"/);
        if (match) {
          entries.push({ line: idx + 1, id: match[1] });
        }
      });
      questionLineMap.current = entries;
      setParseError(null);
    }
  }, [questionnaire]);

  // Custom completion trigger for keyboard shortcuts
  const triggerCompletionSync = (target: EditorView) => {
    return startCompletion(target);
  };

  const handleChange = (value: string): void => {
    try {
      const parsed = JSON.parse(value);
      setQuestionnaire(parsed);
      setParseError(null);
    } catch {
      setParseError("Invalid JSON");
    }
  };

  const getTopQuestionFromFriendly = (): string | null => {
    const container = containerRef.current;
    if (!container) {
      return null;
    }
    const questions = Array.from(
      container.querySelectorAll<HTMLElement>(".question-item"),
    );
    const top = container.scrollTop;
    for (const q of questions) {
      if (q.offsetTop + q.offsetHeight > top) {
        return q.dataset.questionId ?? null;
      }
    }
    return null;
  };

  const scrollFriendlyToQuestion = (id: string) => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const target = container.querySelector<HTMLElement>(
      `.question-item[data-question-id="${id}"]`,
    );
    if (target) {
      container.scrollTop = target.offsetTop;
    }
  };

  const getTopQuestionFromRaw = (): string | null => {
    if (!editorRef.current) {
      return null;
    }
    const view = editorRef.current;
    const block = view.lineBlockAtHeight(view.scrollDOM.scrollTop);
    const lineNumber = view.state.doc.lineAt(block.from).number;
    let current: string | null = null;
    for (const entry of questionLineMap.current) {
      if (entry.line <= lineNumber) {
        current = entry.id;
      } else {
        break;
      }
    }
    return current;
  };

  const scrollRawToQuestion = (id: string) => {
    if (!editorRef.current) {
      return;
    }
    const view = editorRef.current;
    const entry = questionLineMap.current.find((e) => e.id === id);
    if (!entry) {
      return;
    }
    const pos = view.state.doc.line(entry.line).from;
    const block = view.lineBlockAt(pos);
    view.scrollDOM.scrollTop = block.top;
  };

  useLayoutEffect(() => {
    return () => {
      if (showRaw) {
        scrollQuestionRef.current = getTopQuestionFromRaw();
      } else {
        scrollQuestionRef.current = getTopQuestionFromFriendly();
      }
    };
  }, [showRaw]);

  useLayoutEffect(() => {
    const id = scrollQuestionRef.current;
    if (!id) {
      return;
    }
    if (showRaw) {
      scrollRawToQuestion(id);
    } else {
      scrollFriendlyToQuestion(id);
    }
  }, [showRaw]);

  if (isLoading) {
    return (
      <div className="questionnaire-loading">
        <RobotReadingAnimation />
        <p>
          {loadMessage} ({Math.round(loadProgress)}%)
        </p>
        <div className="progress-bar-container">
          <div
            className="progress-bar"
            style={{ width: `${loadProgress}%` }}
          ></div>
        </div>
      </div>
    );
  }

  if (!questionnaire) {
    return (
      <div className="questionnaire-placeholder">
        <p>No questionnaire loaded. Please open a questionnaire file.</p>
      </div>
    );
  }

  return (
    <div className="questionnaire-display">
      {!showRaw && (
        <div className="questionnaire-header">
          <div>
            <h2>{questionnaire.title}</h2>
            {questionnaire.description && <p>{questionnaire.description}</p>}
          </div>
        </div>
      )}

      {showRaw ? (
        <div className="json-display">
          <CodeMirror
            value={editorValue}
            height="500px"
            onCreateEditor={(view) => {
              editorRef.current = view;
            }}
            extensions={[
              gutter({ class: "CodeMirror-lint-markers" }),
              bracketMatching(),
              highlightActiveLineGutter(),
              closeBrackets(),
              lineNumbers(),
              lintGutter(),
              indentOnInput(),
              drawSelection(),
              foldGutter(),
              jsonMode(),
              autocompletion({
                activateOnTyping: true,
                maxRenderedOptions: 20,
                defaultKeymap: true,
              }),
              jsonSchema(questionnaireCompletionSchema),
              keymap.of([
                ...completionKeymap,
                { key: "Ctrl-Space", run: triggerCompletionSync },
                { key: "Alt-Space", run: triggerCompletionSync },
                {
                  key: "Cmd-Space",
                  preventDefault: true,
                  run: triggerCompletionSync,
                }, // Try Cmd+Space too
              ]),
            ]}
            theme={oneDark}
            onChange={handleChange}
          />
          {parseError && <div className="error-message">{parseError}</div>}
        </div>
      ) : (
        <div className="sections-container">
          {questionnaire.sections.map((section) => (
            <div key={section.id} className="section">
              <div className="section-header">
                <h3>
                  {section.number}: {section.title}
                </h3>
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
                {section.questions.map((question) => (
                  <QuestionItem
                    key={question.id}
                    question={question}
                    isIdField={questionnaire.id_fields.includes(question.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
