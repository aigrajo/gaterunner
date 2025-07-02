# Gatekey

**Gatekey** is an automated web saving tool that captures complete webpages using Playwright. Designed specifically to bypass malicious TDS gating to follow attack chains and capture its resources in the process.

## Setup

Install dependencies:

```bash

pip install -r requirements.txt
playwright install
```

## Usage

Gatekey allows obfuscated URLs. Running this command will save data to `./data/saved_example.com`
```bash
python main.py hxxps[:]//example[.]com
```
To run Gatekey on a list of urls, run:
```bash
python main.py urls.txt
```



