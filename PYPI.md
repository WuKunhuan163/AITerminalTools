# PYPI - Python Package Index API Tool

A comprehensive command-line tool for interacting with the PyPI API to retrieve package information, dependencies, sizes, and metadata.

## Features

- **Package Information**: Get comprehensive package details from PyPI
- **Dependency Analysis**: Retrieve direct dependencies of any package
- **Size Information**: Get package sizes in human-readable format
- **Batch Operations**: Process multiple packages in parallel
- **JSON Output**: Machine-readable output for integration
- **Error Handling**: Robust error handling with timeout and retry logic
- **Performance**: Parallel API calls for high-performance operations

## Installation

The tool is automatically available in your `~/.local/bin` directory. Ensure this directory is in your PATH.

## Usage

```bash
PYPI <command> [package] [options]
```

### Commands

#### `info` - Get Package Information
```bash
PYPI info requests
PYPI info numpy --json
```

#### `deps` - Get Package Dependencies
```bash
PYPI deps tensorflow
PYPI deps pandas --json
```

#### `size` - Get Package Size
```bash
PYPI size matplotlib
PYPI size scipy --json
```

#### `metadata` - Get Comprehensive Package Metadata
```bash
PYPI metadata django
PYPI metadata flask --json
```

#### `batch` - Process Multiple Packages
```bash
PYPI batch --packages requests numpy pandas matplotlib
PYPI batch --packages tensorflow pytorch --json
```

#### `test` - Test API Connection
```bash
PYPI test
```

### Options

- `--json`: Output results in JSON format
- `--timeout <seconds>`: Set request timeout (default: 10)
- `--workers <number>`: Set maximum parallel workers (default: 40)
- `--packages <pkg1> <pkg2> ...`: Specify multiple packages for batch operations

## Examples

### Basic Package Information
```bash
$ PYPI info requests
Name: requests
Version: 2.31.0
Summary: Python HTTP for Humans.
Author: Kenneth Reitz
License: Apache 2.0
```

### Get Dependencies
```bash
$ PYPI deps tensorflow
Dependencies for tensorflow:
  - numpy
  - protobuf
  - setuptools
  - grpcio
  - tensorboard
  - keras
```

### Get Package Size
```bash
$ PYPI size numpy
Size of numpy: 20.3MB (21299200 bytes)
```

### Batch Processing
```bash
$ PYPI batch --packages requests numpy pandas
Processing 3 packages...
requests: 7 deps, 0.5MB
numpy: 0 deps, 20.3MB
pandas: 15 deps, 45.2MB
```

### JSON Output
```bash
$ PYPI metadata requests --json
{
  "name": "requests",
  "version": "2.31.0",
  "summary": "Python HTTP for Humans.",
  "size": 524288,
  "dependencies": [
    "urllib3",
    "certifi",
    "charset-normalizer",
    "idna"
  ],
  "author": "Kenneth Reitz",
  "license": "Apache 2.0"
}
```

## Integration with Other Tools

### Use with GDS (Google Drive Shell)
The PYPI tool is integrated with GDS for dependency analysis:
```bash
GDS pip --show-deps tensorflow --depth=2
```

### Use in Scripts
```python
import subprocess
import json

# Get package metadata
result = subprocess.run(['PYPI', 'metadata', 'requests', '--json'], 
                       capture_output=True, text=True)
data = json.loads(result.stdout)
print(f"Package {data['name']} has {len(data['dependencies'])} dependencies")
```

## API Reference

The tool provides a Python API through the `PyPIClient` class:

```python
from PYPI import PyPIClient

client = PyPIClient()

# Get package info
info = client.get_package_info('requests')

# Get dependencies
deps = client.get_package_dependencies('numpy')

# Get package size
size = client.get_package_size('pandas')

# Batch operations
results = client.batch_get_dependencies_with_sizes(['requests', 'numpy'])
```

## Performance

- **Parallel Processing**: Up to 40 concurrent API requests
- **Rate Limiting**: Built-in rate limiting to respect PyPI limits
- **Caching**: Session-based connection pooling for efficiency
- **Timeout Handling**: Configurable timeouts for reliable operation

## Error Handling

The tool handles various error conditions gracefully:

- **Package Not Found**: Returns appropriate error messages
- **Network Issues**: Implements retry logic and timeout handling
- **API Rate Limits**: Respects PyPI rate limits and provides feedback
- **Invalid Responses**: Validates API responses and handles malformed data

## Troubleshooting

### Common Issues

1. **Network Timeouts**: Increase timeout with `--timeout 30`
2. **Rate Limiting**: Reduce workers with `--workers 10`
3. **Package Not Found**: Verify package name spelling

### Debug Mode
```bash
PYPI test  # Test basic functionality and connection
```

## Contributing

This tool is part of the larger bin tools ecosystem. For contributions or bug reports, please ensure compatibility with the existing tool infrastructure.

## See Also

- **NETWORK**: Network testing and performance tools
- **GOOGLE_DRIVE**: Google Drive Shell with pip integration
- **OPENROUTER**: AI model API tools

## Version History

- **v1.0**: Initial release with basic PyPI API functionality
- **v1.1**: Added batch processing and parallel operations
- **v1.2**: Enhanced error handling and JSON output
- **v1.3**: Integrated with GDS dependency analysis
