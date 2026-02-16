python -m python_magnetworkflows.cli \
	--wd ~/jeremie-simus/Tore_thmagel \
  --mdata '{"Toretest":{"value":31000,"type":"bitter","filter":"","flow":"flow_params.json"}}' \
  Toretest-cfpdes-thmagel-nonlinear-Axi-sim.cfg \
  --cooling mean \
  --eps "1.e-5" \
  --debug
