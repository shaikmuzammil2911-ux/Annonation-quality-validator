"""Automated tests for the Annotation Quality Validator.

Tests all validation rules, schema checks, error reporting, edge cases,
and command-line interface behaviors using Python's standard unittest framework.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest

from validate_annotations import (
    ERROR_BLANK_FIELD,
    ERROR_CONFIDENCE_OUT_OF_RANGE,
    ERROR_EMPTY_FILE,
    ERROR_INVALID_CONFIDENCE_TYPE,
    ERROR_INVALID_DECISION,
    ERROR_INVALID_LOCATION,
    ERROR_MISSING_COLUMNS,
    format_validation_report,
    main,
    validate_confidence,
    validate_csv_file,
    validate_decision,
    validate_observed_location,
    validate_task_id,
)


class BaseCSVTestCase(unittest.TestCase):
    """Base test case providing helper methods for creating temporary CSV files."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_temp_csv(self, content: str, encoding: str = "utf-8") -> str:
        """Create a temporary CSV file with given content and return its path."""
        file_path = os.path.join(self.temp_dir.name, "test_file.csv")
        with open(file_path, mode="w", encoding=encoding, newline="") as f:
            f.write(content)
        return file_path


class TestValidCSVValidation(BaseCSVTestCase):
    """Tests for valid CSV files and formatting."""

    def test_valid_csv_passes_validation(self) -> None:
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,LEFT,MATCH,5\n"
            "TASK-2,CENTER,MISMATCH,3\n"
            "TASK-3,RIGHT,UNCLEAR,1\n"
            "TASK-4,NOT_VISIBLE,MATCH,4\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_rows, 4)
        self.assertEqual(report.passed_rows, 4)
        self.assertEqual(report.failed_rows, 0)
        self.assertEqual(len(report.errors), 0)

        # Validate formatted output
        formatted = format_validation_report(report)
        self.assertIn("STATUS      : PASSED", formatted.upper())
        self.assertIn("SUCCESS", formatted)

    def test_case_insensitivity_and_whitespace_handling(self) -> None:
        """Verify label comparisons are case-insensitive and tolerate surrounding spaces."""
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,  left  ,  match  , 5 \n"
            "TASK-2,Center,Mismatch, 4\n"
            "TASK-3,RIGHT,unclear,3\n"
            "TASK-4,not_visible,MATCH,2\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_rows, 4)
        self.assertEqual(len(report.errors), 0)

    def test_utf8_bom_file_support(self) -> None:
        """Verify files encoded with UTF-8 BOM are handled seamlessly."""
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-BOM-1,LEFT,MATCH,5\n"
            "TASK-BOM-2,CENTER,MISMATCH,4\n"
        )
        file_path = self.create_temp_csv(csv_content, encoding="utf-8-sig")
        report = validate_csv_file(file_path)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_rows, 2)
        self.assertEqual(len(report.errors), 0)


class TestSchemaAndHeaderValidation(BaseCSVTestCase):
    """Tests for file-level and CSV header validation."""

    def test_empty_csv_file(self) -> None:
        """Verify empty files report an error cleanly."""
        file_path = self.create_temp_csv("")
        report = validate_csv_file(file_path)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.total_rows, 0)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].error_type, ERROR_EMPTY_FILE)
        self.assertIn("empty", report.errors[0].message.lower())

    def test_missing_single_required_column(self) -> None:
        """Verify error when one required column is missing."""
        csv_content = (
            "task_id,observed_location,decision\n"
            "TASK-1,LEFT,MATCH\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertFalse(report.is_valid)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].error_type, ERROR_MISSING_COLUMNS)
        self.assertIn("confidence", report.errors[0].message)

    def test_missing_multiple_required_columns(self) -> None:
        """Verify all missing columns are identified and reported."""
        csv_content = (
            "task_id,other_column\n"
            "TASK-1,VAL\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertFalse(report.is_valid)
        self.assertIn("observed_location", report.missing_columns)
        self.assertIn("decision", report.missing_columns)
        self.assertIn("confidence", report.missing_columns)
        self.assertEqual(report.errors[0].error_type, ERROR_MISSING_COLUMNS)

    def test_case_insensitive_header_matching(self) -> None:
        """Verify headers match case-insensitively with whitespace trimmed."""
        csv_content = (
            " Task_ID , OBSERVED_LOCATION , Decision , Confidence \n"
            "TASK-1,LEFT,MATCH,5\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_rows, 1)


class TestFieldValidationUnits(unittest.TestCase):
    """Unit tests for individual field validation functions."""

    def test_validate_task_id_valid(self) -> None:
        val, err = validate_task_id("TASK-100", 2)
        self.assertEqual(val, "TASK-100")
        self.assertIsNone(err)

    def test_validate_task_id_blank(self) -> None:
        val, err = validate_task_id("   ", 2)
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.field, "task_id")
        self.assertEqual(err.error_type, ERROR_BLANK_FIELD)

    def test_validate_observed_location_valid(self) -> None:
        for loc in ("LEFT", "CENTER", "RIGHT", "NOT_VISIBLE", "left", "Center "):
            val, err = validate_observed_location(loc, 2, "TASK-1")
            self.assertIsNotNone(val)
            self.assertIsNone(err)

    def test_validate_observed_location_blank(self) -> None:
        val, err = validate_observed_location("", 2, "TASK-1")
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.error_type, ERROR_BLANK_FIELD)

    def test_validate_observed_location_unsupported(self) -> None:
        val, err = validate_observed_location("TOP_LEFT", 2, "TASK-1")
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.error_type, ERROR_INVALID_LOCATION)
        self.assertIn("TOP_LEFT", err.message)

    def test_validate_decision_valid(self) -> None:
        for dec in ("MATCH", "MISMATCH", "UNCLEAR", "match", "Unclear "):
            val, err = validate_decision(dec, 2, "TASK-1")
            self.assertIsNotNone(val)
            self.assertIsNone(err)

    def test_validate_decision_blank(self) -> None:
        val, err = validate_decision("   ", 2, "TASK-1")
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.error_type, ERROR_BLANK_FIELD)

    def test_validate_decision_unsupported(self) -> None:
        val, err = validate_decision("MAYBE", 2, "TASK-1")
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.error_type, ERROR_INVALID_DECISION)
        self.assertIn("MAYBE", err.message)

    def test_validate_confidence_valid_range(self) -> None:
        for score in ("1", "2", "3", "4", "5", " 3 "):
            val, err = validate_confidence(score, 2, "TASK-1")
            self.assertIsNotNone(val)
            self.assertIsNone(err)

    def test_validate_confidence_blank(self) -> None:
        val, err = validate_confidence("", 2, "TASK-1")
        self.assertIsNone(val)
        self.assertIsNotNone(err)
        self.assertEqual(err.error_type, ERROR_BLANK_FIELD)

    def test_validate_confidence_out_of_range(self) -> None:
        for score in ("0", "6", "-1", "-10", "100"):
            val, err = validate_confidence(score, 2, "TASK-1")
            self.assertIsNone(val)
            self.assertIsNotNone(err)
            self.assertEqual(err.error_type, ERROR_CONFIDENCE_OUT_OF_RANGE)

    def test_validate_confidence_decimal(self) -> None:
        for score in ("3.5", "4.0", "1.0", "0.5"):
            val, err = validate_confidence(score, 2, "TASK-1")
            self.assertIsNone(val)
            self.assertIsNotNone(err)
            self.assertEqual(err.error_type, ERROR_INVALID_CONFIDENCE_TYPE)
            self.assertIn("Decimal", err.message)

    def test_validate_confidence_non_numeric(self) -> None:
        for score in ("high", "five", "N/A", "abc"):
            val, err = validate_confidence(score, 2, "TASK-1")
            self.assertIsNone(val)
            self.assertIsNotNone(err)
            self.assertEqual(err.error_type, ERROR_INVALID_CONFIDENCE_TYPE)
            self.assertIn("Non-numeric", err.message)


class TestRowNumberingAndMultiErrorReporting(BaseCSVTestCase):
    """Tests checking row numbering and multiple errors."""

    def test_multiple_errors_in_single_row(self) -> None:
        """Verify multiple errors in a single row are all detected and reported."""
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,UPPER,INVALID,99\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.total_rows, 1)
        self.assertEqual(report.failed_rows, 1)
        self.assertEqual(len(report.errors), 3)

        fields = [e.field for e in report.errors]
        self.assertIn("observed_location", fields)
        self.assertIn("decision", fields)
        self.assertIn("confidence", fields)

        # All errors should point to Row 2
        for err in report.errors:
            self.assertEqual(err.row_number, 2)
            self.assertEqual(err.task_id, "TASK-1")

    def test_multiple_invalid_rows_and_exact_row_numbers(self) -> None:
        """Verify accurate row numbering across multiple rows."""
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,LEFT,MATCH,5\n"       # Row 2: valid
            "TASK-2,INVALID,MATCH,4\n"     # Row 3: error in location
            "TASK-3,RIGHT,MATCH,5\n"       # Row 4: valid
            "TASK-4,CENTER,DEC_ERR,2\n"    # Row 5: error in decision
            ",LEFT,MATCH,5\n"              # Row 6: blank task_id
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.total_rows, 5)
        self.assertEqual(report.passed_rows, 2)
        self.assertEqual(report.failed_rows, 3)
        self.assertEqual(len(report.errors), 3)

        self.assertEqual(report.errors[0].row_number, 3)
        self.assertEqual(report.errors[0].field, "observed_location")

        self.assertEqual(report.errors[1].row_number, 5)
        self.assertEqual(report.errors[1].field, "decision")

        self.assertEqual(report.errors[2].row_number, 6)
        self.assertEqual(report.errors[2].field, "task_id")

    def test_error_summary_by_type(self) -> None:
        """Verify error summary aggregates counts accurately."""
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,INVALID_1,MATCH,5\n"
            "TASK-2,INVALID_2,MATCH,5\n"
            "TASK-3,LEFT,MATCH,0\n"
        )
        file_path = self.create_temp_csv(csv_content)
        report = validate_csv_file(file_path)

        counts = report.error_counts_by_type
        self.assertEqual(counts[ERROR_INVALID_LOCATION], 2)
        self.assertEqual(counts[ERROR_CONFIDENCE_OUT_OF_RANGE], 1)


class TestCommandLineInterface(BaseCSVTestCase):
    """Tests verifying CLI behavior and exit codes."""

    def test_cli_valid_file_returns_code_0(self) -> None:
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,LEFT,MATCH,5\n"
        )
        file_path = self.create_temp_csv(csv_content)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exit_code = main([file_path])
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(exit_code, 0)
        self.assertIn("PASSED", output)

    def test_cli_invalid_file_returns_code_1(self) -> None:
        csv_content = (
            "task_id,observed_location,decision,confidence\n"
            "TASK-1,INVALID,MATCH,5\n"
        )
        file_path = self.create_temp_csv(csv_content)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            exit_code = main([file_path])
        finally:
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        self.assertEqual(exit_code, 1)
        self.assertIn("FAILED", output)

    def test_cli_missing_argument_returns_code_2(self) -> None:
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            exit_code = main([])
        finally:
            err_output = sys.stderr.getvalue()
            sys.stderr = old_stderr

        self.assertEqual(exit_code, 2)
        self.assertIn("Usage:", err_output)

    def test_cli_nonexistent_file_returns_code_2(self) -> None:
        fake_path = os.path.join(self.temp_dir.name, "does_not_exist.csv")

        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            exit_code = main([fake_path])
        finally:
            err_output = sys.stderr.getvalue()
            sys.stderr = old_stderr

        self.assertEqual(exit_code, 2)
        self.assertIn("File not found", err_output)

    def test_cli_directory_path_returns_code_2(self) -> None:
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            exit_code = main([self.temp_dir.name])
        finally:
            err_output = sys.stderr.getvalue()
            sys.stderr = old_stderr

        self.assertEqual(exit_code, 2)
        self.assertIn("directory", err_output.lower())


if __name__ == "__main__":
    unittest.main()
