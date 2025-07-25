# ALIAS

Permanent Shell Alias Creation Tool

## Description

ALIAS is a comprehensive tool for creating and managing permanent command aliases. It automatically writes aliases to multiple shell configuration files and ensures they persist across terminal sessions by updating ~/.bash_profile, ~/.bashrc, and ~/.zshrc.

## Usage

### Creating Aliases
```bash
ALIAS <alias_name> <alias_command>
```

### Removing Aliases
```bash
ALIAS --remove <alias_name>
ALIAS --undo <alias_name>
```

### Other Options
```bash
ALIAS --update
ALIAS --help
```

## Arguments

- `alias_name`: The short name for the alias (cannot be 'ALIAS')
- `alias_command`: The command that the alias will execute (for creating)

## Options

- `--help, -h`: Show help message
- `--remove, --undo, -r`: Remove an existing alias from all config files
- `--update`: Update shell configuration files (source all config files)

## Examples

### Creating Basic Aliases
```bash
# Create simple aliases
ALIAS ll "ls -la"
ALIAS gs "git status"
ALIAS python python3

# Create complex command aliases
ALIAS myip "curl -s https://ipinfo.io/ip"
ALIAS weather "curl -s wttr.in"
```

### Advanced Alias Creation
```bash
# Create aliases with parameters
ALIAS gitlog "git log --oneline --graph --all"
ALIAS search "grep -r"

# Create system management aliases
ALIAS ports "lsof -i -P -n | grep LISTEN"
ALIAS processes "ps aux | grep"

# Create directory navigation aliases
ALIAS mydir "cd ~/my-project"
ALIAS serve "python -m http.server"
```

### Removing Aliases
```bash
# Remove aliases
ALIAS --remove ll

# Alternative syntax
ALIAS --undo gs
ALIAS -r python
```

### Configuration Management
```bash
# Update shell configurations
ALIAS --update

# Get help
ALIAS --help
```

### RUN Integration
```bash
# Get JSON output
RUN --show ALIAS myalias "echo hello"
RUN --show ALIAS --remove myalias
```

## Features

### 🔄 Multi-Shell Support
ALIAS tool automatically updates these configuration files:
- `~/.bash_profile` (Bash login shells)
- `~/.bashrc` (Bash non-login shells)
- `~/.zshrc` (Zsh shells)

### 🔒 Security & Validation
- Prohibits using "ALIAS" as an alias name
- Validates alias name format (no spaces or special characters)
- Automatically handles existing alias updates
- Creates backup files before modifications

### 📝 Smart Management
- Automatically creates missing configuration files
- Removes duplicate alias definitions
- Complete alias removal from all config files
- Updates both config files and current shell session
- Cross-shell compatibility

### 🛠️ Advanced Features
- Supports complex commands with pipes and redirections
- Handles commands with spaces and special characters
- Preserves command quoting and escaping
- Immediate activation in current session

## Configuration Files

The tool manages aliases in these files:
- `~/.bash_profile` (Bash login shells)
- `~/.bashrc` (Bash non-login shells)
- `~/.zshrc` (Zsh shells)

## Best Practices

### Alias Naming
- Use short, memorable names
- Follow shell variable naming conventions
- Avoid conflicts with existing commands
- Use descriptive names for complex operations

### Command Structure
```bash
# Good examples
ALIAS ll "ls -la"
ALIAS gp "git push"
ALIAS serve "python -m http.server 8000"

# Commands with arguments
ALIAS search "grep -r --include='*.py'"
ALIAS backup "rsync -av --progress"
```

### Maintenance
```bash
# Regular cleanup
ALIAS --remove old_alias
ALIAS --update

# Check existing aliases
alias | grep your_pattern
```

## Troubleshooting

### Common Issues
1. **Alias not working**: Run `ALIAS --update` or restart terminal
2. **Permission denied**: Check write permissions on config files
3. **Alias conflicts**: Remove conflicting aliases first
4. **Special characters**: Properly quote complex commands

### Recovery
- Backup files are created automatically (`.backup` extension)
- Use `--remove` to clean up problematic aliases
- Manual editing of config files is supported

## Notes

- Alias names cannot contain spaces or most special characters
- Alias commands with spaces must be quoted
- Changes take effect immediately in current session
- New terminal sessions automatically load aliases
- Use `--update` to refresh configuration without restarting terminal
- Existing aliases with the same name will be updated automatically
- The tool validates all inputs before making changes 