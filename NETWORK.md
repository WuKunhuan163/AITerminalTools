# NETWORK - Network Performance and Testing Tool

A comprehensive command-line tool for network performance testing, latency measurement, and connectivity analysis. Designed to support high-performance network operations and batch testing scenarios.

## Features

- **Speed Testing**: Download and upload speed measurements
- **Latency Testing**: Ping and response time measurements  
- **Batch Testing**: Test multiple endpoints in parallel
- **Rate Limiting**: Configurable request rates for API testing
- **JSON Output**: Machine-readable results for integration
- **Performance Analysis**: Statistical analysis of network metrics
- **Endpoint Validation**: Connectivity and response validation

## Installation

The tool is automatically available in your `~/.local/bin` directory. Ensure this directory is in your PATH.

## Usage

```bash
NETWORK <command> [options]
```

### Commands

#### `test` - Comprehensive Network Test
```bash
NETWORK test
NETWORK test --endpoints google.com github.com
NETWORK test --json
```

#### `speed` - Speed Testing
```bash
NETWORK speed
NETWORK speed --endpoint https://httpbin.org/
NETWORK speed --download --upload
```

#### `ping` - Latency Testing
```bash
NETWORK ping google.com
NETWORK ping --count 10 --timeout 5 8.8.8.8
```

#### `batch` - Batch Testing
```bash
NETWORK batch --endpoints google.com github.com stackoverflow.com
NETWORK batch --rate 10 --endpoints api1.com api2.com api3.com
```

#### `rate` - Rate Limit Testing
```bash
NETWORK rate --url https://api.example.com --rate 40
NETWORK rate --url https://pypi.org/pypi/requests/json --rate 10 --duration 60
```

### Options

- `--json`: Output results in JSON format
- `--endpoints <url1> <url2> ...`: Specify multiple endpoints
- `--rate <number>`: Requests per second for rate testing
- `--timeout <seconds>`: Request timeout (default: 10)
- `--count <number>`: Number of tests to perform
- `--duration <seconds>`: Test duration for rate testing
- `--download`: Include download speed test
- `--upload`: Include upload speed test
- `--parallel <number>`: Number of parallel connections

## Examples

### Basic Network Test
```bash
$ NETWORK test
Network Performance Test Results:
================================
Endpoint: google.com
  ✅ Connectivity: OK
  ⏱️  Latency: 15.3ms
  📊 Response: 200 OK
  
Endpoint: github.com  
  ✅ Connectivity: OK
  ⏱️  Latency: 42.7ms
  📊 Response: 200 OK

Overall Status: ✅ All endpoints reachable
Average Latency: 29.0ms
```

### Speed Testing
```bash
$ NETWORK speed --download --upload
Speed Test Results:
==================
Download Speed: 85.3 Mbps (10.7 MB/s)
Upload Speed: 23.1 Mbps (2.9 MB/s)
Latency: 12.5ms
Test Server: speedtest.net
```

### Batch Endpoint Testing
```bash
$ NETWORK batch --endpoints google.com github.com stackoverflow.com
Batch Test Results (3 endpoints):
=================================
google.com: ✅ 15.3ms (200 OK)
github.com: ✅ 42.7ms (200 OK)  
stackoverflow.com: ✅ 28.1ms (200 OK)

Summary:
- Success Rate: 100% (3/3)
- Average Latency: 28.7ms
- Total Time: 1.2s
```

### Rate Limit Testing
```bash
$ NETWORK rate --url https://api.example.com --rate 40 --duration 30
Rate Limit Test Results:
========================
Target Rate: 40 req/s
Duration: 30s
Total Requests: 1,200
Successful: 1,180 (98.3%)
Failed: 20 (1.7%)
Average Response Time: 125ms
Rate Achieved: 39.3 req/s

Status: ✅ API can handle 40 req/s with 98.3% success rate
```

### JSON Output
```bash
$ NETWORK test --json
{
  "timestamp": "2024-08-22T15:30:45Z",
  "test_type": "connectivity",
  "results": [
    {
      "endpoint": "google.com",
      "status": "success",
      "latency_ms": 15.3,
      "response_code": 200,
      "response_time_ms": 156
    },
    {
      "endpoint": "github.com", 
      "status": "success",
      "latency_ms": 42.7,
      "response_code": 200,
      "response_time_ms": 234
    }
  ],
  "summary": {
    "total_endpoints": 2,
    "successful": 2,
    "failed": 0,
    "success_rate": 100.0,
    "average_latency_ms": 29.0
  }
}
```

## Integration with Other Tools

### Use with GDS (Google Drive Shell)
The NETWORK tool is integrated with GDS for network-aware operations:
```bash
GDS pip install --batch tensorflow  # Uses network testing for optimal performance
```

### Use with PYPI Tool
Combined network and API testing:
```bash
NETWORK rate --url https://pypi.org/pypi/requests/json --rate 40
PYPI test  # Validate PyPI connectivity
```

### Use in Scripts
```python
import subprocess
import json

# Test network performance
result = subprocess.run(['NETWORK', 'test', '--json'], 
                       capture_output=True, text=True)
data = json.loads(result.stdout)
print(f"Average latency: {data['summary']['average_latency_ms']}ms")
```

## Performance Metrics

The tool provides comprehensive performance metrics:

### Latency Metrics
- **RTT (Round Trip Time)**: Complete request-response cycle
- **DNS Resolution Time**: Domain name lookup duration
- **Connection Time**: TCP connection establishment
- **First Byte Time**: Time to first response byte

### Throughput Metrics
- **Download Speed**: Data download rate (Mbps/MB/s)
- **Upload Speed**: Data upload rate (Mbps/MB/s)
- **Request Rate**: Requests per second capability
- **Concurrent Connections**: Parallel connection handling

### Reliability Metrics
- **Success Rate**: Percentage of successful requests
- **Error Rate**: Percentage of failed requests
- **Timeout Rate**: Percentage of timed-out requests
- **Retry Success**: Success rate after retries

## Advanced Features

### Parallel Testing
```bash
NETWORK batch --endpoints api1.com api2.com api3.com --parallel 10
```

### Custom Headers and Authentication
```bash
NETWORK test --endpoint https://api.example.com --header "Authorization: Bearer token"
```

### Continuous Monitoring
```bash
NETWORK ping google.com --count 100 --interval 1  # Monitor for 100 seconds
```

### Network Diagnostics
```bash
NETWORK diagnose --endpoint problematic-api.com  # Detailed troubleshooting
```

## Configuration

### Environment Variables
- `NETWORK_TIMEOUT`: Default timeout in seconds
- `NETWORK_RATE_LIMIT`: Default rate limit for batch operations
- `NETWORK_USER_AGENT`: Custom user agent string

### Configuration File
Create `~/.network.config` for persistent settings:
```json
{
  "default_timeout": 10,
  "default_rate": 10,
  "preferred_endpoints": ["google.com", "github.com"],
  "user_agent": "NetworkTool/1.0"
}
```

## Error Handling

The tool handles various network conditions gracefully:

- **Connection Timeouts**: Configurable timeout handling
- **DNS Resolution Failures**: Fallback DNS servers
- **Rate Limiting**: Automatic backoff and retry
- **SSL/TLS Issues**: Certificate validation and bypass options

## Troubleshooting

### Common Issues

1. **High Latency**: Check network congestion and routing
2. **Connection Failures**: Verify firewall and proxy settings
3. **Rate Limit Errors**: Reduce request rate or increase timeout
4. **SSL Errors**: Update certificates or use `--insecure` flag

### Debug Mode
```bash
NETWORK test --debug  # Verbose output for troubleshooting
```

## Use Cases

### Development and Testing
- API endpoint validation before deployment
- Load testing for web services
- Network performance benchmarking
- CI/CD pipeline network checks

### System Administration
- Network infrastructure monitoring
- Bandwidth utilization analysis
- Service availability checking
- Performance regression testing

### Research and Analysis
- Network latency studies
- Geographic performance analysis
- ISP performance comparison
- CDN effectiveness measurement

## Performance Optimization

The tool is optimized for:

- **Low Overhead**: Minimal resource usage during testing
- **High Concurrency**: Efficient parallel request handling
- **Memory Efficiency**: Streaming data processing
- **CPU Optimization**: Asynchronous I/O operations

## Contributing

This tool is part of the larger bin tools ecosystem. For contributions or bug reports, please ensure compatibility with the existing tool infrastructure.

## See Also

- **PYPI**: Python Package Index API tools with network integration
- **GOOGLE_DRIVE**: Google Drive Shell with network-aware operations
- **OPENROUTER**: AI model API tools with rate limiting

## Version History

- **v1.0**: Initial release with basic network testing
- **v1.1**: Added speed testing and batch operations
- **v1.2**: Enhanced rate limiting and parallel testing
- **v1.3**: Integrated with GDS and PYPI tools
- **v1.4**: Added comprehensive performance metrics
