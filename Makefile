run:
	for i in examples/*; do echo $$i; cd $$i; ./run.sh; cd - > /dev/null; done

clean:
	find examples -type d -name model\* -exec rm -rv '{}' +
