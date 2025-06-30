#!/bin/bash

input=$1 # List of urls

total=$(wc -l < "$input")
count=0
SECONDS=0

while read -r raw_url; do
    ((count++))
    # Deobfuscate URL: convert [.] to . and [:] to :
    url=$(echo "$raw_url" | sed 's/\[\.\]/./g; s/\[\:\]/:/g')

    percent=$(( 100 * count / total ))
    elapsed=$(printf "%02dm:%02ds" $((SECONDS/60)) $((SECONDS%60)))

    echo "[*] Running gatekey for: $url"
    echo "[*] Progress: $count/$total ($percent%) | Elapsed: $elapsed"

    # Config
     python main.py "$url" \
        --country US \
        --ua "Windows;;Chrome" \
        --lang "en-US" # > /dev/null 2>&1


done < "$input"

elapsed=$(printf "%02dm:%02ds" $((SECONDS/60)) $((SECONDS%60)))
echo "[*] Done. Total time: $elapsed"