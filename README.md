# Annotation Quality Validator

A lightweight, reliable command-line tool built in Python for validating simulated data annotation records stored in CSV format. The tool automatically detects missing columns, blank required fields, unsupported categorical labels, out-of-range confidence scores, and format irregularities before dataset records are used for downstream modeling or analytical workflows.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Schema & Supported Values](#schema--supported-values)
- [Installation & Quick Start](#installation--quick-start)
- [Usage & Examples](#usage--examples)
  - [Command Syntax](#command-syntax)
  - [Example: Successful Validation](#example-successful-validation)
  - [Example: Validation with Errors](#example-validation-with-errors)
- [Exit Codes](#exit-codes)
- [Automated Testing](#automated-testing)
- [Limitations & Disclaimer](#limitations--disclaimer)
- [License](#license)

---

## Overview

High-quality annotation pipelines depend on strict schema consistency and valid categorical assignments. Even minor issues—such as decimal confidence scores, missing task identifiers, or unsupported labels—can break downstream processing models or skew quality audits.

The **Annotation Quality Validator** provides immediate, row-by-row feedback on CSV files. It points directly to exact file line numbers, explains violations in clear, plain language, and aggregates a summary of detected error categories.

---

## Key Features

- **Standard Library Only**: Requires zero external packages (`pip` dependencies not needed).
- **Robust CSV Encoding**: Automatically supports both standard UTF-8 and UTF-8 with Byte Order Mark (`UTF-8 BOM`).
- **Pre-flight Header Verification**: Validates the presence of all required columns before inspecting data rows.
- **Comprehensive Row & Field Checks**:
  - Non-blank task identifiers with preserved original values for traceability.
  - Case-insensitive and whitespace-tolerant categorical validation (`observed_location`, `decision`).
  - Strict confidence validation (integers 1–5 only; rejects decimals, non-numeric strings, and out-of-range values).
- **Exhaustive Multi-Error Reporting**:
  - Captures all errors across all rows rather than failing at the first issue.
  - Captures multiple errors occurring within the same row.
  - Deduplicates repeated messages for identical row issues.
- **Error Aggregation Summary**: Groups and counts detected error types to highlight dataset quality trends.
- **Predictable Exit Codes**: Returns distinct process exit codes (`0`, `1`, `2`) for clean integration with CI/CD and automated pipelines.
- **Decoupled Architecture**: Validation engine is completely isolated from CLI printing for clean unit testability.

---

## Requirements

- **Python Version**: Python 3.9 or higher.
- **Dependencies**: None (uses only built-in modules: `csv`, `dataclasses`, `sys`, `os`, `typing`, `unittest`).

---

## Project Structure

```text
Annotation-quality-validator/
│
├── validate_annotations.py             # Main CLI entrypoint and validation logic
├── test_validate_annotations.py        # Automated unit test suite (unittest)
├── sample_annotations.csv              # Valid sample CSV dataset
├── sample_annotations_with_errors.csv  # Deliberately invalid sample dataset
├── requirements.txt                    # Documentation on dependency-free status
├── .gitignore                          # Git ignore rules for caches and virtualenvs
├── LICENSE                             # MIT License
└── README.md                           # Documentation
```

---

## Schema & Supported Values

The validator enforces the following default schema:

| Column Name | Required | Data Type / Allowed Values | Rules & Validation Behavior |
| :--- | :---: | :--- | :--- |
| `task_id` | **Yes** | String (non-empty) | Must not be blank or whitespace-only. Preserved verbatim in reports. |
| `observed_location` | **Yes** | `LEFT`, `CENTER`, `RIGHT`, `NOT_VISIBLE` | Case-insensitive and trimmed. Unsupported labels rejected. |
| `decision` | **Yes** | `MATCH`, `MISMATCH`, `UNCLEAR` | Case-insensitive and trimmed. Unsupported labels rejected. |
| `confidence` | **Yes** | Integer (`1` to `5`) | Must be whole number. Rejects decimals (`3.5`), text (`HIGH`), and out-of-bounds values (`0`, `6`). |

---

## Installation & Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shaikmuzammil2911-ux/Annonation-quality-validator.git
   cd Annonation-quality-validator
   ```

2. **Verify Python installation**:
   ```bash
   python --version
   ```

3. **No package installation required**:
   The tool relies exclusively on Python's built-in standard library.

---

## Usage & Examples

### Command Syntax

```bash
python validate_annotations.py <path_to_csv_file>
```

Running without arguments or with `--help` prints the usage guide:
```bash
python validate_annotations.py --help
```

---

### Example: Successful Validation

Validating a properly formatted CSV file:

```bash
python validate_annotations.py sample_annotations.csv
```

**Terminal Output:**
```text
================================================================================
ANNOTATION QUALITY VALIDATOR REPORT
================================================================================
Target File : sample_annotations.csv
Total Rows  : 15
Passed Rows : 15
Failed Rows : 0
Total Errors: 0
Status      : PASSED
================================================================================
SUCCESS: All 15 annotation record(s) passed validation successfully.
================================================================================
```
*Process Exit Code: `0`*

---

### Example: Validation with Errors

Validating a dataset containing format violations:

```bash
python validate_annotations.py sample_annotations_with_errors.csv
```

**Terminal Output:**
```text
================================================================================
ANNOTATION QUALITY VALIDATOR REPORT
================================================================================
Target File : sample_annotations_with_errors.csv
Total Rows  : 13
Passed Rows : 1
Failed Rows : 12
Total Errors: 14
Status      : FAILED
================================================================================

VALIDATION ERRORS:
--------------------------------------------------------------------------------
[Row 3] Field 'task_id': Field 'task_id' is required and cannot be blank.
[Row 4] Field 'observed_location': Invalid observed_location 'TOP'. Allowed values: CENTER, LEFT, NOT_VISIBLE, RIGHT. [Task ID: TASK-2003]
[Row 5] Field 'decision': Invalid decision 'MAYBE'. Allowed values: MATCH, MISMATCH, UNCLEAR. [Task ID: TASK-2004]
[Row 6] Field 'confidence': Confidence score 0 is out of range. Must be a whole number between 1 and 5. [Task ID: TASK-2005]
[Row 7] Field 'confidence': Confidence score 6 is out of range. Must be a whole number between 1 and 5. [Task ID: TASK-2006]
[Row 8] Field 'confidence': Confidence score -1 is out of range. Must be a whole number between 1 and 5. [Task ID: TASK-2007]
[Row 9] Field 'confidence': Invalid confidence '3.5'. Decimal values are not allowed. Must be a whole number between 1 and 5. [Task ID: TASK-2008]
[Row 10] Field 'confidence': Invalid confidence 'HIGH'. Non-numeric text is not allowed. Must be a whole number between 1 and 5. [Task ID: TASK-2009]
[Row 11] Field 'observed_location': Field 'observed_location' is required and cannot be blank. Allowed values: LEFT, CENTER, RIGHT, NOT_VISIBLE. [Task ID: TASK-2010]
[Row 12] Field 'decision': Field 'decision' is required and cannot be blank. Allowed values: MATCH, MISMATCH, UNCLEAR. [Task ID: TASK-2011]
[Row 13] Field 'confidence': Field 'confidence' is required and cannot be blank. Must be a whole number between 1 and 5. [Task ID: TASK-2012]
[Row 14] Field 'observed_location': Invalid observed_location 'BEHIND'. Allowed values: CENTER, LEFT, NOT_VISIBLE, RIGHT. [Task ID: TASK-2013]
[Row 14] Field 'decision': Invalid decision 'PENDING'. Allowed values: MATCH, MISMATCH, UNCLEAR. [Task ID: TASK-2013]
[Row 14] Field 'confidence': Confidence score 7 is out of range. Must be a whole number between 1 and 5. [Task ID: TASK-2013]

ERROR SUMMARY BY TYPE:
--------------------------------------------------------------------------------
- BLANK_FIELD                 : 4 occurrence(s)
- CONFIDENCE_OUT_OF_RANGE     : 4 occurrence(s)
- INVALID_CONFIDENCE_TYPE     : 2 occurrence(s)
- INVALID_DECISION            : 2 occurrence(s)
- INVALID_LOCATION            : 2 occurrence(s)

================================================================================
FAILURE: 14 validation error(s) detected. Please correct the file.
================================================================================
```
*Process Exit Code: `1`*

---

## Exit Codes

The tool returns standard UNIX process exit codes:

| Exit Code | Meaning | When Triggered |
| :---: | :--- | :--- |
| `0` | **Passed** | The CSV file is fully valid and conforms to all schema and quality rules. |
| `1` | **Validation Errors** | File has schema issues (missing required columns, empty file) or record validation errors. |
| `2` | **Usage / CLI Error** | Missing argument, extra arguments, file not found, permission error, or unreadable path. |

---

## Automated Testing

The project includes a comprehensive suite of automated tests using Python's built-in `unittest` framework. All test fixtures execute in isolated temporary directories using `tempfile`.

### Running All Tests

```bash
python -m unittest test_validate_annotations.py -v
```

### Coverage Highlights

The test suite validates:
- [x] Valid CSV files that pass with zero errors.
- [x] Missing header columns (single and multiple).
- [x] Blank task IDs and preserved ID tracking in error reporting.
- [x] Blank location, decision, and confidence entries.
- [x] Unsupported categorical labels for `observed_location` and `decision`.
- [x] Confidence boundary validation (`1` and `5` pass; `0` and `6` fail).
- [x] Negative confidence values (`-1`, `-5`).
- [x] Decimal and non-numeric confidence inputs (`3.5`, `HIGH`).
- [x] Completely empty CSV files (0 bytes).
- [x] Command-line usage errors and missing arguments.
- [x] Multiple errors within a single row.
- [x] Multiple invalid rows with exact CSV physical line numbers.
- [x] Case-insensitive and space-padded categorical label matching.
- [x] Proper CLI exit codes (`0`, `1`, `2`).
- [x] UTF-8 files containing Byte Order Mark (`UTF-8 BOM`).

---

## Limitations & Disclaimer

- **Portfolio Demonstration**: This is an independent portfolio demonstration project using simulated synthetic datasets.
- **Non-Production Disclaimer**: It does not connect to, originate from, or represent any Amazon production system, internal tooling, or confidential dataset.
- **Single-Table Scope**: The validator is focused specifically on tabular CSV annotation quality and does not perform image or media-level validation.

---

## License

This project is open-source and released under the [MIT License](LICENSE).
