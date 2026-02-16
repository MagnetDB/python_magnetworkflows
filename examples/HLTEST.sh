for cooling in ['mean', 'grad', 'meanH', 'gradH', 'gradHZ' ]; do
    cd $cooling; 
    python -m python_magnetworkflows.cli \
	--wd ~/jeremie-simus/HLTEST \
	--mdata '{"Toretest":{"value":31000,"type":"bitter","filter":"","flow":"../HLtest-flow_params.json"}}' \
	HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg \
	--cooling $cooling \
	--eps "1.e-5" \
	--debug > log 2>&1
done
