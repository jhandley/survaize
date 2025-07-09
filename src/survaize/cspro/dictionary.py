from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class DictionaryLabel(BaseModel):
    """Represents a label in CSPro dictionary."""

    text: str


class DictionarySecurity(BaseModel):
    """Represents security settings in CSPro dictionary."""

    allowDataViewerModifications: bool = True
    allowExport: bool = True
    cachedPasswordMinutes: int = 0
    settings: str | None = None


class DictionaryValue(BaseModel):
    """Represents a value in a value set."""

    labels: list[DictionaryLabel]
    pairs: list[dict[str, str | list[str]]]
    special: str | None = None


class DictionaryValueSet(BaseModel):
    """Represents a value set in CSPro dictionary item."""

    name: str
    labels: list[DictionaryLabel]
    values: list[DictionaryValue]


class DictionaryItem(BaseModel):
    """Represents an item in CSPro dictionary."""

    name: str
    labels: list[DictionaryLabel]
    contentType: Literal["numeric", "alpha"]
    start: int | None = None
    length: int
    zeroFill: bool | None = None
    valueSets: list[DictionaryValueSet] | None = None


class DictionaryRecordOccurrences(BaseModel):
    """Represents occurrences of a record in CSPro dictionary."""

    required: bool
    maximum: int


class DictionaryRecord(BaseModel):
    """Represents a record in CSPro dictionary."""

    name: str
    labels: list[DictionaryLabel]
    recordType: str
    occurrences: DictionaryRecordOccurrences
    items: list[DictionaryItem]


class DictionaryIds(BaseModel):
    """Represents IDs in CSPro dictionary."""

    items: list[DictionaryItem]


class DictionaryLevel(BaseModel):
    """Represents a level in CSPro dictionary."""

    name: str
    labels: list[DictionaryLabel]
    ids: DictionaryIds
    records: list[DictionaryRecord]


class CSProDictionary(BaseModel):
    """Represents a complete CSPro dictionary file."""

    software: str = "CSPro"
    version: float = 8.0
    fileType: str = "dictionary"
    name: str
    labels: list[DictionaryLabel]
    readOptimization: bool = True
    recordType: dict[str, int] = {"start": 1, "length": 1}
    defaults: dict[str, bool] = {"decimalMark": True, "zeroFill": True}
    relativePositions: bool = True
    levels: list[DictionaryLevel]

    def save(self, file_path: Path) -> None:
        """Save the dictionary to a file.

        Args:
            file_path: The path to save the dictionary file to.
        """
        with open(file=file_path, mode="w") as f:
            f.write(self.model_dump_json(indent=2, exclude_none=True))
