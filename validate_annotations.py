"""Annotation Quality Validator.

A robust command-line validation tool for simulated data annotation records stored in CSV files.
Validates headers, required fields, allowed categorical values, and confidence scores
using only Python's standard library.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import os
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

# Schema Definitions
REQUIRED_COLUMNS: Tuple[str, ...] = (
    "task_id",
    "observed_location",
    "decision",
    "confidence",
)

VALID_LOCATIONS: Set[str] = {"LEFT", "CENTER", "RIGHT", "NOT_VISIBLE"}
VALID_DECISIONS: Set[str] = {"MATCH", "MISMATCH", "UNCLEAR"}
MIN_CONFIDENCE: int = 1
MAX_CONFIDENCE: int = 5

# Error Type Constants
ERROR_EMPTY_FILE = "EMPTY_FILE"
ERROR_MISSING_COLUMNS = "MISSING_COLUMNS"
ERROR_BLANK_FIELD = "BLANK_FIELD"
ERROR_INVALID_LOCATION = "INVALID_LOCATION"
ERROR_INVALID_DECISION = "INVALID_DECISION"
ERROR_INVALID_CONFIDENCE_TYPE = "INVALID_CONFIDENCE_TYPE"
ERROR_CONFIDENCE_OUT_OF_RANGE = "CONFIDENCE_OUT_OF_RANGE"
ERROR_MALFORMED_ROW = "MALFORMED_ROW"


@dataclass
class ValidationError:
    """Represents a single validation error in a CSV record."""

    row_number: int
    field: str
    message: str
    error_type: str
    task_id: Optional[str] = None

    def __str__(self) -> str:
        task_info = f" [Task ID: {self.task_id}]" if self.task_id else ""
        return f"[Row {self.row_number}] Field '{self.field}': {self.message}{task_info}"


@dataclass
class ValidationReport:
    """Contains full results of a CSV validation run."""

    file_path: str
    total_rows: int = 0
    passed_rows: int = 0
    failed_rows: int = 0
    errors: List[ValidationError] = field(default_factory=list)
    missing_columns: List[str] = field(default_factory=list)
    file_level_error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Return True if the CSV has no errors and passed schema validation."""
        return len(self.errors) == 0 and not self.missing_columns and not self.file_level_error

    @property
    def error_counts_by_type(self) -> Dict[str, int]:
        """Return a mapping of error type to occurrence count."""
        counts: Dict[str, int] = {}
        for err in self.errors:
            counts[err.error_type] = counts.get(err.error_type, 0) + 1
        return counts


def validate_task_id(
    value: Optional[str],
    row_number: int,
) -> Tuple[Optional[str], Optional[ValidationError]]:
    """Validate task_id. Must not be blank.

    Returns (preserved_task_id, optional_error).
    """
    raw_val = value if value is not None else ""
    trimmed = raw_val.strip()

    if not trimmed:
        err = ValidationError(
            row_number=row_number,
            field="task_id",
            message="Field 'task_id' is required and cannot be blank.",
            error_type=ERROR_BLANK_FIELD,
            task_id=None,
        )
        return None, err

    return raw_val, None


def validate_observed_location(
    value: Optional[str],
    row_number: int,
    task_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[ValidationError]]:
    """Validate observed_location.

    Must be one of LEFT, CENTER, RIGHT, NOT_VISIBLE (case-insensitive).
    """
    raw_val = value if value is not None else ""
    trimmed = raw_val.strip()

    if not trimmed:
        err = ValidationError(
            row_number=row_number,
            field="observed_location",
            message=(
                "Field 'observed_location' is required and cannot be blank. "
                "Allowed values: LEFT, CENTER, RIGHT, NOT_VISIBLE."
            ),
            error_type=ERROR_BLANK_FIELD,
            task_id=task_id,
        )
        return None, err

    normalized = trimmed.upper()
    if normalized not in VALID_LOCATIONS:
        err = ValidationError(
            row_number=row_number,
            field="observed_location",
            message=(
                f"Invalid observed_location '{raw_val}'. "
                f"Allowed values: {', '.join(sorted(VALID_LOCATIONS))}."
            ),
            error_type=ERROR_INVALID_LOCATION,
            task_id=task_id,
        )
        return None, err

    return normalized, None


def validate_decision(
    value: Optional[str],
    row_number: int,
    task_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[ValidationError]]:
    """Validate decision.

    Must be one of MATCH, MISMATCH, UNCLEAR (case-insensitive).
    """
    raw_val = value if value is not None else ""
    trimmed = raw_val.strip()

    if not trimmed:
        err = ValidationError(
            row_number=row_number,
            field="decision",
            message=(
                "Field 'decision' is required and cannot be blank. "
                "Allowed values: MATCH, MISMATCH, UNCLEAR."
            ),
            error_type=ERROR_BLANK_FIELD,
            task_id=task_id,
        )
        return None, err

    normalized = trimmed.upper()
    if normalized not in VALID_DECISIONS:
        err = ValidationError(
            row_number=row_number,
            field="decision",
            message=(
                f"Invalid decision '{raw_val}'. "
                f"Allowed values: {', '.join(sorted(VALID_DECISIONS))}."
            ),
            error_type=ERROR_INVALID_DECISION,
            task_id=task_id,
        )
        return None, err

    return normalized, None


def validate_confidence(
    value: Optional[str],
    row_number: int,
    task_id: Optional[str] = None,
) -> Tuple[Optional[int], Optional[ValidationError]]:
    """Validate confidence score.

    Must be a whole number between 1 and 5.
    Rejects blanks, decimal numbers, text, and numbers out of range.
    """
    raw_val = value if value is not None else ""
    trimmed = raw_val.strip()

    if not trimmed:
        err = ValidationError(
            row_number=row_number,
            field="confidence",
            message=(
                f"Field 'confidence' is required and cannot be blank. "
                f"Must be a whole number between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}."
            ),
            error_type=ERROR_BLANK_FIELD,
            task_id=task_id,
        )
        return None, err

    # Explicitly reject decimal values (e.g. '3.5', '4.0')
    if "." in trimmed:
        err = ValidationError(
            row_number=row_number,
            field="confidence",
            message=(
                f"Invalid confidence '{raw_val}'. Decimal values are not allowed. "
                f"Must be a whole number between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}."
            ),
            error_type=ERROR_INVALID_CONFIDENCE_TYPE,
            task_id=task_id,
        )
        return None, err

    try:
        int_val = int(trimmed)
    except ValueError:
        err = ValidationError(
            row_number=row_number,
            field="confidence",
            message=(
                f"Invalid confidence '{raw_val}'. Non-numeric text is not allowed. "
                f"Must be a whole number between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}."
            ),
            error_type=ERROR_INVALID_CONFIDENCE_TYPE,
            task_id=task_id,
        )
        return None, err

    if int_val < MIN_CONFIDENCE or int_val > MAX_CONFIDENCE:
        err = ValidationError(
            row_number=row_number,
            field="confidence",
            message=(
                f"Confidence score {int_val} is out of range. "
                f"Must be a whole number between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}."
            ),
            error_type=ERROR_CONFIDENCE_OUT_OF_RANGE,
            task_id=task_id,
        )
        return None, err

    return int_val, None


def validate_row(
    row_values: Dict[str, str],
    row_number: int,
) -> List[ValidationError]:
    """Validate all fields in a single row dictionary.

    Returns a list of any validation errors detected.
    """
    errors: List[ValidationError] = []

    # 1. Task ID
    task_id_raw = row_values.get("task_id", "")
    preserved_task_id, task_err = validate_task_id(task_id_raw, row_number)
    if task_err:
        errors.append(task_err)

    # 2. Observed Location
    loc_raw = row_values.get("observed_location", "")
    _, loc_err = validate_observed_location(loc_raw, row_number, preserved_task_id)
    if loc_err:
        errors.append(loc_err)

    # 3. Decision
    dec_raw = row_values.get("decision", "")
    _, dec_err = validate_decision(dec_raw, row_number, preserved_task_id)
    if dec_err:
        errors.append(dec_err)

    # 4. Confidence
    conf_raw = row_values.get("confidence", "")
    _, conf_err = validate_confidence(conf_raw, row_number, preserved_task_id)
    if conf_err:
        errors.append(conf_err)

    return errors


def validate_csv_reader(
    reader: Sequence[List[str]] | csv.reader,
    file_path: str = "<stream>",
) -> ValidationReport:
    """Validate rows from a CSV reader object.

    Handles header verification and row-by-row validation.
    """
    report = ValidationReport(file_path=file_path)

    # Attempt to read header row
    iterator = iter(reader)
    try:
        header = next(iterator)
    except StopIteration:
        report.file_level_error = "The CSV file is empty or contains no header row."
        report.errors.append(
            ValidationError(
                row_number=1,
                field="header",
                message=report.file_level_error,
                error_type=ERROR_EMPTY_FILE,
            )
        )
        return report

    # Strip empty trailing/leading whitespace and build normalized column lookup
    normalized_headers: Dict[str, int] = {}
    for idx, col_name in enumerate(header):
        cleaned_col = col_name.strip().lower()
        if cleaned_col and cleaned_col not in normalized_headers:
            normalized_headers[cleaned_col] = idx

    # Verify required columns
    missing_cols: List[str] = [
        col for col in REQUIRED_COLUMNS if col.lower() not in normalized_headers
    ]

    if missing_cols:
        report.missing_columns = missing_cols
        missing_str = ", ".join(missing_cols)
        msg = f"Missing required column(s): {missing_str}."
        report.errors.append(
            ValidationError(
                row_number=1,
                field="header",
                message=msg,
                error_type=ERROR_MISSING_COLUMNS,
            )
        )
        # Cannot safely validate data rows if required columns are absent
        return report

    # Process data rows
    seen_errors: Set[Tuple[int, str, str]] = set()

    for row_idx, row in enumerate(iterator, start=2):
        report.total_rows += 1

        # Check for malformed rows (too few columns)
        row_dict: Dict[str, str] = {}
        row_has_malformed = False

        for col_name in REQUIRED_COLUMNS:
            col_pos = normalized_headers[col_name.lower()]
            if col_pos < len(row):
                row_dict[col_name] = row[col_pos]
            else:
                row_dict[col_name] = ""
                row_has_malformed = True

        row_errors: List[ValidationError] = []

        if row_has_malformed and len(row) < len(header):
            task_hint = row_dict.get("task_id") or None
            err = ValidationError(
                row_number=row_idx,
                field="row",
                message=f"Malformed row: expected at least {len(header)} columns, found {len(row)}.",
                error_type=ERROR_MALFORMED_ROW,
                task_id=task_hint,
            )
            row_errors.append(err)

        field_errors = validate_row(row_dict, row_idx)
        row_errors.extend(field_errors)

        # De-duplicate errors if any
        unique_row_errors: List[ValidationError] = []
        for err in row_errors:
            key = (err.row_number, err.field, err.message)
            if key not in seen_errors:
                seen_errors.add(key)
                unique_row_errors.append(err)

        if unique_row_errors:
            report.failed_rows += 1
            report.errors.extend(unique_row_errors)
        else:
            report.passed_rows += 1

    return report


def validate_csv_file(file_path: str) -> ValidationReport:
    """Open and validate a CSV file at the given path.

    Supports UTF-8 and UTF-8 with BOM (utf-8-sig).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")

    if os.path.isdir(file_path):
        raise IsADirectoryError(f"Path is a directory, not a CSV file: '{file_path}'")

    # Use utf-8-sig to handle both UTF-8 with BOM and standard UTF-8 seamlessly
    with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return validate_csv_reader(reader, file_path=file_path)


def format_validation_report(report: ValidationReport) -> str:
    """Format the validation results into a human-readable text report."""
    border = "=" * 80
    sub_border = "-" * 80
    lines: List[str] = [
        border,
        "ANNOTATION QUALITY VALIDATOR REPORT",
        border,
        f"Target File : {report.file_path}",
        f"Total Rows  : {report.total_rows}",
        f"Passed Rows : {report.passed_rows}",
        f"Failed Rows : {report.failed_rows}",
        f"Total Errors: {len(report.errors)}",
        f"Status      : {'PASSED' if report.is_valid else 'FAILED'}",
        border,
    ]

    if report.is_valid:
        lines.append(
            f"SUCCESS: All {report.total_rows} annotation record(s) passed validation successfully."
        )
        lines.append(border)
        return "\n".join(lines)

    # Section: Errors List
    lines.append("\nVALIDATION ERRORS:")
    lines.append(sub_border)
    for err in report.errors:
        lines.append(str(err))

    # Section: Summary of Error Types
    lines.append("\nERROR SUMMARY BY TYPE:")
    lines.append(sub_border)
    for err_type, count in sorted(report.error_counts_by_type.items()):
        lines.append(f"- {err_type:<28}: {count} occurrence(s)")

    lines.append("\n" + border)
    lines.append(
        f"FAILURE: {len(report.errors)} validation error(s) detected. Please correct the file."
    )
    lines.append(border)

    return "\n".join(lines)


def print_usage() -> None:
    """Print command-line usage information."""
    usage_text = """Annotation Quality Validator

Usage:
    python validate_annotations.py <path_to_csv_file>

Description:
    Validates CSV files containing simulated data annotation records.
    Verifies required headers, non-empty fields, supported categories,
    and valid confidence score ranges.

Schema Requirements:
    - task_id            : Required, non-blank string
    - observed_location  : Required (LEFT, CENTER, RIGHT, NOT_VISIBLE)
    - decision           : Required (MATCH, MISMATCH, UNCLEAR)
    - confidence         : Required, whole integer between 1 and 5

Exit Codes:
    0 : Validation passed successfully.
    1 : Validation errors found in the CSV data.
    2 : Command-line usage error, missing argument, or unreadable file.
"""
    sys.stderr.write(usage_text)


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint. Returns an exit code (0, 1, or 2)."""
    args = argv if argv is not None else sys.argv[1:]

    if len(args) != 1 or args[0] in ("-h", "--help"):
        print_usage()
        return 2

    file_path = args[0]

    try:
        report = validate_csv_file(file_path)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 2
    except IsADirectoryError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 2
    except PermissionError as err:
        sys.stderr.write(f"Error: Permission denied reading '{file_path}': {err}\n")
        return 2
    except UnicodeDecodeError as err:
        sys.stderr.write(f"Error: File encoding error while reading '{file_path}': {err}\n")
        return 2
    except Exception as err:
        sys.stderr.write(f"Error: Unexpected failure while processing '{file_path}': {err}\n")
        return 2

    formatted = format_validation_report(report)
    print(formatted)

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
