#!/usr/bin/env python3
"""
Verification script for ZLS Code Actions Enhancement benchmark task.
Combines structural/AST checks with functional test validation.

Usage:
    python3 verify.py <path_to_zls_repo>

Returns exit code 0 if all checks pass, 1 otherwise.
Outputs a JSON report to stdout with detailed results.
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    category: str  # "structural" or "functional"
    details: str = ""
    weight: float = 1.0  # relative importance


@dataclass
class VerificationReport:
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    structural_score: float = 0.0
    functional_score: float = 0.0
    overall_score: float = 0.0
    results: list = field(default_factory=list)

    def add(self, result: CheckResult):
        self.results.append(asdict(result))
        self.total_checks += 1
        if result.passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1

    def compute_scores(self):
        structural = [r for r in self.results if r["category"] == "structural"]
        functional = [r for r in self.results if r["category"] == "functional"]

        if structural:
            total_w = sum(r["weight"] for r in structural)
            passed_w = sum(r["weight"] for r in structural if r["passed"])
            self.structural_score = passed_w / total_w if total_w > 0 else 0

        if functional:
            total_w = sum(r["weight"] for r in functional)
            passed_w = sum(r["weight"] for r in functional if r["passed"])
            self.functional_score = passed_w / total_w if total_w > 0 else 0

        # Overall: 40% structural, 60% functional
        self.overall_score = 0.4 * self.structural_score + 0.6 * self.functional_score


def read_file(path: str) -> Optional[str]:
    """Read a file and return its contents, or None if it doesn't exist."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError):
        return None


# =============================================================================
# STRUCTURAL CHECKS
# =============================================================================

def check_file_exists(repo: str, relpath: str) -> CheckResult:
    """Check that a required file exists."""
    full = os.path.join(repo, relpath)
    exists = os.path.isfile(full)
    return CheckResult(
        name=f"file_exists:{relpath}",
        passed=exists,
        category="structural",
        details=f"{'Found' if exists else 'Missing'}: {relpath}",
        weight=0.5,
    )


def check_code_actions_imports(repo: str) -> list[CheckResult]:
    """Check that code_actions.zig has the required new imports."""
    results = []
    content = read_file(os.path.join(repo, "src/features/code_actions.zig"))
    if content is None:
        results.append(CheckResult(
            name="imports:code_actions_file",
            passed=False, category="structural",
            details="code_actions.zig not found",
        ))
        return results

    # Check for Token import
    has_token = bool(re.search(r'const\s+Token\s*=\s*std\.zig\.Token', content))
    results.append(CheckResult(
        name="imports:Token",
        passed=has_token, category="structural",
        details="Token = std.zig.Token import " + ("found" if has_token else "missing"),
        weight=0.5,
    ))

    # Check for DocumentScope import
    has_docscope = bool(re.search(r'const\s+DocumentScope\s*=\s*@import\(\s*"\.\.\/DocumentScope\.zig"\s*\)', content))
    results.append(CheckResult(
        name="imports:DocumentScope",
        passed=has_docscope, category="structural",
        details="DocumentScope import " + ("found" if has_docscope else "missing"),
        weight=0.5,
    ))

    return results


def check_builder_fields(repo: str) -> list[CheckResult]:
    """Check that Builder struct has the required new fields."""
    results = []
    content = read_file(os.path.join(repo, "src/features/code_actions.zig"))
    if content is None:
        return [CheckResult(name="builder:file", passed=False, category="structural", details="File not found")]

    # Extract Builder struct content (rough extraction)
    builder_match = re.search(r'pub const Builder = struct \{(.*?)\n\};', content, re.DOTALL)
    if not builder_match:
        results.append(CheckResult(
            name="builder:struct_exists",
            passed=False, category="structural",
            details="Builder struct not found",
            weight=2.0,
        ))
        return results

    builder_content = builder_match.group(1)

    # Check only_kinds field
    has_only_kinds = bool(re.search(r'only_kinds\s*:', builder_content))
    results.append(CheckResult(
        name="builder:only_kinds_field",
        passed=has_only_kinds, category="structural",
        details="only_kinds field " + ("found" if has_only_kinds else "missing"),
        weight=1.5,
    ))

    # Check actions field (moved inside Builder)
    has_actions = bool(re.search(r'actions\s*:\s*std\.ArrayListUnmanaged\(types\.CodeAction\)', builder_content))
    results.append(CheckResult(
        name="builder:actions_field",
        passed=has_actions, category="structural",
        details="actions field inside Builder " + ("found" if has_actions else "missing"),
        weight=1.5,
    ))

    # Check fixall_text_edits field
    has_fixall = bool(re.search(r'fixall_text_edits\s*:\s*std\.ArrayListUnmanaged\(types\.TextEdit\)', builder_content))
    results.append(CheckResult(
        name="builder:fixall_text_edits_field",
        passed=has_fixall, category="structural",
        details="fixall_text_edits field " + ("found" if has_fixall else "missing"),
        weight=1.5,
    ))

    # Check generateCodeAction takes ErrorBundle
    has_error_bundle = bool(re.search(r'generateCodeAction\s*\(\s*builder.*?error_bundle\s*:\s*std\.zig\.ErrorBundle', content, re.DOTALL))
    results.append(CheckResult(
        name="builder:generateCodeAction_ErrorBundle",
        passed=has_error_bundle, category="structural",
        details="generateCodeAction takes ErrorBundle " + ("yes" if has_error_bundle else "no"),
        weight=2.0,
    ))

    # Check wantKind method exists
    has_want_kind = bool(re.search(r'fn\s+wantKind\s*\(', content))
    results.append(CheckResult(
        name="builder:wantKind_method",
        passed=has_want_kind, category="structural",
        details="wantKind method " + ("found" if has_want_kind else "missing"),
        weight=1.0,
    ))

    # Check generateCodeActionsInRange method exists
    has_range_method = bool(re.search(r'fn\s+generateCodeActionsInRange\s*\(', content))
    results.append(CheckResult(
        name="builder:generateCodeActionsInRange",
        passed=has_range_method, category="structural",
        details="generateCodeActionsInRange " + ("found" if has_range_method else "missing"),
        weight=1.5,
    ))

    return results


def check_organize_imports(repo: str) -> list[CheckResult]:
    """Check that organize imports feature is implemented."""
    results = []
    content = read_file(os.path.join(repo, "src/features/code_actions.zig"))
    if content is None:
        return [CheckResult(name="organize:file", passed=False, category="structural", details="File not found")]

    # Check handleUnorganizedImport function
    has_handler = bool(re.search(r'fn\s+handleUnorganizedImport\s*\(', content))
    results.append(CheckResult(
        name="organize:handleUnorganizedImport",
        passed=has_handler, category="structural",
        details="handleUnorganizedImport " + ("found" if has_handler else "missing"),
        weight=2.0,
    ))

    # Check ImportDecl struct
    has_import_decl = bool(re.search(r'pub const ImportDecl = struct', content))
    results.append(CheckResult(
        name="organize:ImportDecl_struct",
        passed=has_import_decl, category="structural",
        details="ImportDecl struct " + ("found" if has_import_decl else "missing"),
        weight=2.0,
    ))

    # Check ImportDecl.Kind enum
    has_kind_enum = bool(re.search(r'pub const Kind = enum', content))
    results.append(CheckResult(
        name="organize:ImportDecl_Kind_enum",
        passed=has_kind_enum, category="structural",
        details="ImportDecl.Kind enum " + ("found" if has_kind_enum else "missing"),
        weight=1.0,
    ))

    # Check that Kind has the right variants (std, builtin, build_options, package, file)
    kind_variants = ["std", "builtin", "build_options", "package", "file"]
    for variant in kind_variants:
        # Look for the variant as an enum field
        has_variant = bool(re.search(rf'\.{variant}\b', content))
        results.append(CheckResult(
            name=f"organize:Kind_{variant}",
            passed=has_variant, category="structural",
            details=f"Kind.{variant} " + ("found" if has_variant else "missing"),
            weight=0.3,
        ))

    # Check getImportsDecls function
    has_get_imports = bool(re.search(r'pub fn getImportsDecls\s*\(', content))
    results.append(CheckResult(
        name="organize:getImportsDecls",
        passed=has_get_imports, category="structural",
        details="getImportsDecls " + ("found" if has_get_imports else "missing"),
        weight=2.0,
    ))

    # Check lessThan sorting function
    has_less_than = bool(re.search(r'pub fn lessThan\s*\(', content))
    results.append(CheckResult(
        name="organize:lessThan",
        passed=has_less_than, category="structural",
        details="ImportDecl.lessThan " + ("found" if has_less_than else "missing"),
        weight=1.0,
    ))

    # Check source.organizeImports code action kind
    has_organize_kind = bool(re.search(r'source\.organizeImports', content))
    results.append(CheckResult(
        name="organize:code_action_kind",
        passed=has_organize_kind, category="structural",
        details="source.organizeImports kind " + ("found" if has_organize_kind else "missing"),
        weight=1.0,
    ))

    # Check that handleUnorganizedImport is called from generateCodeAction
    has_call = bool(re.search(r'handleUnorganizedImport\s*\(', content))
    results.append(CheckResult(
        name="organize:called_from_generateCodeAction",
        passed=has_call, category="structural",
        details="handleUnorganizedImport call " + ("found" if has_call else "missing"),
        weight=1.0,
    ))

    return results


def check_string_literal_conversion(repo: str) -> list[CheckResult]:
    """Check that string literal conversion code actions are implemented."""
    results = []
    content = read_file(os.path.join(repo, "src/features/code_actions.zig"))
    if content is None:
        return [CheckResult(name="string:file", passed=False, category="structural", details="File not found")]

    # Check generateStringLiteralCodeActions
    has_str_to_ml = bool(re.search(r'fn\s+generateStringLiteralCodeActions\s*\(', content))
    results.append(CheckResult(
        name="string:generateStringLiteralCodeActions",
        passed=has_str_to_ml, category="structural",
        details="generateStringLiteralCodeActions " + ("found" if has_str_to_ml else "missing"),
        weight=2.0,
    ))

    # Check generateMultilineStringCodeActions
    has_ml_to_str = bool(re.search(r'fn\s+generateMultilineStringCodeActions\s*\(', content))
    results.append(CheckResult(
        name="string:generateMultilineStringCodeActions",
        passed=has_ml_to_str, category="structural",
        details="generateMultilineStringCodeActions " + ("found" if has_ml_to_str else "missing"),
        weight=2.0,
    ))

    # Check for .refactor code action kind
    has_refactor_kind = bool(re.search(r'\.kind\s*=\s*\.refactor', content))
    results.append(CheckResult(
        name="string:refactor_kind",
        passed=has_refactor_kind, category="structural",
        details=".refactor kind " + ("found" if has_refactor_kind else "missing"),
        weight=1.0,
    ))

    # Check for string_literal.parseAlloc usage
    has_parse_alloc = bool(re.search(r'string_literal\.parseAlloc', content))
    results.append(CheckResult(
        name="string:parseAlloc_usage",
        passed=has_parse_alloc, category="structural",
        details="string_literal.parseAlloc " + ("found" if has_parse_alloc else "missing"),
        weight=1.0,
    ))

    # Check carriage return / control character handling
    # The expected code uses "\\n\\r" in indexOfNonePos and control char ranges like 0x0b...0x0c
    has_cr_check = bool(re.search(r'\\\\n\\\\r|0x0d|0x0e|carriage|isControl', content))
    results.append(CheckResult(
        name="string:carriage_return_check",
        passed=has_cr_check, category="structural",
        details="Carriage return/control char check " + ("found" if has_cr_check else "missing"),
        weight=0.5,
    ))

    # Check UTF-8 validation
    has_utf8_check = bool(re.search(r'utf8ValidateSlice|utf8Validate', content))
    results.append(CheckResult(
        name="string:utf8_validation",
        passed=has_utf8_check, category="structural",
        details="UTF-8 validation " + ("found" if has_utf8_check else "missing"),
        weight=0.5,
    ))

    return results


def check_config_changes(repo: str) -> list[CheckResult]:
    """Check Config.zig changes."""
    results = []
    content = read_file(os.path.join(repo, "src/Config.zig"))
    if content is None:
        return [CheckResult(name="config:file", passed=False, category="structural", details="File not found")]

    # Check force_autofix exists
    has_force_autofix = bool(re.search(r'force_autofix\s*:', content))
    results.append(CheckResult(
        name="config:force_autofix",
        passed=has_force_autofix, category="structural",
        details="force_autofix field " + ("found" if has_force_autofix else "missing"),
        weight=1.0,
    ))

    # Check enable_autofix is removed
    has_enable_autofix = bool(re.search(r'enable_autofix\s*:', content))
    results.append(CheckResult(
        name="config:enable_autofix_removed",
        passed=not has_enable_autofix, category="structural",
        details="enable_autofix " + ("still present (should be removed)" if has_enable_autofix else "removed"),
        weight=1.0,
    ))

    return results


def check_test_file(repo: str) -> list[CheckResult]:
    """Check that required tests exist in the test file."""
    results = []
    content = read_file(os.path.join(repo, "tests/lsp_features/code_actions.zig"))
    if content is None:
        return [CheckResult(name="tests:file", passed=False, category="structural", details="Test file not found")]

    # Check for organize imports tests
    required_test_patterns = [
        (r'test\s+"organize imports"', "organize_imports_basic", 2.0),
        (r'test\s+"organize imports - .*bubbles? up"', "organize_imports_bubble_up", 1.0),
        (r'test\s+"organize imports - .*scope"', "organize_imports_scope", 1.0),
        (r'test\s+"organize imports - .*comments?"', "organize_imports_comments", 1.0),
        (r'test\s+"organize imports - .*field.access"', "organize_imports_field_access", 1.0),
        (r'test\s+"organize imports - .*edge.cases?"', "organize_imports_edge_cases", 1.0),
        (r'test\s+"convert multiline string literal"', "convert_multiline_to_string", 2.0),
        (r'test\s+"convert string literal to multiline"', "convert_string_to_multiline", 2.0),
        (r'test\s+"convert string literal to multiline - .*escapes?"', "convert_string_escapes", 1.0),
        (r'test\s+"convert string literal to multiline - .*invalid"', "convert_string_invalid", 1.0),
        (r'test\s+"convert string literal to multiline - .*cursor.*"', "convert_string_cursor_outside", 1.0),
    ]

    for pattern, name, weight in required_test_patterns:
        has_test = bool(re.search(pattern, content, re.IGNORECASE))
        results.append(CheckResult(
            name=f"tests:{name}",
            passed=has_test, category="structural",
            details=f"Test '{name}' " + ("found" if has_test else "missing"),
            weight=weight,
        ))

    # Check for testOrganizeImports helper function
    has_organize_helper = bool(re.search(r'fn\s+testOrganizeImports\s*\(', content))
    results.append(CheckResult(
        name="tests:testOrganizeImports_helper",
        passed=has_organize_helper, category="structural",
        details="testOrganizeImports helper " + ("found" if has_organize_helper else "missing"),
        weight=1.0,
    ))

    # Check for testConvertString helper function
    has_convert_helper = bool(re.search(r'fn\s+testConvertString\s*\(', content))
    results.append(CheckResult(
        name="tests:testConvertString_helper",
        passed=has_convert_helper, category="structural",
        details="testConvertString helper " + ("found" if has_convert_helper else "missing"),
        weight=1.0,
    ))

    # Check for testDiagnostic updated with filter_kind parameter
    has_filter_kind = bool(re.search(r'filter_kind', content))
    results.append(CheckResult(
        name="tests:filter_kind_support",
        passed=has_filter_kind, category="structural",
        details="filter_kind in test infra " + ("found" if has_filter_kind else "missing"),
        weight=1.0,
    ))

    return results


def check_server_integration(repo: str) -> list[CheckResult]:
    """Check that Server.zig has proper integration with the new code action features."""
    results = []
    content = read_file(os.path.join(repo, "src/Server.zig"))
    if content is None:
        return [CheckResult(name="server:file", passed=False, category="structural", details="File not found")]

    # Check that only_kinds is used in code action handling
    has_only_kinds = bool(re.search(r'only_kinds', content))
    results.append(CheckResult(
        name="server:only_kinds_integration",
        passed=has_only_kinds, category="structural",
        details="only_kinds integration " + ("found" if has_only_kinds else "missing"),
        weight=1.0,
    ))

    # Check that generateCodeActionsInRange is called
    has_range_call = bool(re.search(r'generateCodeActionsInRange', content))
    results.append(CheckResult(
        name="server:generateCodeActionsInRange_call",
        passed=has_range_call, category="structural",
        details="generateCodeActionsInRange call " + ("found" if has_range_call else "missing"),
        weight=1.0,
    ))

    # Check for force_autofix reference (replacing enable_autofix)
    has_force_autofix = bool(re.search(r'force_autofix', content))
    results.append(CheckResult(
        name="server:force_autofix_reference",
        passed=has_force_autofix, category="structural",
        details="force_autofix reference " + ("found" if has_force_autofix else "missing"),
        weight=1.0,
    ))

    # Check that getAutofixMode references source.fixAll
    has_fixall_mode = bool(re.search(r'source\.fix[Aa]ll', content))
    results.append(CheckResult(
        name="server:source_fixall_mode",
        passed=has_fixall_mode, category="structural",
        details="source.fixAll in autofix mode " + ("found" if has_fixall_mode else "missing"),
        weight=0.5,
    ))

    # Check for ErrorBundle usage in autofix function
    has_error_bundle = bool(re.search(r'error_bundle|ErrorBundle', content))
    results.append(CheckResult(
        name="server:error_bundle_usage",
        passed=has_error_bundle, category="structural",
        details="ErrorBundle usage " + ("found" if has_error_bundle else "missing"),
        weight=1.0,
    ))

    return results


def check_code_actions_line_growth(repo: str) -> list[CheckResult]:
    """Check that code_actions.zig has grown substantially (686 -> ~1213 lines)."""
    results = []
    content = read_file(os.path.join(repo, "src/features/code_actions.zig"))
    if content is None:
        return [CheckResult(name="growth:file", passed=False, category="structural", details="File not found")]

    line_count = content.count("\n")

    # Base was 686 lines, expected ~1213 lines
    # Allow some tolerance - anything above 950 lines suggests the features were added
    passed = line_count > 950
    results.append(CheckResult(
        name="growth:code_actions_lines",
        passed=passed, category="structural",
        details=f"code_actions.zig has {line_count} lines (expected >950, base was 686)",
        weight=1.0,
    ))

    # Check test file growth too (417 -> ~924 lines)
    test_content = read_file(os.path.join(repo, "tests/lsp_features/code_actions.zig"))
    if test_content:
        test_lines = test_content.count("\n")
        test_passed = test_lines > 650
        results.append(CheckResult(
            name="growth:test_file_lines",
            passed=test_passed, category="structural",
            details=f"code_actions test has {test_lines} lines (expected >650, base was 417)",
            weight=1.0,
        ))

    return results


# =============================================================================
# FUNCTIONAL CHECKS (Test execution)
# =============================================================================

def run_zig_tests(repo: str) -> list[CheckResult]:
    """Attempt to build and run the ZLS code action tests."""
    results = []

    # First check if zig is available
    try:
        zig_version = subprocess.run(
            ["zig", "version"], capture_output=True, text=True, timeout=10
        )
        if zig_version.returncode != 0:
            results.append(CheckResult(
                name="functional:zig_available",
                passed=False, category="functional",
                details="Zig compiler not found or not working",
                weight=0.0,
            ))
            return results
    except (FileNotFoundError, subprocess.TimeoutExpired):
        results.append(CheckResult(
            name="functional:zig_available",
            passed=False, category="functional",
            details="Zig compiler not available - skipping functional tests",
            weight=0.0,
        ))
        return results

    results.append(CheckResult(
        name="functional:zig_available",
        passed=True, category="functional",
        details=f"Zig version: {zig_version.stdout.strip()}",
        weight=0.0,
    ))

    # Try to build the project
    try:
        build_result = subprocess.run(
            ["zig", "build"],
            capture_output=True, text=True, timeout=300,
            cwd=repo
        )
        build_passed = build_result.returncode == 0
        results.append(CheckResult(
            name="functional:build",
            passed=build_passed, category="functional",
            details="Build " + ("succeeded" if build_passed else f"failed: {build_result.stderr[:500]}"),
            weight=3.0,
        ))
        if not build_passed:
            return results  # Can't run tests if build fails
    except subprocess.TimeoutExpired:
        results.append(CheckResult(
            name="functional:build",
            passed=False, category="functional",
            details="Build timed out after 300s",
            weight=3.0,
        ))
        return results

    # Run the specific code actions tests
    test_cases = [
        ("discard value", 2.0),
        ("discard value with comments", 1.0),
        ("discard function parameter", 1.5),
        ("discard captures", 1.5),
        ("remove pointless discard", 1.0),
        ("variable never mutated", 1.0),
        ("organize imports", 3.0),
        ("organize imports - bubbles up", 2.0),
        ("organize imports - scope", 2.0),
        ("organize imports - comments", 2.0),
        ("organize imports - field access", 2.0),
        ("organize imports - edge cases", 2.0),
        ("convert multiline string literal", 3.0),
        ("convert string literal to multiline", 3.0),
        ("convert string literal to multiline - cursor outside of string literal", 2.0),
        ("convert string literal to multiline - escapes", 2.0),
        ("convert string literal to multiline - invalid", 2.0),
    ]

    # Try running all tests at once first
    try:
        test_result = subprocess.run(
            ["zig", "build", "test", "-Dtest-filter="],
            capture_output=True, text=True, timeout=300,
            cwd=repo
        )

        # If bulk test passes, mark all as passed
        if test_result.returncode == 0:
            for test_name, weight in test_cases:
                results.append(CheckResult(
                    name=f"functional:test:{test_name}",
                    passed=True, category="functional",
                    details=f"Test '{test_name}' passed (bulk run)",
                    weight=weight,
                ))
        else:
            # Try individual tests to get granular results
            for test_name, weight in test_cases:
                try:
                    individual_result = subprocess.run(
                        ["zig", "build", "test", f"-Dtest-filter={test_name}"],
                        capture_output=True, text=True, timeout=120,
                        cwd=repo
                    )
                    passed = individual_result.returncode == 0
                    results.append(CheckResult(
                        name=f"functional:test:{test_name}",
                        passed=passed, category="functional",
                        details=f"Test '{test_name}' " + ("passed" if passed else "failed"),
                        weight=weight,
                    ))
                except subprocess.TimeoutExpired:
                    results.append(CheckResult(
                        name=f"functional:test:{test_name}",
                        passed=False, category="functional",
                        details=f"Test '{test_name}' timed out",
                        weight=weight,
                    ))

    except subprocess.TimeoutExpired:
        results.append(CheckResult(
            name="functional:test_run",
            passed=False, category="functional",
            details="Test execution timed out after 300s",
            weight=5.0,
        ))

    return results


# =============================================================================
# MAIN
# =============================================================================

def run_all_checks(repo: str) -> VerificationReport:
    report = VerificationReport()

    # --- Structural checks ---
    print("Running structural checks...", file=sys.stderr)

    # File existence
    for f in [
        "src/features/code_actions.zig",
        "tests/lsp_features/code_actions.zig",
        "src/Server.zig",
        "src/Config.zig",
    ]:
        report.add(check_file_exists(repo, f))

    # Import checks
    for r in check_code_actions_imports(repo):
        report.add(r)

    # Builder struct checks
    for r in check_builder_fields(repo):
        report.add(r)

    # Organize imports checks
    for r in check_organize_imports(repo):
        report.add(r)

    # String literal conversion checks
    for r in check_string_literal_conversion(repo):
        report.add(r)

    # Config changes
    for r in check_config_changes(repo):
        report.add(r)

    # Test file checks
    for r in check_test_file(repo):
        report.add(r)

    # Server integration
    for r in check_server_integration(repo):
        report.add(r)

    # Line count growth
    for r in check_code_actions_line_growth(repo):
        report.add(r)

    # --- Functional checks ---
    print("Running functional checks...", file=sys.stderr)
    for r in run_zig_tests(repo):
        report.add(r)

    report.compute_scores()
    return report


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_zls_repo>", file=sys.stderr)
        sys.exit(1)

    repo = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo):
        print(f"Error: {repo} is not a directory", file=sys.stderr)
        sys.exit(1)

    report = run_all_checks(repo)

    # Print results to stderr for human readability
    print("\n" + "=" * 60, file=sys.stderr)
    print("VERIFICATION REPORT", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    for r in report.results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}: {r['details']}", file=sys.stderr)

    print(f"\n--- Summary ---", file=sys.stderr)
    print(f"Total checks: {report.total_checks}", file=sys.stderr)
    print(f"Passed: {report.passed_checks}", file=sys.stderr)
    print(f"Failed: {report.failed_checks}", file=sys.stderr)
    print(f"Structural score: {report.structural_score:.1%}", file=sys.stderr)
    print(f"Functional score: {report.functional_score:.1%}", file=sys.stderr)
    print(f"Overall score:    {report.overall_score:.1%}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Print JSON report to stdout
    output = {
        "total_checks": report.total_checks,
        "passed_checks": report.passed_checks,
        "failed_checks": report.failed_checks,
        "structural_score": round(report.structural_score, 4),
        "functional_score": round(report.functional_score, 4),
        "overall_score": round(report.overall_score, 4),
        "results": report.results,
    }
    print(json.dumps(output, indent=2))

    # Exit code: 0 if overall score >= 0.8, 1 otherwise
    sys.exit(0 if report.overall_score >= 0.8 else 1)


if __name__ == "__main__":
    main()
