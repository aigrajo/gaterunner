# Gaterunner

A sophisticated browser fingerprinting evasion tool that captures complete webpages using Playwright. Designed specifically to bypass malicious TDS gating, follow attack chains, and capture resources while evading detection.

## Features

- **Multi-Engine Support**: Automatically selects between Playwright, CamouFox, and Patchright
- **Advanced Fingerprinting Evasion**: Comprehensive spoofing of user agents, geolocation, timezones, WebGL, fonts, and more
- **Parallel Processing**: Multi-worker support for batch URL processing
- **Complete Page Capture**: Saves HTML, resources, and tracks redirects
- **Proxy Support**: SOCKS5 and HTTP proxy integration
- **Headless/Headful Modes**: Invisible processing or visible browser windows

## Installation

```bash
git clone https://github.com/aigrajo/gaterunner.git
cd gaterunner
pip install -e .
playwright install
```

## Quick Start

### Single URL
```bash
# Basic usage
python -m gaterunner https://example.com

# With spoofing options
python -m gaterunner --country US --lang en-US https://example.com
```

### Multiple URLs
```bash
# Serial processing
python -m gaterunner urls.txt

# Parallel processing with 4 workers
python -m gaterunner --workers 4 urls.txt
```

### Programmatic Usage
```python
from gaterunner import Config, save_page
import asyncio

async def main():
    config = Config(
        engine="auto",
        timeout_sec=30,
        verbose=True
    )
    
    await save_page(
        url="https://example.com",
        output_dir="./output",
        config=config
    )

asyncio.run(main())
```

## Configuration

### Command Line Options

| Option | Description |
|--------|-------------|
| `--country CODE` | ISO country code for geolocation spoofing (e.g., `US`, `DE`) |
| `--ua TEMPLATE` | User agent template (e.g., `Windows;;Chrome`) |
| `--ua-full UA` | Literal user agent string |
| `--lang LANG` | Accept-Language header (e.g., `en-US`, `fr-FR`) |
| `--proxy URL` | Proxy server (`socks5://host:port` or `http://host:port`) |
| `--engine ENGINE` | Browser engine: `auto`, `playwright`, `camoufox`, `patchright` |
| `--headful` | Show browser window instead of headless mode |
| `--timeout SEC` | Per-page timeout in seconds (default: 30) |
| `--workers N` | Number of parallel workers (default: 1) |
| `--verbose` | Enable debug output |
| `--output-dir DIR` | Output directory (default: `./data`) |

### Configuration Examples

```bash
# Spoof US location with Chrome on Windows
python -m gaterunner --country US --ua "Windows;;Chrome" https://example.com

# Use Tor proxy with French locale
python -m gaterunner --proxy socks5://127.0.0.1:9050 --lang fr-FR https://example.com

# Headful mode with verbose logging
python -m gaterunner --headful --verbose --timeout 60 https://example.com
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install test dependencies only
pip install -e ".[test]"
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=gaterunner

# Run specific test categories
python -m pytest -m unit
python -m pytest tests/test_unit/
```

### Code Quality

```bash
# Format code
black gaterunner/ tests/

# Type checking
mypy gaterunner/

# Linting
isort gaterunner/ tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
