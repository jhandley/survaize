from pathlib import Path

from survaize.reader.json_reader import JSONReader
from survaize.writer.cspro_writer import CSProWriter

test_data_dir = Path(__file__).parent / "fixtures" / "PopstanHouseholdSurvey"
cspro_fixture_dir = test_data_dir / "cspro"
json_fixture_file = test_data_dir / "PopstanHouseholdQuestionnaire.json"


def read_text(path: Path) -> str:
    """Read text from a file, normalizing line endings."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_cspro_writer_generates_expected_files(tmp_path: Path) -> None:
    """CSProWriter.write should generate files matching the cspro fixtures."""
    # Read questionnaire from JSON fixture
    reader = JSONReader()
    with open(json_fixture_file, "rb") as f:
        questionnaire = reader.read(f)

    # Prepare output path
    output_file = tmp_path / "PopstanHouseholdSurvey"

    # Run writer
    writer = CSProWriter()
    writer.write(questionnaire, output_file)

    assert output_file.is_dir(), f"Generated directory not found: {output_file}"

    # Compare each fixture file with generated file
    for fixture_path in sorted(cspro_fixture_dir.iterdir()):
        gen_path = output_file / fixture_path.name
        assert gen_path.exists(), f"Missing generated file: {gen_path.name}"
        # Compare contents
        expected = read_text(fixture_path)
        actual = read_text(gen_path)
        assert actual == expected, f"Contents differ for file {fixture_path.name}"

    # Ensure no extra files were generated
    generated_files = {p.name for p in output_file.iterdir()}
    fixture_files = {p.name for p in cspro_fixture_dir.iterdir()}
    assert generated_files == fixture_files, (
        f"Unexpected generated files: {sorted(generated_files - fixture_files)}; "
        f"missing files: {sorted(fixture_files - generated_files)}"
    )


def test_generate_record_type() -> None:
    """Test that _generate_record_type generates unique record types correctly."""
    writer = CSProWriter()

    # Test first 26 records should be A-Z
    for i in range(26):
        expected = chr(ord("A") + i)
        actual = writer._generate_record_type(i)
        assert actual == expected, f"Index {i}: expected {expected}, got {actual}"

    # Test next 26 records should be AA-AZ
    for i in range(26, 52):
        second_char = chr(ord("A") + (i - 26))
        expected = f"A{second_char}"
        actual = writer._generate_record_type(i)
        assert actual == expected, f"Index {i}: expected {expected}, got {actual}"

    # Test next 26 records should be BA-BZ
    for i in range(52, 78):
        second_char = chr(ord("A") + (i - 52))
        expected = f"B{second_char}"
        actual = writer._generate_record_type(i)
        assert actual == expected, f"Index {i}: expected {expected}, got {actual}"

    # Test specific edge cases
    test_cases = [
        (0, "A"),  # First record
        (25, "Z"),  # Last single character
        (26, "AA"),  # First double character
        (51, "AZ"),  # Last A* record
        (52, "BA"),  # First B* record
        (77, "BZ"),  # Last B* record
        (78, "CA"),  # First C* record
        (100, "CW"),  # Random middle case: 100-26=74, 74//26=2 (C), 74%26=22 (W)
        (701, "ZZ"),  # Last double character: 701-26=675, 675//26=25 (Z), 675%26=25 (Z)
    ]

    for index, expected in test_cases:
        actual = writer._generate_record_type(index)
        assert actual == expected, f"Index {index}: expected {expected}, got {actual}"

    # Test uniqueness for a large range
    record_types: set[str] = set()
    for i in range(702):  # Test up to ZZ (last 2-character combination)
        record_type = writer._generate_record_type(i)
        assert record_type not in record_types, f"Duplicate record type {record_type} at index {i}"
        record_types.add(record_type)

    # Verify we have exactly 702 unique record types (26 + 26*26)
    assert len(record_types) == 702
