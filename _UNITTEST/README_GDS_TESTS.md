# GDS Comprehensive Tests

This directory contains comprehensive test suites for the GDS (Google Drive Shell) functionality, specifically focusing on the recently fixed commands: read, edit, upload, and echo.

## Test Files

### `test_gds_comprehensive.py`
The main comprehensive test suite that covers:

- **GDS read command**: Basic reading, line ranges, multiple ranges, --force option
- **GDS edit command**: Line-based editing, text-based editing, --preview, --backup, mixed mode
- **GDS upload command**: Single file upload, multiple file upload, --target-dir option
- **GDS echo command**: Basic text output, file creation with redirection

### `run_gds_tests.py`
A simple runner script that provides an easy interface to execute the comprehensive tests with user confirmation and clear instructions.

### `test_google_drive.py`
The original comprehensive test suite, now updated with:
- Option to run the new comprehensive tests via `--comprehensive` flag
- Removed timeout restrictions for upload tests that require user interaction
- Enhanced helper functions for user-interactive tests

## Key Features

### 🔧 Temporary Test Environment
- Uses hashed timestamp folders in `~/tmp` for isolated testing
- Automatic cleanup after test completion
- No interference with existing remote files

### ⏰ No Timeout Restrictions
- All tests allow unlimited time for user interaction
- Supports the manual nature of GDS remote command execution
- Clear user prompts and instructions throughout

### 📝 User Interaction Support
- Tests are designed around the GDS remote command workflow
- Tkinter window interactions are expected and supported
- Clear progress indicators and instructions

### 🧪 Comprehensive Coverage
- Tests all major command variations and options
- Error handling scenarios included
- Integration workflow tests combining multiple commands

## Usage

### Run All GDS Tests (Recommended)
```bash
# Run all test categories with user-friendly interface
python3 run_all_gds_tests.py

# Run specific categories
python3 run_all_gds_tests.py --category comprehensive
python3 run_all_gds_tests.py --category upload
python3 run_all_gds_tests.py --category traditional

# Skip confirmation prompt
python3 run_all_gds_tests.py --no-confirm
```

### Run Individual Test Categories
```bash
# Run only the new comprehensive tests (27 test methods)
python3 run_gds_tests.py
python3 test_google_drive.py --comprehensive

# Run only upload improvement tests (4 test methods)
python3 test_google_drive.py --upload-improvements

# Run all traditional tests (40+ test methods)
python3 test_google_drive.py
```

### Run Individual Test Methods
```bash
# Run specific test method
python3 test_gds_comprehensive.py --specific test_01_echo_basic
```

## Test Structure

### Test Setup
1. **Pre-cleanup**: Removes entire `~/tmp` directory to avoid duplicate folder confusion
2. Creates fresh `~/tmp` directory structure
3. Creates unique temporary folder in `~/tmp` with hashed timestamp
4. **Dedicated test shell**: Creates a new GDS logical shell for isolated testing
5. Generates local test files with various content types
6. Sets up remote test environment via GDS commands

### Test Execution
1. No timeouts to allow user interaction
2. Clear prompts for each user action required
3. All operations use remote command windows (including rm commands)
4. Verification of results after each operation

### Test Cleanup
1. **Complete tmp cleanup**: Removes entire `~/tmp` directory via remote command
2. **Test shell termination**: Properly terminates the dedicated test shell
3. Prevents duplicate folder confusion in Google Drive
4. Local test files remain for potential debugging

## Test Categories

### Echo Tests (`test_01_*` - `test_02_*`)
- Basic echo functionality
- File creation with redirection
- Quote handling

### Upload Tests (`test_03_*` - `test_05_*`)
- Single file upload
- Multiple file upload
- Upload with --target-dir option

### Read Tests (`test_06_*` - `test_09_*`)
- Basic file reading
- Line range reading
- --force option for cache bypass
- Multiple range reading with JSON format

### Edit Tests (`test_10_*` - `test_14_*`)
- Line-based replacement editing
- Text search and replace
- --preview mode for safe testing
- --backup mode for file protection
- Mixed mode combining line and text editing

### Integration Tests (`test_15_*`)
- Comprehensive workflow combining all commands

### File Content Tests (`test_16_*` - `test_18_*`)
- Cat command for displaying file content
- Grep command for content searching
- Find command for file location

### File Operations Tests (`test_19_*` - `test_22_*`)
- Mv command for moving/renaming files
- Ls command with advanced options (--detailed, -R)
- Edit command insert mode with [line, null] syntax
- Download command with --force option

### Python & Environment Tests (`test_23_*` - `test_25_*`)
- Python code execution (direct and file-based)
- Virtual environment management (create, activate, deactivate, delete)
- Pip package management with virtual environments

### Advanced Integration Tests (`test_26_*` - `test_27_*`)
- Advanced workflow combining multiple commands with project structure
- Comprehensive error handling scenarios

## Requirements

- Python 3.6+
- GOOGLE_DRIVE.py tool available in parent directory
- Google Drive Desktop for file synchronization
- User available for interactive command execution

## Notes

- Tests require active user participation due to the nature of GDS remote command execution
- Each test provides clear instructions on what user action is expected
- **Dedicated test shells**: Each test session uses its own GDS logical shell for isolation
- **Automatic tmp cleanup**: Tests automatically clean up `~/tmp` before and after execution
- **No duplicate folder confusion**: Pre-cleanup prevents Google Drive duplicate folder issues
- **Shell lifecycle management**: Test shells are created before tests and terminated after
- All rm operations use remote command windows (no direct permission errors)
- All tests use the same temporary folder pattern for easy identification

## Troubleshooting

### Test Failures
- Check that Google Drive Desktop is running
- Ensure you have write permissions in the Google Drive folder
- Verify that the GOOGLE_DRIVE.py tool is working correctly

### Cleanup Issues
- Tests automatically clean `~/tmp` before and after execution
- If cleanup fails, manually run: `GDS rm -rf ~/tmp`
- Check for leftover backup files if edit tests fail
- All cleanup operations use remote command windows for proper execution

### User Interaction Issues
- Each test waits indefinitely for user completion
- Use Ctrl+C to interrupt tests if needed
- Tests can be run individually to isolate issues 