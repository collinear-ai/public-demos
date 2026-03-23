# SWE-Bench Task: ZLS Code Actions Enhancement

## Repository
- **Name:** zigtools/zls (Zig Language Server)
- **Language:** Zig (99.8%)
- **Base commit:** `b2e89dfe` (2024-11-01)
- **License:** MIT

## Task Description

Implement a comprehensive enhancement to the ZLS code action system. The existing codebase provides basic "quickfix" code actions (unused variable discard, remove pointless discard, camelCase function rename, etc.) that are generated from compiler diagnostics. You need to extend this system with three new feature areas, refactor the Builder API, and update configuration.

This task aggregates work from **4 major PRs and 12+ supporting commits** spanning October 2024 to February 2025.

---

## Feature Requirements

### 1. Organize Imports Code Action (`source.organizeImports`)

Implement a code action that sorts and organizes `@import` declarations at the top of a Zig file. The action should:

- **Extract all import declarations** from the root scope of a file, including:
  - Direct imports: `const std = @import("std");`
  - Field access imports (second-order): `const ascii = std.ascii;` (where `std` is itself an import)
  - Imports with doc comments (preserve and move comments with the import)

- **Categorize imports** into groups (in this order):
  1. `std` (standard library)
  2. `builtin` and `root`
  3. `build_options`
  4. External packages (non-file imports)
  5. File imports (ending in `.zig`)

- **Sort imports** within each group:
  - Case-insensitive alphabetical sorting
  - Second-order imports (e.g., `const ascii = std.ascii`) should sort after their parent import
  - File imports with path separators sort by the full path; others sort by name

- **Generate text edits** that:
  - Insert all sorted imports at the top of the file (after any container doc comments)
  - Remove the original import declarations (including their line breaks)
  - Add blank line separators between different import groups

- **Register** the code action with kind `source.organizeImports`
- **Skip** generation if the file has parse errors
- **Create** an `ImportDecl` struct to represent imports with fields: `var_decl`, `first_comment_token`, `name`, `value`, `parent_name`, `parent_value`
- **Create** a `getImportsDecls` function that uses the AST and `DocumentScope` to extract imports, iterating until no more second-order imports are found

### 2. String Literal Conversion Code Actions (`refactor`)

Implement bidirectional conversion between regular string literals and multiline string literals:

#### 2a. String Literal to Multiline (`generateStringLiteralCodeActions`)
- Convert a regular string literal (`"hello\nworld"`) to a multiline string literal (`\\hello` / `\\world`)
- Parse the string literal content using `std.zig.string_literal.parseAlloc`
- **Reject** conversion if:
  - The string contains control characters (other than `\n`)
  - The parsed result is not valid UTF-8
  - The literal is a test name (`keyword_test` before it) or an extern function name (`keyword_extern` before it)
- Replace newlines with multiline string literal line continuations (hardcoded 4-space indent)
- Register with code action kind `.refactor`

#### 2b. Multiline to String Literal (`generateMultilineStringCodeActions`)
- Convert multiline string literal lines back to a single string literal
- Collect all consecutive `multiline_string_literal_line` tokens
- Escape special characters (newlines become `\n`, tabs become `\t`, etc.)
- **Reject** conversion if the multiline string contains carriage returns (`\r`)
- Register with code action kind `.refactor`

#### 2c. Range-based Dispatch (`generateCodeActionsInRange`)
- New public method on `Builder` that takes a `types.Range`
- Use `Analyser.getPositionContext` to determine if the cursor is within a string literal
- Dispatch to the appropriate conversion function based on the token type at the cursor position

### 3. Code Action Kind Filtering

Add server-side filtering of code actions by kind:

- Add an `only_kinds` field to `Builder`: `?std.EnumSet(std.meta.Tag(types.CodeActionKind))`
- Add a `wantKind` method that returns `false` if the client explicitly excluded this kind
- Check `wantKind` before generating organize imports and string literal conversion actions

### 4. Builder API Refactoring

Refactor the `Builder` struct:

- **Move `actions` list inside Builder**: Add `actions: std.ArrayListUnmanaged(types.CodeAction) = .empty` as a field
- **Add `fixall_text_edits`**: `std.ArrayListUnmanaged(types.TextEdit) = .empty` for collecting fix-all edits
- **Change `generateCodeAction` signature**: Instead of taking individual `types.Diagnostic` objects, accept `std.zig.ErrorBundle` and iterate over its messages internally
- **Generate consolidated fixAll action**: After processing all diagnostics, if there are fixall text edits, append a single `source.fixAll` code action
- **Simplify handler signatures**: Remove the `actions` and `remove_capture_actions` parameters from all `handle*` functions. They should use `builder.actions` and `builder.fixall_text_edits` directly instead
- **Add new imports**: `Token = std.zig.Token` and `DocumentScope = @import("../DocumentScope.zig")`
- **Call `handleUnorganizedImport`** at the start of `generateCodeAction`, before processing error diagnostics

### 5. Configuration Update (src/Config.zig)

- **Rename** `enable_autofix: bool = false` to `force_autofix: bool = false`
- **Update** the doc comment to: `Work around editors that do not support 'source.fixall' code actions on save. This option may delivered a substandard user experience. Please refer to the installation guide to see which editors natively support code actions on save.`

---

## Files to Modify

| File | Type of Change |
|------|---------------|
| `src/features/code_actions.zig` | Major additions + refactoring (686 -> 1213 lines) |
| `tests/lsp_features/code_actions.zig` | New test cases (417 -> 924 lines) |
| `src/Config.zig` | Rename `enable_autofix` -> `force_autofix` |
| `src/Server.zig` | Integration changes for new Builder API |

## Expected Test Coverage

The following test cases should be added to `tests/lsp_features/code_actions.zig`:

1. **Organize Imports Tests:**
   - Basic organize imports (sort std before file imports)
   - Second-order imports bubble up correctly
   - Imports within different scopes are handled
   - Imports with doc comments are preserved
   - Field access imports (`@embedFile`)
   - Edge cases (duplicate imports, mixed declarations)

2. **String Literal Conversion Tests:**
   - Convert multiline string literal to regular string
   - Convert regular string literal to multiline
   - Cursor outside of string literal (no action)
   - Escape character handling
   - Invalid conversions (control chars, carriage returns)

---

## Constraints

- All code must be in Zig
- Must integrate with the existing LSP protocol types from the `lsp` package
- Must use the existing `offsets` module for position/range calculations
- Must maintain backward compatibility with existing quickfix code actions
- All existing tests must continue to pass
- The organize imports algorithm must handle circular/forward references (second-order imports where the parent import hasn't been found yet) by iterating until stable

## Difficulty

**Hard** - This task requires:
- Deep understanding of the Zig AST structure
- Knowledge of LSP protocol code action kinds
- Complex sorting algorithm with multiple grouping criteria
- String parsing and escape handling
- Careful integration with existing Builder pattern
- Understanding of the ZLS DocumentScope for symbol resolution
