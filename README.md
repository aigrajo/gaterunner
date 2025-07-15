# Gaterunner

**Gaterunner** is an automated web saving tool that captures complete webpages using Playwright. Designed specifically to bypass malicious TDS gating to follow attack chains and capture its resources in the process.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```

## Usage

Gaterunner allows obfuscated URLs. Running this command will save data to `./data/default/saved_example.com`
```bash
python main.py hxxps[:]//example[.]com
```
To run Gaterunner on a list of urls, run:
```bash
python main.py urls.txt
```

The `--workers N` flag runs `N` instances of **Gaterunner** in parallel. Since website behavior tends to vary widely, it's best to allocate workers conservatively. A good rule of thumb is 1 worker per 1gb of RAM. Debug statements are represented differently in parallel mode:
```bash
python main.py urls.txt --workers 3
[----------------------------------------] 00% | 11:03 (0/100)
[W-1] http://website1.com
[W-2] http://website2.com
[W-3] http://website3.com
```

**Gaterunner**'s default engine dynamically spoofs a large list of fingerprintable values using a user agent string as a seed. If you pass `"OS;;Engine"`, **Gaterunner** will randomly select a user agent string that matches the criteria. You can also pass a specific user agent string
```bash
python main.py https://example.com --ua "Windows;;Chrome"
python main.py https://example.com --ua-full "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
```



2 more engines are integrated into **Gaterunner**.  `--engine camoufox` ([Camoufox](https://github.com/daijro/camoufox)) is a stealth browser forked from Firefox that is undetectable by fingerprinting and bot detection. It randomizes values like **Gaterunner**'s base engine. But many malicious sites tend to behave differently than they would on a chromium browser. `--engine patchright`([Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) is a stealth-focused fork of Playwright. It does not offer the same value randomization as the other 2 engine choices. 
