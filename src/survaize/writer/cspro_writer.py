import json
import logging
from pathlib import Path
from typing import Literal

import logfire

from survaize.cspro.dictionary import (
    CSProDictionary,
    DictionaryIds,
    DictionaryItem,
    DictionaryLabel,
    DictionaryLevel,
    DictionaryRecord,
    DictionaryRecordOccurrences,
    DictionaryValue,
    DictionaryValueSet,
)
from survaize.cspro.form import (
    Form,
    FormField,
    FormFile,
    FormGroup,
    FormItemCaptureType,
    FormItemType,
    FormLevel,
    FormText,
    Roster,
    RosterColumn,
)
from survaize.cspro.question_text import QsfCondition, QsfFile, QsfLanguage, QsfQuestion, QsfStyle, QsfText
from survaize.model.questionnaire import (
    MultipleChoiceQuestion,
    Question,
    Questionnaire,
    QuestionType,
    SingleChoiceQuestion,
)

# Configure logger
logger = logging.getLogger(__name__)


class CSProWriter:
    """Generates CSPro format output from questionnaires."""

    @logfire.instrument()
    def write(self, questionnaire: Questionnaire, output_path: Path):
        """Generate a CSPro application from a questionnaire.

        This method creates a directory with all necessary CSPro files.

        Args:
            questionnaire: The structured questionnaire data
            output_path: Path where the generated CSPro files should be saved

        Returns:
            Path to the generated CSPro application directory
        """
        # Create a directory for the CSPro application
        app_file_name = self._make_file_name(questionnaire.title)
        app_dir = output_path
        app_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generating CSPro application in: {app_dir}")

        # Generate all required CSPro files
        dictionary, dict_item_to_question = self._generate_data_dictionary(questionnaire)
        dictionary_file_name = f"{app_file_name}.dcf"
        dictionary.save(app_dir / dictionary_file_name)

        form_file = self._generate_form_file(dictionary, dictionary_file_name, dict_item_to_question)
        form_file.save(app_dir / f"{app_file_name}.fmf")
        self._generate_logic_file(questionnaire, app_dir / f"{app_file_name}.ent.apc")
        qsf_file = self._generate_question_text_file(questionnaire, dictionary.name)
        qsf_file.save(app_dir / f"{app_file_name}.ent.qsf")
        self._generate_application_file(questionnaire, app_dir / f"{app_file_name}.ent")
        self._generate_message_file(questionnaire, app_dir / f"{app_file_name}.ent.mgf")
        self._generate_pff_file(questionnaire, app_dir / f"{app_file_name}.pff")

        logger.info("CSPro application generated successfully")

    def _make_file_name(self, name: str) -> str:
        """Convert a title to a valid CSPro filename.

        Args:
            name: The title to sanitize

        Returns:
            A sanitized name suitable for a CSPro application
        """
        # Remove spaces and special characters
        sanitized = "".join(c if c.isalnum() else "" for c in name)
        return sanitized

    def _generate_data_dictionary(self, questionnaire: Questionnaire) -> tuple[CSProDictionary, dict[str, Question]]:
        """Generate the CSPro data dictionary from the questionnaire.

        Args:
            questionnaire: The questionnaire data

        Returns:
            The generated CSPro dictionary and a mapping of dictionary item to question that it was created from
        """
        logger.info("Generating data dictionary")

        # Create dictionary name from questionnaire title
        dict_name = self._to_dictionary_name(f"{questionnaire.title}_DICT")

        # Create a dictionary level (CSPro dictionaries can have multiple levels, but we use only one)
        level_name = self._to_dictionary_name(f"{questionnaire.title}_LEVEL")

        dict_item_to_question: dict[str, Question] = {}

        # Create dictionary to track ID questions for easy lookup
        id_question_ids = set(questionnaire.id_fields)

        # Find all ID questions and create ID items
        id_items: list[DictionaryItem] = []

        # First pass: Find all ID questions and organize them by section
        for section in questionnaire.sections:
            for question in section.questions:
                if question.id in id_question_ids:
                    id_item = self._question_to_dictionary_item(question)
                    dict_item_to_question[id_item.name] = question
                    id_items.append(id_item)

        # Create records for each section (excluding empty sections)
        records: list[DictionaryRecord] = []
        for section in questionnaire.sections:
            # Create a record for this section with non-ID questions
            record_items: list[DictionaryItem] = []

            # If all questions in this section are ID fields, skip creating a record
            section_has_non_id_questions = any(question.id not in id_question_ids for question in section.questions)

            if not section_has_non_id_questions:
                # All questions in this section are ID fields, don't create a record
                logger.info(f"Skipping record for section {section.id} (all questions are ID fields)")
                continue

            # Add only non-ID questions to the record
            for question in section.questions:
                if question.id not in id_question_ids:
                    item = self._question_to_dictionary_item(question)
                    dict_item_to_question[item.name] = question
                    record_items.append(item)

            # Only create record if it has items
            if record_items:
                record = DictionaryRecord(
                    name=self._to_dictionary_name(f"{section.id}_REC"),
                    labels=[DictionaryLabel(text=self._to_dictionary_label(section.number, section.id))],
                    recordType=section.number[0],  # Use first letter of section number as record type
                    items=record_items,
                    occurrences=DictionaryRecordOccurrences(required=False, maximum=section.occurrences),
                )
                records.append(record)

        # Create the level
        level = DictionaryLevel(
            name=level_name,
            labels=[DictionaryLabel(text=f"{questionnaire.title} Level")],
            ids=DictionaryIds(items=id_items),
            records=records,
        )

        # Create the complete dictionary
        dictionary = CSProDictionary(
            name=dict_name,
            labels=[DictionaryLabel(text=f"{questionnaire.title} Dictionary")],
            levels=[level],
        )

        return dictionary, dict_item_to_question

    def _question_to_dictionary_item(self, question: Question) -> DictionaryItem:
        """Convert a questionnaire question to a CSPro dictionary item.

        Args:
            question: The question to convert

        Returns:
            A CSPro dictionary item representing the question
        """
        # Determine content type and length based on question type
        content_type: Literal["numeric", "alpha"] = "alpha"
        length = 25  # Default length for text
        value_sets = None
        label = self._to_dictionary_label(question.number, question.id)

        if question.type == QuestionType.NUMERIC:
            content_type = "numeric"
            # Determine appropriate length for numeric fields based on max_value
            if question.max_value:
                length = len(str(int(question.max_value)))
                # Minimum length is 1
                length = max(1, length)
            else:
                length = 15  # Default numeric length

        elif question.type == QuestionType.TEXT:
            content_type = "alpha"
            length = question.max_length if question.max_length else 100

        elif question.type == QuestionType.SINGLE_SELECT:
            content_type = "numeric"  # TODO: use alpha if any options are alphanumeric
            length = 1  # Default for single select codes
            # Get max length of codes to determine field length
            if question.options:
                max_code_length = max(len(option.code) for option in question.options)
                length = max_code_length

            # Create value set for the options
            value_sets = [self._create_value_set(label, question)]

        elif question.type == QuestionType.MULTI_SELECT:
            content_type = "alpha"
            # For multi-select, we need enough space to store all selected codes
            if question.options:
                # Each code needs its own space
                length = sum(len(option.code) for option in question.options)

            # Create value set for the options
            value_sets = [self._create_value_set(label, question)]

        elif question.type == QuestionType.DATE:
            content_type = "numeric"
            length = 8  # YYYYMMDD format

        elif question.type == QuestionType.LOCATION:
            # TODO: Use two float fields for lat/lon
            content_type = "alpha"
            length = 25  # Enough for lat,lon

        # Create the item
        item = DictionaryItem(
            name=self._to_dictionary_name(question.id),
            labels=[DictionaryLabel(text=label)],
            contentType=content_type,
            length=length,
        )

        # Add zeroFill for numeric fields
        if content_type == "numeric":
            item.zeroFill = True

        # Add value sets if applicable
        if value_sets:
            item.valueSets = value_sets

        return item

    def _create_value_set(self, label: str, question: Question) -> DictionaryValueSet:
        """Create a CSPro value set for a question with options.

        Args:
            question: The question with options to convert

        Returns:
            A CSPro dictionary value set
        """
        if question.type not in [QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT]:
            raise ValueError(f"Cannot create value set for question type: {question.type}")

        assert isinstance(question, SingleChoiceQuestion | MultipleChoiceQuestion)

        values: list[DictionaryValue] = []

        # Add each option as a value
        for option in question.options:
            value = DictionaryValue(
                labels=[DictionaryLabel(text=option.label)],
                pairs=[{"value": option.code}],
            )
            values.append(value)

        # Create the value set
        value_set = DictionaryValueSet(
            name=self._to_dictionary_name(f"{question.id}_VS1"),
            labels=[DictionaryLabel(text=label)],
            values=values,
        )

        return value_set

    def _to_dictionary_name(self, identifier: str) -> str:
        """Convert any string to a valid CSPro dictionary symbol.

        CSPro dictionary symbols must:
        1. Start with a letter (A-Z)
        2. Contain only letters, numbers, and underscores
        3. Be uppercase

        This implementation properly handles accented characters and
        follows CSPro naming conventions.

        Args:
            identifier: The string to convert to a valid CSPro symbol

        Returns:
            A valid CSPro symbol name
        """
        # First convert to uppercase
        text = identifier.upper()

        # Replace accented characters with their non-accented equivalents
        accent_map = {
            "À": "A",
            "Á": "A",
            "Â": "A",
            "Ã": "A",
            "Ä": "A",
            "Å": "A",
            "Ç": "C",
            "È": "E",
            "É": "E",
            "Ê": "E",
            "Ë": "E",
            "Ì": "I",
            "Í": "I",
            "Î": "I",
            "Ï": "I",
            "Ñ": "N",
            "Ò": "O",
            "Ó": "O",
            "Ô": "O",
            "Õ": "O",
            "Ö": "O",
            "Ù": "U",
            "Ú": "U",
            "Û": "U",
            "Ü": "U",
        }

        # Process character by character
        result: list[str] = []
        prev_char_underscore = False

        for char in text:
            # Replace accented characters
            char = accent_map.get(char, char)

            # Check if character is valid for CSPro names (letters, digits, underscore)
            if char.isalnum():
                result.append(char)
                prev_char_underscore = False
            else:
                # Convert invalid characters to underscore
                # But avoid consecutive underscores
                if not prev_char_underscore:
                    result.append("_")
                    prev_char_underscore = True

        # Convert to string
        result_str = "".join(result)

        # Strip off non-alphabetic characters from beginning
        while result_str and not result_str[0].isalpha():
            result_str = result_str[1:]

        # Strip trailing underscores
        result_str = result_str.rstrip("_")

        # If empty, provide a default name
        if not result_str:
            result_str = "NAME"

        return result_str

    def _to_dictionary_label(self, number: str, id: str) -> str:
        """Convert id from JSON questionnaire to human friendly label.
        Replaces underscores with spaces and capitalizes words.

        Args:
            identifier: The string to convert to a label

        Returns:
            label: A human-friendly label
        """
        friendly_id = id.replace("_", " ").title()
        return f"{number} {friendly_id}" if number else friendly_id

    def _get_capture_type(
        self, item: DictionaryItem, dict_item_to_question: dict[str, Question]
    ) -> FormItemCaptureType:
        """Determine the appropriate FormItemCaptureType for a given question and dictionary item.

        Args:
            item: The corresponding DictionaryItem
            dict_item_to_question: Mapping of DictionaryItem to Question

        Returns:
            The FormItemCaptureType to use for the form field
        """
        original_question = dict_item_to_question[item.name]
        if original_question.type == QuestionType.SINGLE_SELECT:
            return FormItemCaptureType.RADIO_BUTTON
        elif original_question.type == QuestionType.MULTI_SELECT:
            return FormItemCaptureType.CHECK_BOX
        elif original_question.type == QuestionType.NUMERIC or original_question.type == QuestionType.TEXT:
            return FormItemCaptureType.TEXT_BOX
        elif original_question.type == QuestionType.DATE:
            return FormItemCaptureType.DATE
        else:
            return FormItemCaptureType.TEXT_BOX

    def _create_items_form(
        self,
        items: list[DictionaryItem],
        dict_item_to_question: dict[str, Question],
        form_number: int,
        form_name: str,
        label: str,
        required: bool = True,
        max_occurs: int = 1,
    ) -> tuple[Form, FormGroup]:
        """Helper to create a form and group for a list of items (ID or record items)."""
        ROW_OFFSET = 30
        LABEL_CHAR_SIZE = 9
        LABEL_WIDTH_PADDING = 20
        FIELD_WIDTH_CHAR_SIZE = 15
        FIELD_HEIGHT = 20

        form = Form(
            name=form_name,
            label=label,
            form_file_number=form_number,
            level=1,
            size=(300, 300),  # CSPro will resize this for us on load
            items=[],
        )
        group = FormGroup(
            name=form_name,
            label=label,
            form_file_number=form_number,
            item_type=FormItemType.GROUP,
            required=required,
            max=max_occurs,
            items=[],
        )
        row = 27
        max_label_length = max(len(item.labels[0].text) for item in items)
        label_width = max_label_length * LABEL_CHAR_SIZE + LABEL_WIDTH_PADDING
        for item in items:
            label_x = 50
            field_text_label = FormText(
                name=f"{item.name}_LABEL",
                label=item.labels[0].text,
                form_file_number=form_number,
                item_type=FormItemType.TEXT,
                text=item.labels[0].text,
                position=(label_x, row, label_x + label_width, row + FIELD_HEIGHT),
            )

            capture_type = self._get_capture_type(item, dict_item_to_question)

            field_x = label_x + label_width
            field_width = item.length * FIELD_WIDTH_CHAR_SIZE
            field = FormField(
                name=item.name,
                label=item.labels[0].text,
                form_file_number=form_number,
                item_type=FormItemType.FIELD,
                text=field_text_label,
                position=(field_x, row, field_x + field_width, row + FIELD_HEIGHT),
                dictionary_item=item.name,
                data_capture_type=capture_type,
                use_unicode_text_box=item.contentType == "alpha",
            )
            group.items.append(field)
            form.items.append(field)
            row += ROW_OFFSET
        return form, group

    def _create_roster_form(
        self,
        record: DictionaryRecord,
        dict_item_to_question: dict[str, Question],
        form_number: int,
        form_name: str,
        label: str,
    ) -> tuple[Form, FormGroup]:
        """Helper to create a roster form and group for a record with multiple occurrences."""
        roster_name = self._replace_suffix(record.name, "_REC", "_ROSTER")
        roster = Roster(
            name=roster_name,
            label=label,
            form_file_number=form_number,
            item_type=FormItemType.ROSTER,
            required=False,
            max=record.occurrences.maximum,
            type="Record",
            type_name=record.name,
            display_size=(40, 30, 0, 0),
            orientation="Horizontal",
            field_row_height=0,
            heading_row_height=0,
            use_occurrence_labels=True,
            free_movement=False,
            columns=[],
            stub_text=[],
        )
        for i in range(1, record.occurrences.maximum + 1):
            stub_text = FormText(
                name=f"{record.name}_OCC_{i}",
                label=str(i),
                form_file_number=None,
                item_type=FormItemType.TEXT,
                text=str(i),
                position=None,
            )
            roster.stub_text.append(stub_text)
        roster.columns.append(RosterColumn(width=10))
        for item in record.items:
            header_text = FormText(
                name=f"{item.name}_HEADER",
                label=item.labels[0].text,
                form_file_number=None,
                item_type=FormItemType.TEXT,
                text=item.labels[0].text,
                position=None,
            )
            column = RosterColumn(header_text=header_text, fields=[])

            capture_type = self._get_capture_type(item, dict_item_to_question)

            field = FormField(
                name=item.name,
                label=item.labels[0].text,
                text=header_text,
                form_file_number=None,
                position=None,
                item_type=FormItemType.FIELD,
                dictionary_item=item.name,
                data_capture_type=capture_type,
                use_unicode_text_box=item.contentType == "alpha",
            )
            column.fields.append(field)
            roster.columns.append(column)
        group = FormGroup(
            name=form_name,
            label=label,
            form_file_number=form_number,
            item_type=FormItemType.GROUP,
            required=record.occurrences.required,
            max=1,
            items=[roster],
        )
        form = Form(
            name=form_name,
            label=label,
            form_file_number=form_number,
            level=1,
            size=(300, 300),  # CSPro will resize this for us on load
            items=[roster],
        )
        return form, group

    def _generate_form_file(
        self,
        dictionary: CSProDictionary,
        dictionary_file_name: str,
        dict_item_to_question: dict[str, Question],
    ) -> FormFile:
        logger.info("Generating form file")
        level = dictionary.levels[0]
        forms: list[Form] = []
        form_number = 0
        groups: list[FormGroup] = []
        # ID items
        id_items = level.ids.items
        form_name = "ID_ITEMS_FORM"
        form_number += 1
        # Pass questionnaire to _create_items_form
        id_form, id_group = self._create_items_form(
            id_items, dict_item_to_question, form_number, form_name, "Id Items", required=True, max_occurs=1
        )
        forms.append(id_form)
        groups.append(id_group)
        # Each record becomes a form
        for record in level.records:
            form_name = self._replace_suffix(record.name, "_REC", "_FORM")
            form_number += 1
            label = record.labels[0].text
            is_roster = record.occurrences.maximum > 1
            if is_roster:
                # Pass questionnaire to _create_roster_form
                record_form, record_group = self._create_roster_form(
                    record, dict_item_to_question, form_number, form_name, label
                )
            else:
                # Pass questionnaire to _create_items_form
                record_form, record_group = self._create_items_form(
                    record.items,
                    dict_item_to_question,
                    form_number,
                    form_name,
                    label,
                    required=record.occurrences.required,
                    max_occurs=1,
                )
            forms.append(record_form)
            groups.append(record_group)
        form_level = FormLevel(name=level.name, label=level.labels[0].text, form_file_number=0, groups=groups)
        return FormFile(
            name=self._replace_suffix(dictionary.name, "_DICT", "_FF"),
            dictionary_name=dictionary.name,
            dictionary_file_name=dictionary_file_name,
            forms=forms,
            levels=[form_level],
        )

    def _generate_logic_file(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Generate the CSPro logic (.ent.apc) file.

        Args:
            questionnaire: The questionnaire data
            output_path: Path to save the generated file
        """
        logger.info(f"Generating logic file: {output_path}")
        with open(output_path, "w") as f:
            f.write(f"{{ Application '{questionnaire.title}' logic file generated by Survaize }}\n")

    def _generate_question_text_file(self, questionnaire: Questionnaire, dictionary_name: str) -> QsfFile:
        """Generate the CSPro question text (.ent.qsf) file in YAML format.

        This method creates a question text file containing all questions from the
        questionnaire with their text and instructions. The file follows the CSPro
        YAML format for question text files. PyYAML is used for proper YAML generation.

        Args:
            questionnaire: The questionnaire data
        """
        logger.info("Generating question text file")

        # Build the question text file structure using Pydantic models
        languages = [QsfLanguage(name="EN", label="English")]
        styles = [
            QsfStyle(
                name="Normal",
                className="normal",
                css="font-family: Arial;font-size: 16px;",
            ),
            QsfStyle(
                name="Instruction",
                className="instruction",
                css="font-family: Arial;font-size: 14px;color: #0000FF;",
            ),
            QsfStyle(
                name="Heading 1",
                className="heading1",
                css="font-family: Arial;font-size: 36px;",
            ),
            QsfStyle(
                name="Heading 2",
                className="heading2",
                css="font-family: Arial;font-size: 24px;",
            ),
            QsfStyle(
                name="Heading 3",
                className="heading3",
                css="font-family: Arial;font-size: 18px;",
            ),
        ]

        qsf_questions: list[QsfQuestion] = []

        # Process all questions from all sections
        for section in questionnaire.sections:
            for question in section.questions:
                # Get the CSPro dictionary name for this field
                question_name = self._to_dictionary_name(question.id)
                full_name = f"{dictionary_name}.{question_name}"

                # Create question entry
                question_text_html = f"<p>{question.text}</p>"
                if question.instructions:
                    question_text_html += f'<p><span class="instruction">{question.instructions}</span></p>'

                condition = QsfCondition(questionText=QsfText(EN=question_text_html), helpText=QsfText(EN=""))
                qsf_question = QsfQuestion(name=full_name, conditions=[condition])
                qsf_questions.append(qsf_question)

        return QsfFile(languages=languages, styles=styles, questions=qsf_questions)

    def _generate_application_file(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Generate the CSPro application (.ent) file.

        This method creates the main application file that references all other components
        of the CSPro application (dictionary, forms, message file, logic, etc).

        Args:
            questionnaire: The questionnaire data
            output_path: Path to save the generated file
        """
        logger.info(f"Generating application file: {output_path}")

        # Create sanitized names for files
        app_name = self._to_dictionary_name(questionnaire.title)
        file_base = output_path.stem  # Get base name without extension

        # Create the application structure
        application = {
            "software": "CSPro",
            "version": 8.0,
            "fileType": "application",
            "type": "entry",
            "name": app_name.upper(),
            "label": app_name,
            "dictionaries": [
                {
                    "type": "input",
                    "path": f"{file_base}.dcf",
                    "parent": f"{file_base}.fmf",
                }
            ],
            "forms": [f"{file_base}.fmf"],
            "questionText": [f"{file_base}.ent.qsf"],
            "code": [{"type": "main", "path": f"{file_base}.ent.apc"}],
            "messages": [f"{file_base}.ent.mgf"],
            "logicSettings": {
                "version": 2.0,
                "caseSensitive": {"symbols": False},
                "actionInvoker": {
                    "accessFromExternalCaller": "promptIfNoValidAccessToken",
                    "convertResultsForLogic": True,
                },
            },
            "properties": {
                "askOperatorId": False,
                "autoAdvanceOnSelection": False,
                "caseTree": "mobileOnly",
                "centerForms": False,
                "createListing": False,
                "createLog": False,
                "decimalMark": "dot",
                "displayCodesAlongsideLabels": False,
                "notes": {"delete": "all", "edit": "all"},
                "partialSave": {"operatorEnabled": False},
                "showEndCaseMessage": True,
                "showOnlyDiscreteValuesInComboBoxes": True,
                "showFieldLabels": True,
                "showErrorMessageNumbers": False,
                "showQuestionText": True,
                "showRefusals": True,
                "verify": {"frequency": 1, "start": 1},
                "htmlDialogs": True,
                "paradata": {
                    "collection": "all",
                    "recordCoordinates": False,
                    "recordInitialPropertyValues": False,
                    "recordIteratorLoadCases": False,
                    "recordValues": False,
                    "deviceStateIntervalMinutes": 5,
                },
                "useHtmlComponentsInsteadOfNativeVersions": False,
            },
        }

        # Write the application file
        with open(output_path, "w") as f:
            json.dump(application, f, indent=2)

    def _generate_message_file(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Generate the CSPro message (.ent.mgf) file.

        Args:
            _questionnaire: The questionnaire data (currently unused)
            output_path: Path to save the generated file
        """
        logger.info(f"Generating message file: {output_path}")
        # Stub implementation: This would create the message file
        # with error and warning messages
        with open(output_path, "w") as f:
            f.write(f"{{ Application '{questionnaire.title}' logic file generated by Survaize }}\n")
            # Real implementation would include validation messages

    def _generate_pff_file(self, questionnaire: Questionnaire, output_path: Path) -> None:
        """Generate the CSPro program information (.pff) file.

        Args:
            questionnaire: The questionnaire data
            output_path: Path to save the generated file
        """
        logger.info(f"Generating program information file: {output_path}")
        app_name = self._make_file_name(questionnaire.title)

        contents = (
            "[Run Information]\n"
            "Version=CSPro 8.0\n"
            "AppType=Entry\n\n"
            "[Files]\n"
            f"Application=.\\{app_name}.ent\n"
            f"InputData=.\\{app_name}.csdb\n"
        )

        with open(output_path, "w") as f:
            f.write(contents)

    def _replace_suffix(self, string: str, old_suffix: str, new_suffix: str) -> str:
        """Replace the end of a string if it matches old_suffix with new_suffix."""
        if string.endswith(old_suffix):
            return string[: -len(old_suffix)] + new_suffix
        return string
