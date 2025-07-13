"""Module for interpreting questionnaire documents using LLMs."""

import base64
import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import TypeVar

import logfire
from openai import AzureOpenAI, OpenAI
from openai.types.chat import (
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
)
from PIL import Image
from pydantic import BaseModel

from survaize.config.llm_config import LLMConfig
from survaize.interpreter.openai_recorder import (
    RecordingClient,
    create_openai_client,
)
from survaize.interpreter.scanned_questionnaire import ScannedQuestionnaire
from survaize.model.questionnaire import (
    PartialQuestionnaire,
    Questionnaire,
    Section,
    SectionFragment,
    TrailingSectionRef,
    merge_questionnaires,
)

# Configure logger
logger = logging.getLogger(__name__)

STRUCTURED_RESPONSE_TYPE = TypeVar("STRUCTURED_RESPONSE_TYPE", bound="BaseModel")


@dataclass
class LLMUsage:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class AIQuestionnaireInterpreter:
    """Interprets questionnaire documents using LLM vision models."""

    def __init__(self, llm_config: LLMConfig, max_retries: int = 10, sleep_between_pages_seconds: int = 0):
        """Initialize the interpreter.

        Args:
            llm_config: Configuration/keys for the OpenAI API
        """
        self.llm_config: LLMConfig = llm_config
        self.client: AzureOpenAI | OpenAI | RecordingClient = create_openai_client(llm_config)
        self.max_retries: int = max_retries
        self.sleep_between_pages_seconds: int = sleep_between_pages_seconds

    @logfire.instrument(extract_args=False)
    def interpret(
        self,
        scanned_document: ScannedQuestionnaire,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> Questionnaire:
        """Interpret a questionnaire document into a structured format.

        Args:
            scanned_document: QuestionnaireDocument containing page images. The
                OCR text may be omitted.

        Returns:
            Structured Questionnaire object
        """
        # Reset current state for a new interpretation
        current_state = None

        # Process each page
        total_pages = len(scanned_document.pages)
        total_usage = LLMUsage()

        context: list[SectionFragment] = []
        texts = (
            scanned_document.extracted_text if scanned_document.extracted_text else ["" for _ in scanned_document.pages]
        )
        for i, (page, text) in enumerate(
            zip(scanned_document.pages, texts, strict=True),
            1,
        ):
            if progress_callback:
                percent = int(100 * (i - 1) / total_pages)
                progress_callback(percent, f"Examining page {i}/{total_pages}")

            logger.info(f"Examining page {i}/{total_pages}")
            if i == 1:
                questionnaire, usage = self._process_first_page(page, text)
                context = self._build_context(questionnaire.trailing_sections, questionnaire.sections)
                current_state = questionnaire
            else:
                assert current_state is not None
                partial, usage = self._process_subsequent_page(page, text, i, context)
                context = self._build_context(partial.trailing_sections, partial.sections)
                current_state = merge_questionnaires(current_state, partial)
            total_usage.add(usage.prompt_tokens, usage.completion_tokens)
            if i < total_pages:
                # Sleep between pages to avoid hitting rate limits or overwhelming the model
                logger.info(f"Waiting for {self.sleep_between_pages_seconds} seconds before next page")
                time.sleep(self.sleep_between_pages_seconds)

        if current_state is None:
            raise ValueError("No valid questionnaire found in the document")
        if progress_callback:
            progress_callback(100, "Completed")
        logger.info(
            "Token usage - prompt: %s, completion: %s, total: %s",
            total_usage.prompt_tokens,
            total_usage.completion_tokens,
            total_usage.total_tokens,
        )
        return current_state

    def _process_first_page(self, image: Image.Image, ocr_text: str) -> tuple[Questionnaire, LLMUsage]:
        """Process the first page of the questionnaire.

        Args:
            image: PIL Image of the page
            ocr_text: OCR extracted text from the page

        Returns:
            Tuple containing the structured questionnaire and token usage

        Raises:
            ValueError: If unable to interpret the questionnaire after max retry attempts
        """
        # Encode image for API
        base64_image = self._encode_image(image)

        # Initialize conversation history
        prompt = self._create_vision_prompt(1)
        message: Iterable[ChatCompletionContentPartParam] = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            },
            {"type": "text", "text": f"OCR Text:\n{ocr_text}"},
        ]
        return self._get_structured_llm_response(message, Questionnaire)

    def _process_subsequent_page(
        self,
        image: Image.Image,
        ocr_text: str,
        page_number: int,
        previous_context: list[SectionFragment],
    ) -> tuple[PartialQuestionnaire, LLMUsage]:
        """Process a single page of the questionnaire.
        This method is called for all pages after the first one.

        Args:
            image: PIL Image of the page
            ocr_text: OCR extracted text from the page
            page_number: Current page number
            previous_context: Trailing sections from the previous page

        Returns:
            Tuple with the partial questionnaire from this page and token usage

        Raises:
            ValueError: If unable to interpret the page after max retry attempts
        """
        # Encode image for API
        base64_image = self._encode_image(image)

        # Initialize conversation
        prompt = self._create_vision_prompt(page_number)
        context_json = json.dumps(
            [section.model_dump(exclude_none=True) for section in previous_context],
            indent=2,
        )
        message: Iterable[ChatCompletionContentPartParam] = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            },
            {"type": "text", "text": f"OCR Text:\n{ocr_text}"},
            {
                "type": "text",
                "text": f"previous_page_context:\n{context_json}",
            },
        ]
        return self._get_structured_llm_response(message, PartialQuestionnaire)

    def _get_structured_llm_response(
        self, message: Iterable[ChatCompletionContentPartParam], response_type: type[STRUCTURED_RESPONSE_TYPE]
    ) -> tuple[STRUCTURED_RESPONSE_TYPE, LLMUsage]:
        """Get structured response from LLM by asking LLM to fix validation errors in a loop.
        Args:
            message: Message to send to the LLM
            response_type: Type of the expected structured response
        Returns:
            Tuple of the structured response and token usage
        Raises:
            ValueError: If unable to validate the response after max retry attempts
        """

        # Track conversation to maintain context during retries
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": message}]

        usage = LLMUsage()
        attempt = 0

        while True:
            attempt += 1

            # Make API call
            response = self.client.chat.completions.create(
                model=self.llm_config.model,
                messages=messages,
                response_format={"type": "json_object"},
            )

            if getattr(response, "usage", None):
                usage.add(
                    getattr(response.usage, "prompt_tokens", 0) or 0,
                    getattr(response.usage, "completion_tokens", 0) or 0,
                )

            # Extract content
            response_str = response.choices[0].message.content
            if not response_str:
                raise ValueError(f"Refusal from OpenAI: {response.choices[0].message.refusal}")

            # Add assistant's response to conversation history
            messages.append({"role": "assistant", "content": response_str})

            try:
                # Try to validate the response
                validated_response = response_type.model_validate(json.loads(response_str))
                return validated_response, usage

            except Exception as e:
                if attempt >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) reached. Last error: {e}")
                    logger.error(f"Raw response: {response}")
                    raise ValueError(f"Unable to validate response after {self.max_retries} attempts: {e}") from e

                # Prepare error feedback for the model
                error_prompt = f"""
                Your previous response had validation errors:
                
                Error: {str(e)}
                
                Please fix the JSON structure to conform to the PartialQuestionnaire schema. Ensure all required fields 
                are present and correctly typed. Return only the corrected JSON.
                """

                # Add error feedback to conversation history
                messages.append({"role": "user", "content": error_prompt})

                logger.info(f"Validation failed, attempt {attempt}: {e}. Retrying...")

    def _build_context(
        self,
        refs: list[TrailingSectionRef],
        sections: list[Section],
    ) -> list[SectionFragment]:
        """Construct context fragments from trailing section references."""

        sections_by_id = {section.id: section for section in sections}
        fragments: list[SectionFragment] = []
        for ref in refs:
            section = sections_by_id.get(ref.id)
            if not section:
                continue
            trailing_questions = [q for q in section.questions if q.id in ref.question_ids]
            if trailing_questions:
                fragments.append(
                    SectionFragment(
                        id=section.id,
                        number=section.number,
                        title=section.title,
                        questions=trailing_questions,
                    )
                )
        return fragments

    def _encode_image(self, image: Image.Image) -> str:
        """Encode a PIL image to base64.

        Args:
            image: PIL Image to encode

        Returns:
            Base64 encoded image string
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _create_vision_prompt(self, page_number: int) -> str:
        """Create the prompt for GPT-4 Vision.

        Args:
            page_number: Current page number

        Returns:
            Prompt string
        """
        schema_example = """
            {
                "title": "Survey Title",
                "description": "A national household survey",
                "id_fields": ["cluster", "household number"],
                "sections": [
                    {
                        "id": "section_a",
                        "number": "A",
                        "title": "Household Information",
                        "description": "Basic information about the household",
                        "universe": "Respondents over 18 years old",
                        "occurrences": 20,
                        "questions": [
                            {
                                "number": "A1",
                                "id": "cluster",
                                "text": "Enter cluster number for household from sample",
                                "type": "numeric",
                                "max_length": 99
                            },
                            {
                                "number": "A2",
                                "id": "household number",
                                "text": "Enter household number from sample",
                                "type": "numeric",
                                "max_length": 999
                            },
                            {
                                "number": "A3",
                                "id": "name",
                                "text": "What is your name?",
                                "type": "text",
                                "instructions": "Please enter the full name",
                                "max_length": 99
                            },
                            {
                                "number": "A4",
                                "id": "name",
                                "text": "What is your name?",
                                "type": "text",
                                "instructions": "Please enter the full name",
                                "max_length": 99
                            },
                            {
                                "number": "A5",
                                "id": "age",
                                "text": "What is your age?",
                                "type": "numeric",
                                "instructions": "Please enter the age in years",
                                "min_value": 0,
                                "max_value": 99
                            },
                            {
                                "number": "A6",
                                "id": "birth_date",
                                "text": "What is your date of birth?",
                                "type": "date"
                            },
                            {
                                "number": "A7",
                                "id": "gender",
                                "text": "What is your gender?",
                                "type": "single_select",
                                "options": [{"code": "1", "label": "Male"}, {"code": "2", "label": "Female"}]
                            }
                        ]
                    }
                ],
                "trailing_sections": [
                    {"id": "section_a", "question_ids": ["gender"]}
                ]
            }
        """

        partial_example = """
            {
                "sections": [
                    {
                        "id": "section_b",
                        "number": "B",
                        "title": "Education Information",
                        "description": "Information about educational background",
                        "universe": "Household members aged 5 and above",
                        "occurrences": 50,
                        "questions": [
                            {
                                "number": "B1",
                                "id": "edu_level",
                                "text": "What is the highest level of education completed?",
                                "type": "single_select",
                                "options": [
                                    {"code": "1", "label": "None"},
                                    {"code": "2", "label": "Primary"},
                                    {"code": "3", "label": "Secondary"},
                                    {"code": "4", "label": "Tertiary"}
                                ]
                            }
                        ]
                    }
                ],
                "trailing_sections": [
                    {"id": "section_b", "question_ids": ["edu_level"]}
                ]
            }
        """

        if page_number == 1:
            return f"""You are an expert in implementing CAPI survey instruments for surveys. Your job is to read a
            paper questionnaire and convert it to a structured format that can be used for further processing.
                    
            Given the first page of a questionnaire as an image, along with the OCR text from the page, produce a JSON
            representation of the page of the questionnaire that follows the example. Include all sections and questions
            found on this page in normal reading order. If the order is unclear visually, use the section and question
            numbers to determine the order.
            
            Include a `trailing_sections` field listing the ids of any sections/questions that may continue on
            the next page. These are sections with questions that appear incomplete, are part of a sequence or have
            been split across pages, usually the last question in each column.

            Proceed as follows:

            1. Identify the title of the survey (required)
            2. Identify any description of the survey (required)
            3. Identify the sections of the survey and extract the following information:
                - Section ID - derived from the title, lowercase with underscores (required)
                - Section number (required, number with sequential capital letters if missing, however if previous 
                  sections are numbered and this one is not, it is probably part of a previous section)
                - Section title (required)
                - Section description (if present)
                - Universe (which respondent the section is intended for, if present)
                - Occurrences (how many times the section is repeated. Repeated sections are often represented as
                  tables with multiple rows in which case count the rows, otherwise estimate based on the 
                  topic/questions in the section e.g. if the section is about household members, it may be repeated 
                  for each member of the household)
                  **Always include this field with an integer value, even if it must be estimated.**
            4. In each section identify the individual questions and extract the following information:
                - Question number (required, number sequentially if missing)
                - Question ID - derived from the question, lowercase with underscores (required)
                - Text of the question to be read to the respondent (required)
                - Instructions to the interviewer (if present)
                - Question type (either single_select, multi_select, numeric, text, date, location) (required).
                  **Only use these exact values; do not create new question types.**
                - Single_select and multi_select questions will have a list of responses; for those questions
                  extract the code and label for each response. **Every option needs a code; use numbers if missing.**
                - Numeric questions will have a minimum maximum value which can be inferred. For the maximum, 
                  examine the image of the question, determine the number of digits allowed for the response represented
                  as boxes next to or under the question. For example, if the question has 2 boxes next to it, the 
                  maximum is 99. If the length cannot be determined from the image, infer a reasonable value based on 
                  the question itself. For example, if the question is about age, the maximum is 120 since that is an
                  upper limit for the age of a human being. For the minimum, infer a reasonable value based on the
                  question. If there is no information to infer the minimum and maximum values, omit them from the 
                  output.
                - Text questions will have a maximum length which can be inferred based on the number of boxes next to
                  or under the question, if there is no information to infer the maximum length, omit the field from 
                  the output
            5. Identify the id-fields for the questionnaire. These must be a subset of the ids from questions in the
               questionnaire. They are usually at the start of the questionnaire and combined will uniquely identify
               the questionnaire. They are often geographic identifiers, household identifiers, or respondent
               identifiers or codes from the sample.
            6. Ensure every object includes all required properties. Provide a best guess or placeholder when the 
               value is not explicit rather than omitting the field.

            Here is an example of the output you should produce:
            ```json
            {schema_example}
            ```
            """
        else:
            return f"""You are an expert in implementing CAPI survey instruments for surveys. Your job is to read a
            paper questionnaire and convert it to a structured format that can be used for further processing.

            Given page {page_number} of a questionnaire as an image, along with the OCR text from the page, produce a
            JSON representation of just the sections and questions found on this page that follows the example. 
            Include all sections and questions found on this page in normal reading order. If the order is unclear 
            visually, use the section and question numbers to determine the order.
                        
            Also include a `trailing_sections` field listing the ids of any sections/questions that may continue on
            the next page. These are sections with questions that appear incomplete, are part of a sequence or have
            been split across pages, usually the last question in each column.

            Proceed as follows:

            1. Identify any new sections that begin on this page and extract the following information:
                - Section ID - derived from the title, lowercase with underscores (required)
                - Section number (required, number with sequential capital letters if missing, however if previous 
                  sections are numbered and this one is not, it is probably part of a previous section)
                - Section title (required)
                - Section description (if present)
                - Universe (which respondent the section is intended for, if present)
                - Occurrences (how many times the section is repeated. Repeated sections are often represented as
                  tables with multiple rows in which case count the rows, otherwise estimate based on the 
                  topic/questions in the section e.g. if the section is about household members, it may be repeated 
                  for each member of the household)
                  **Always include this field with an integer value, even if it must be estimated.**
            2. For questions that belong to a section from a previous page, include that section with its ID but only
               the new questions. The `previous_page_context` contains the last sections and questions from the 
               previous page that may continue on this page.

            3. Identify the individual questions and extract the following information:
                - Question number (required, number sequentially if missing)
                - Question ID - derived from the question, lowercase with underscores (required)
                - Text of the question to be read to the respondent (required)
                - Instructions to the interviewer (if present)
                - Question type (either single_select, multi_select, numeric, text, date, location) (required).
                  **Only use these exact values; do not create new question types.**
                - Single_select and multi_select questions will have a list of responses; for those questions
                  extract the code and label for each response. **Every option needs a code; use numbers if missing.**
                - Numeric questions will have a minimum maximum value which can be inferred. For the maximum, 
                  examine the image of the question, determine the number of digits allowed for the response represented
                  as boxes next to or under the question. For example, if the question has 2 boxes next to it, the 
                  maximum is 99. If the length cannot be determined from the image, infer a reasonable value based on 
                  the question itself. For example, if the question is about age, the maximum is 120 since that is an
                  upper limit for the age of a human being. For the minimum, infer a reasonable value based on the
                  question. If there is no information to infer the minimum and maximum values, omit them from the 
                  output.
                - Text questions will have a maximum length which can be inferred based on the number of boxes next to
                  or under the question, if there is no information to infer the maximum length, omit the field from 
                  the output
            4. Ensure every object includes all required properties. Provide a best guess or placeholder when the value 
               is not explicit rather than omitting the field.

            Here is an example of the output you should produce:
            ```json
            {partial_example}
            ```
            """
