"""Survey Solutions questionnaire models based on their JSON schema."""

import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def generate_guid() -> str:
    """Generate a GUID string for Survey Solutions entities."""
    return str(uuid.uuid4())


class QuestionScopeEnum(str, Enum):
    """Question scope enumeration."""

    INTERVIEWER = "Interviewer"
    SUPERVISOR = "Supervisor"
    HIDDEN = "Hidden"


class ValidationSeverity(str, Enum):
    """Validation condition severity."""

    ERROR = "Error"
    WARNING = "Warning"


class DisplayModeEnum(str, Enum):
    """Display mode for single/multi select questions."""

    RADIO = "Radio"
    COMBOBOX = "Combobox"
    CHECKBOXES = "Checkboxes"
    YES_NO = "YesNo"


class GeometryType(str, Enum):
    """Geometry type for area questions."""

    POLYGON = "Polygon"
    POLYLINE = "Polyline"
    POINT = "Point"
    MULTIPOINT = "Multipoint"


class Answer(BaseModel):
    """Represents an answer option for single/multi select questions."""

    Text: str
    Code: int | None = None
    ParentCode: int | None = None
    AttachmentName: str | None = None


class ValidationCondition(BaseModel):
    """Represents a validation condition for questions."""

    Expression: str
    Message: str | None = None
    Severity: ValidationSeverity = ValidationSeverity.ERROR


class BaseQuestion(BaseModel):
    """Base class for all Survey Solutions questions."""

    Id: str = Field(default_factory=generate_guid)
    VariableName: str
    QuestionText: str | None = None
    Instructions: str | None = None
    HideInstructions: bool = False
    ConditionExpression: str | None = None
    HideIfDisabled: bool = False
    IsCritical: bool = False
    QuestionScope: QuestionScopeEnum = QuestionScopeEnum.INTERVIEWER
    VariableLabel: str | None = None
    ValidationConditions: list[ValidationCondition] = Field(default_factory=list)


class TextQuestion(BaseQuestion):
    """Text question type."""

    Type: Literal["TextQuestion"] = "TextQuestion"
    Mask: str | None = None


class NumericQuestion(BaseQuestion):
    """Numeric question type."""

    Type: Literal["NumericQuestion"] = "NumericQuestion"
    IsInteger: bool = True
    DecimalPlaces: int | None = None
    UseThousandsSeparator: bool = False


class SingleQuestion(BaseQuestion):
    """Single select question type."""

    Type: Literal["SingleQuestion"] = "SingleQuestion"
    DisplayMode: DisplayModeEnum = DisplayModeEnum.RADIO
    ShowAsList: bool = False
    ShowAsListThreshold: int | None = None
    Answers: list[Answer] = Field(default_factory=list)
    FilterExpression: str | None = None


class MultiOptionsQuestion(BaseQuestion):
    """Multi select question type."""

    Type: Literal["MultiOptionsQuestion"] = "MultiOptionsQuestion"
    DisplayMode: DisplayModeEnum = DisplayModeEnum.CHECKBOXES
    AreAnswersOrdered: bool = False
    MaxAllowedAnswers: int | None = None
    Answers: list[Answer] = Field(default_factory=list)
    FilterExpression: str | None = None


class DateTimeQuestion(BaseQuestion):
    """Date/time question type."""

    Type: Literal["DateTimeQuestion"] = "DateTimeQuestion"
    IsTimestamp: bool = False
    DefaultDate: str | None = None


class GpsCoordinateQuestion(BaseQuestion):
    """GPS coordinate question type."""

    Type: Literal["GpsCoordinateQuestion"] = "GpsCoordinateQuestion"


class StaticText(BaseModel):
    """Static text element."""

    Type: Literal["StaticText"] = "StaticText"
    Id: str = Field(default_factory=generate_guid)
    VariableName: str | None = None
    Text: str
    AttachmentName: str | None = None
    ValidationConditions: list[ValidationCondition] = Field(default_factory=list)
    ConditionExpression: str | None = None
    HideIfDisabled: bool = False


# Union type for all possible question/element types
QuestionElement = (
    TextQuestion
    | NumericQuestion
    | SingleQuestion
    | MultiOptionsQuestion
    | DateTimeQuestion
    | GpsCoordinateQuestion
    | StaticText
)


class Group(BaseModel):
    """Represents a group/section in Survey Solutions."""

    Type: Literal["Group"] = "Group"
    Id: str = Field(default_factory=generate_guid)
    VariableName: str
    Title: str | None = None
    ConditionExpression: str | None = None
    HideIfDisabled: bool = False
    Children: list[QuestionElement] = Field(default_factory=list)


class QuestionnaireMetaInfo(BaseModel):
    """Questionnaire metadata."""

    SubTitle: str | None = None
    StudyType: str = "AdministrativeRecords"
    Version: str | None = None
    VersionNotes: str | None = None
    KindOfData: str | None = None
    Country: str | None = None
    Year: int | None = None
    Language: str | None = None
    Coverage: str | None = None
    Universe: str | None = None
    UnitOfAnalysis: str | None = None
    PrimaryInvestigator: str | None = None
    Funding: str | None = None
    Consultant: str | None = None
    ModeOfDataCollection: str = "Capi"
    Notes: str | None = None
    Keywords: str | None = None
    AgreeToMakeThisQuestionnairePublic: bool = False


class SurveySolutionsQuestionnaire(BaseModel):
    """Root Survey Solutions questionnaire model."""

    Id: str = Field(default_factory=generate_guid)
    Title: str
    Description: str | None = None
    VariableName: str | None = None
    HideIfDisabled: bool = False
    DefaultTranslation: str | None = None
    Children: list[Group] = Field(default_factory=list)
    Metadata: QuestionnaireMetaInfo | None = None

    # Optional collections that we may not use initially - using empty dicts for now
    Macros: list[dict[str, str]] = Field(default_factory=list)
    LookupTables: list[dict[str, str]] = Field(default_factory=list)
    Attachments: list[dict[str, str]] = Field(default_factory=list)
    Translations: dict[str, str] | None = None
    Categories: list[dict[str, str]] = Field(default_factory=list)
    CriticalRules: list[dict[str, str]] = Field(default_factory=list)
