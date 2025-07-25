# EXPORT

Environment Variable Export Tool

## Description

EXPORT is a comprehensive tool for setting and managing environment variables. It automatically writes them to multiple shell configuration files and ensures environment variables persist across terminal sessions by updating ~/.bash_profile, ~/.bashrc, and ~/.zshrc.

## Usage

### Setting Variables
```bash
EXPORT <variable_name> <value>
```

### Removing Variables
```bash
EXPORT --remove <variable_name>
EXPORT --undo <variable_name>
```

### Other Options
```bash
EXPORT --update
EXPORT --help
```

## Arguments

- `variable_name`: Name of the environment variable to export/remove
- `value`: Value to assign to the variable (for setting)

## Options

- `--help, -h`: Show help message
- `--remove, --undo, -r`: Remove an existing environment variable from all config files
- `--update`: Update shell configuration files (source all config files)

## Examples

### Setting Variables
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

### Removing Variables
```bash
# Remove environment variable
EXPORT --remove MY_VAR

# Alternative syntax
EXPORT --undo OPENROUTER_API_KEY
EXPORT -r MY_MESSAGE
```

### Configuration Management
```bash
# Update shell configurations
EXPORT --update

# Get help
EXPORT --help
```

### RUN Integration
```bash
# Get JSON output
RUN --show EXPORT MY_VAR "test value"
RUN --show EXPORT --remove MY_VAR
```

## Features

- **Multi-File Update**: Automatically updates .bash_profile, .bashrc, and .zshrc
- **Backup Creation**: Creates backup files before modification
- **Duplicate Removal**: Removes existing export statements before adding new ones
- **Variable Removal**: Complete removal of environment variables from all config files
- **Current Session**: Updates both config files and current shell session
- **Validation**: Checks variable names for proper format
- **Cross-Shell Support**: Works with Bash, Zsh, and other shells

## Configuration Files

The tool manages environment variables in these files:
- `~/.bash_profile` (Bash login shells)
- `~/.bashrc` (Bash non-login shells)  
- `~/.zshrc` (Zsh shells)

## Notes

- Variable names must be valid shell identifiers
- Changes take effect immediately in current session
- New terminal sessions will automatically load the variables
- Use `--update` to refresh configuration without restarting terminal
- Backup files are created with `.backup` extension before modifications 