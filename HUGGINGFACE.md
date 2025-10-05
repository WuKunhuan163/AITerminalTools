# HUGGINGFACE - HuggingFace Credentials Management Tool

🤗 A comprehensive tool for managing HuggingFace credentials, authentication, and model access for projects that require HuggingFace Hub integration.

## Features

- **Interactive Login**: Secure token-based authentication
- **Token Management**: Direct token setting and validation
- **Status Checking**: Verify authentication status
- **User Information**: Display current user details
- **Authentication Testing**: Verify API access and permissions
- **RUN Compatibility**: Full support for `RUN --show` JSON output
- **Auto-Installation**: Automatically installs `huggingface_hub` if needed

## Installation

The tool automatically installs the required `huggingface_hub` package when first used.

## Usage

### Basic Commands

```bash
# Check current authentication status (default)
HUGGINGFACE

# Interactive login
HUGGINGFACE --login

# Set token directly
HUGGINGFACE --token hf_xxxxxxxxxxxxxxxxxxxxxxxxx

# Check authentication status
HUGGINGFACE --status

# Show current user information
HUGGINGFACE --whoami

# Test authentication and API access
HUGGINGFACE --test

# Logout and clear credentials
HUGGINGFACE --logout

# Show help
HUGGINGFACE --help
```

### RUN Integration

Use with `RUN --show` for clean JSON output:

```bash
# Check status with JSON output
RUN --show HUGGINGFACE --status

# Test authentication with JSON output
RUN --show HUGGINGFACE --test

# Get user info with JSON output
RUN --show HUGGINGFACE --whoami
```

## Command Details

### `--login` - Interactive Login
Prompts for your HuggingFace token and saves it securely.

**Example:**
```bash
HUGGINGFACE --login
```

**Output:**
```
🤗 HuggingFace Interactive Login
Please visit https://huggingface.co/settings/tokens to get your token
You can create a new token or use an existing one.

Enter your HuggingFace token: hf_xxxxxxxxxxxxxxxxxxxxxxxxx
Successfully logged in to HuggingFace
   token_saved: Yes
   git_credential: Added
```

### `--token <token>` - Direct Token Setting
Set your HuggingFace token directly without interactive prompts.

**Example:**
```bash
HUGGINGFACE --token hf_xxxxxxxxxxxxxxxxxxxxxxxxx
```

### `--status` - Authentication Status
Check if you're currently authenticated and show token information.

**Example:**
```bash
HUGGINGFACE --status
```

**Output (Authenticated):**
```
HuggingFace authentication active
   authenticated: Yes
   username: your_username
   email: your_email@example.com
   token_file: /Users/username/.cache/huggingface/token
   token_exists: True
```

**Output (Not Authenticated):**
```
Error: Not authenticated
```

### `--whoami` - User Information
Display detailed information about the currently authenticated user.

**Example:**
```bash
HUGGINGFACE --whoami
```

**Output:**
```
Current HuggingFace user information
   username: your_username
   fullname: Your Full Name
   email: your_email@example.com
   avatar_url: https://...
   plan: free
```

### `--test` - Authentication Test
Perform comprehensive authentication testing including API access.

**Example:**
```bash
HUGGINGFACE --test
```

**Output:**
```
HuggingFace authentication test passed
   user_test: Passed
   username: your_username
   api_test: Passed
   model_access: Can access public models
   test_model: bert-base-uncased
```

### `--logout` - Logout
Remove stored credentials and logout from HuggingFace.

**Example:**
```bash
HUGGINGFACE --logout
```

**Output:**
```
Successfully logged out from HuggingFace
   token_removed: Yes
   git_credential: Removed
```

## Getting Your Token

1. Visit [HuggingFace Settings - Tokens](https://huggingface.co/settings/tokens)
2. Click "New token"
3. Choose appropriate permissions:
   - **Read**: For downloading models and datasets
   - **Write**: For uploading models and datasets
4. Copy the generated token (starts with `hf_`)
5. Use it with the tool: `HUGGINGFACE --token hf_your_token_here`

## Token Storage

- Tokens are stored in `~/.cache/huggingface/token`
- The tool also adds credentials to git credential storage
- Tokens are used by all HuggingFace libraries automatically

## JSON Output Format

When used with `RUN --show`, the tool returns structured JSON:

```json
{
  "success": true,
  "message": "HuggingFace authentication active",
  "details": {
    "authenticated": "Yes",
    "username": "your_username",
    "email": "your_email@example.com",
    "token_file": "/Users/username/.cache/huggingface/token",
    "token_exists": true
  }
}
```

## Error Handling

The tool provides clear error messages for common issues:

- **No token provided**: When login is attempted without entering a token
- **Invalid token**: When the provided token is malformed or expired
- **Network issues**: When unable to connect to HuggingFace servers
- **Permission issues**: When token lacks required permissions

## Integration with Projects

### Environment Variables

The tool respects standard HuggingFace environment variables:

- `HF_HOME`: Custom location for HuggingFace cache (default: `~/.cache/huggingface`)
- `HF_TOKEN`: Alternative way to provide token

### Python Integration

Once authenticated with this tool, all Python code using `huggingface_hub` will automatically use the stored credentials:

```python
from huggingface_hub import HfApi, hf_hub_download

# These will work automatically after authentication
api = HfApi()
user_info = api.whoami()

# Download models
model_path = hf_hub_download(repo_id="bert-base-uncased", filename="config.json")
```

### GDS Integration

Use with Google Drive Shell for remote operations:

```bash
# Check authentication status remotely
GDS python -c "
import subprocess
result = subprocess.run(['HUGGINGFACE', '--status'], capture_output=True, text=True)
print(result.stdout)
"
```

## Troubleshooting

### Common Issues

1. **"huggingface_hub not found"**
   - The tool will automatically install it
   - If installation fails, manually run: `pip install huggingface_hub`

2. **"Not authenticated" despite having token**
   - Check token validity at https://huggingface.co/settings/tokens
   - Try logging out and logging in again: `HUGGINGFACE --logout && HUGGINGFACE --login`

3. **"API access failed"**
   - Check internet connection
   - Verify token has appropriate permissions
   - Try the test command: `HUGGINGFACE --test`

4. **Permission denied errors**
   - Ensure write access to `~/.cache/huggingface/`
   - Check file permissions: `ls -la ~/.cache/huggingface/token`

### Debug Information

Use the test command for comprehensive diagnostics:

```bash
HUGGINGFACE --test
```

This will test:
- User authentication
- API connectivity
- Model access permissions
- Token validity

## Examples

### Quick Setup

```bash
# 1. Set up authentication
HUGGINGFACE --login

# 2. Verify it works
HUGGINGFACE --test

# 3. Check your info
HUGGINGFACE --whoami
```

### Automation Scripts

```bash
#!/bin/bash
# Check if authenticated before running ML pipeline
if RUN --show HUGGINGFACE --status | jq -r '.success' | grep -q true; then
    echo "HuggingFace authenticated, proceeding..."
    python train_model.py
else
    echo "Error: Not authenticated, please run: HUGGINGFACE --login"
    exit 1
fi
```

### Remote Setup via GDS

```bash
# Set up HuggingFace credentials on remote system
GDS python -c "
import subprocess
import os

# Set token via environment variable
os.environ['HF_TOKEN'] = 'hf_your_token_here'
result = subprocess.run(['HUGGINGFACE', '--token', os.environ['HF_TOKEN']])
print('Setup complete!' if result.returncode == 0 else 'Setup failed!')
"
```

## Security Notes

- Never share your HuggingFace tokens
- Use read-only tokens when possible
- Regularly rotate your tokens
- Store tokens securely using this tool rather than in code
- The tool stores tokens in the standard HuggingFace cache location

## Compatibility

- **Python**: 3.6+
- **Operating Systems**: macOS, Linux, Windows
- **HuggingFace Hub**: All versions
- **RUN Tool**: Full compatibility with `RUN --show`
- **GDS**: Compatible with Google Drive Shell operations 