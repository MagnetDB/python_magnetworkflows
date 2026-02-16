#!/bin/bash

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

for cooling in mean grad meanH gradH gradHZ; do
    if [ -d "$cooling" ]; then
        cd "$cooling" || exit 1
        echo -n "Running cooling method: $cooling ... "
        
        python -m python_magnetworkflows.cli \
            --wd ~/jeremie-simus/HLTEST \
            --mdata '{"test":{"value":31000,"type":"helices","filter":"","flow":"../HLtest-flow_params.json"}}' \
            HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg \
            --cooling "$cooling" \
            --eps "1.e-5" \
            --debug > "$cooling.log" 2>&1
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}FAILED${NC}"
        fi
        
        cd ..
    else
        echo "Warning: Directory $cooling not found, skipping..."
    fi
done

