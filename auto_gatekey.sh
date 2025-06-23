#!/bin/bash

input="live_urls.txt" # List of urls

while read -r raw_url; do
    # Deobfuscate URL: convert [.] to . and [:] to :
    url=$(echo "$raw_url" | sed 's/\[\.\]/./g; s/\[\:\]/:/g')

    echo "[*] Running gatekey for: $url"

    # Config
    python main.py "$url" \
        --country US \
        --ua "Windows;;Chrome" \
        --lang "en-US"

    sleep 1
done < "$input"

