#!/bin/bash

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

WORKDIR=~/jeremie-simus/HLTEST

# needed to work:            --reloadcfg \
 
for cooling in mean; do
    if [ -d "$WORKDIR/$cooling" ]; then
        cd "$WORKDIR/$cooling" || exit 1
        echo -n "Running cooling method: $cooling ... "
        
        python -m python_magnetworkflows.cli \
            --mdata '{"test":{"value":31000,"type":"helix","filter":"","flow":"../HLtest-flow_params.json"}}' \
            HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg \
            --cooling "$cooling" \
	    --eps "1.e-7" \
            --no-update-cooling \
            --debug > "$cooling-noreloadcfg.log" 2>&1
        
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

