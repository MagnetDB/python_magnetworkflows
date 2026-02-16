python -m python_magnetworkflows.commissioning \
  --wd ~/jeremie-simus/M9Bitters_18MW/ \
  --mdata '{"HLtest":{"value":12000,"steplist":[10000,11000,12000],"type":"bitter", "filter":"", "relax":0,"flow":"M9Bitters_18MW-flow_params.json"}}' \
  gradHZ/M9Bitters_18MW-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg \
  --cooling gradHZ \
  --debug
