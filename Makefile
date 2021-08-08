run:
	@for i in examples/*; do echo "======== $$i ========"; cd $$i; ./run.sh; cd - > /dev/null; done

clean:
	@find examples -maxdepth 2 \( -name model_\* -o -name MC_summary_\* \) -exec rm -rv '{}' +
