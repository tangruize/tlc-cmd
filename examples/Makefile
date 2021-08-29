run:
	@for i in *; do if [ ! -d $$i ]; then continue; fi; echo "======== $$i ========"; cd $$i; ./run.sh; cd - > /dev/null; done

clean:
	@find -maxdepth 2 \( -name model_\* -o -name MC_summary_\* \) -exec rm -rv '{}' +
