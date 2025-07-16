# EXPORT

Environment Variable Export Tool

## Description

EXPORT is a comprehensive tool for setting environment variables and automatically writing them to multiple shell configuration files. It ensures environment variables persist across terminal sessions by updating ~/.bash_profile, ~/.bashrc, and ~/.zshrc.

## Usage

```bash
EXPORT <variable_name> <value>
```

## Arguments

- `variable_name`: Name of the environment variable to export
- `value`: Value to assign to the variable

## Options

- `--help, -h`: Show help message

## Examples

### Basic Usage
```bash
# Export API key
EXPORT OPENROUTER_API_KEY "sk-or-v1-..."

# Export PATH addition
EXPORT PATH "/usr/local/bin:$PATH"

# Export custom variable
EXPORT MY_VAR "some value"

# Export variable with spaces
EXPORT MY_MESSAGE "Hello World"
```

### RUN Integration
```bash
# Get JSON output
RUN --show EXPORT MY_VAR "test value"
```

## Features

- **Multi-File Update**: Automatically updates .bash_profile, .bashrc, and .zshrc
- **Backup Creation**: Creates backup files before modification
- **Duplicate Removal**: Removes existing export statements before adding new ones
- **Current Session**: Sets variable in current environment immediately
- **RUN Compatible**: Works with RUN command for JSON output
- **Validation**: Validates variable names for proper format

## Output

When executed directly, the tool shows which files were updated and provides instructions for applying changes. When used with RUN, it returns JSON with operation status and file modification details.

## Files Modified

The tool updates the following configuration files:
- `~/.bash_profile`
- `~/.bashrc`
- `~/.zshrc`

## Dependencies

- Python 3.9+
- File system write permissions

## Notes

- Creates backup files (.backup extension) before modification
- You may need to restart terminal or run `source ~/.bash_profile` to apply changes
- Validates variable names to ensure they follow shell conventions
- RUN mode provides JSON output for automation
- Direct execution shows detailed update information 