# Do not really on artifacts created by make for all targets.
.PHONY: all venv flake8 unit owca_package wrapper_package clean tests check dist

all: venv check dist

venv:
	@echo Preparing virtual enviornment using pipenv.
	pipenv --version
	env PIPENV_QUIET=true pipenv install --dev

flake8: 
	@echo Checking code quality.
	pipenv run flake8 owca tests example workloads

unit: 
	@echo Running unit tests.
	pipenv run env PYTHONPATH=. pytest --cov-report term-missing --cov=owca tests

junit: 
	@echo Running unit tests.
	pipenv run env PYTHONPATH=. pytest --cov-report term-missing --cov=owca tests --junitxml=unit_results.xml -vvv -s

owca_package: 
	@echo Building owca pex file.
	-rm .pex-build/owca*
	-rm dist/owca.pex
	-rm -rf owca.egg-info
	pipenv run env PYTHONPATH=. pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/owca.pex -m owca.main:main
	./dist/owca.pex --version

wrapper_package: 
	@echo Building wrappers pex files.
	-sh -c 'rm -f .pex-build/*wrapper.pex'
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/wrapper.pex -m owca.wrapper.wrapper_main
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/example_workload_wrapper.pex -m owca.wrapper.parser_example_workload
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/specjbb_wrapper.pex -m owca.wrapper.parser_specjbb
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/ycsb_wrapper.pex -m owca.wrapper.parser_ycsb
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/rpc_perf_wrapper.pex -m owca.wrapper.parser_rpc_perf
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/tensorflow_benchmark_training_wrapper.pex -m owca.wrapper.parser_tensorflow_benchmark_training
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/tensorflow_benchmark_prediction_wrapper.pex -m owca.wrapper.parser_tensorflow_benchmark_prediction
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/mutilate_wrapper.pex -m owca.wrapper.parser_mutilate
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/cassandra_stress_wrapper.pex -m owca.wrapper.parser_cassandra_stress
	pipenv run pex . -v -R component-licenses --cache-dir=.pex-build $(PEX_OPTIONS) -o dist/stress_ng_wrapper.pex -m owca.wrapper.parser_stress_ng
	./dist/wrapper.pex --help >/dev/null

check: flake8 unit

dist: owca_package wrapper_package

clean:
	@echo Cleaning.
	rm -rf .pex-build
	rm -rf owca.egg-info
	rm -rf dist
	pipenv --rm
