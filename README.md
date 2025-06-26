# Gatekey

**Gatekey** is an automated web saving tool that captures complete webpages using Playwright. Designed specifically to bypass malicious TDS gating to follow attack chains and capture its resources in the process.

## Setup

Install dependencies:

```bash

pip install -r requirements.txt
playwright install
```

## Usage

Running this command will save data to `./data/saved_\<domain\>`
```bash
python main.py https://example.com
```
To run **Gatekey** on a list of urls, run:
```bash
./auto_gatekey.sh urls.txt
```



