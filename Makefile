# Shell variables which may customize behaviour of this Makefiles:
# 
# * ADDITIONAL_PEX_OPTIONS
# 	additional flags which can be passed to pex tool to be used while building distribution files
#
# * OPTIONAL_FEATURES
# 	space seperated list of optional features to be included in the build of pex files;
# 	optional features list:
# 	* kafka_storage


# For cache-dir $PWD is required, becuase pex 2.0.3 have some issues with relative directories.
PEX_OPTIONS = -v -R component-licenses --cache-dir=${PWD}/.pex-build $(ADDITIONAL_PEX_OPTIONS)
OPTIONAL_MODULES =
ifeq ($(OPTIONAL_FEATURES),kafka_storage) 
	OPTIONAL_MODULES = './confluent-kafka-python'
endif


# Do not really on artifacts created by make for all targets.
.PHONY: all venv flake8 bandit unit wca_package bandit_pex wrapper_package clean tests check dist

all: venv check dist generate_docs

venv:
	@echo Preparing virtual enviornment using pipenv.
	pipenv --version
	env PIPENV_QUIET=true pipenv install --dev

flake8:
	@echo Checking code quality.
	pipenv run flake8 wca tests examples

bandit:
	@echo Checking code with bandit.
	pipenv run bandit -r wca -s B101 -f html -o wca-bandit.html

bandit_pex:
	@echo Checking pex with bandit.
	unzip dist/wca.pex -d dist/wca-pex-bandit
	pipenv run bandit -r dist/wca-pex-bandit/.deps -s B101 -f html -o wca-pex-bandit.html || true
	rm -rf dist/wca-pex-bandit

check_outdated:
	@echo Checking out of date dependencies.
	pipenv run pip list --outdated

unit:
	@echo Running unit tests.
	pipenv run env PYTHONPATH=.:examples/workloads/wrapper pytest --cov-report term-missing --cov=wca tests --ignore=tests/e2e/test_wca_metrics.py

unit_no_ssl:
	@echo Running unit tests.
	pipenv run env PYTHONPATH=.:examples/workloads/wrapper pytest --cov-report term-missing --cov=wca tests --ignore=tests/e2e/test_wca_metrics.py --ignore=tests/ssl/test_ssl.py

junit:
	@echo Running unit tests.	
	pipenv run env PYTHONPATH=.:examples/workloads/wrapper pytest --cov-report term-missing --cov=wca tests --junitxml=unit_results.xml -vvv -s --ignore=tests/e2e/test_wca_metrics.py

wca_package_in_docker: DOCKER_OPTIONS ?=
wca_package_in_docker: WCA_IMAGE ?= wca
wca_package_in_docker: WCA_TAG ?= $(shell git rev-parse HEAD)
wca_package_in_docker:
	@echo Building wca pex file inside docker and copying to ./dist/wca.pex
	# target: standalone
	sudo docker build --build-arg MAKE_WCA_PACKAGE=yes $(DOCKER_OPTIONS) --network host --target standalone -f Dockerfile -t $(WCA_IMAGE):$(WCA_TAG) .
	# Extract pex to dist folder
	rm -rf .cidfile && sudo docker create --cidfile=.cidfile $(WCA_IMAGE):$(WCA_TAG)
	CID=$$(cat .cidfile); \
	mkdir -p dist; \
	sudo docker cp $$CID:/usr/bin/wca.pex dist/ && \
	sudo docker rm $$CID && \
	sudo chown -R $$USER:$$USER dist/wca.pex && sudo rm .cidfile
	@echo WCA image name is: $(WCA_IMAGE):$(WCA_TAG)
	@echo WCA pex file: dist/wca.pex

wca_package_in_docker_with_kafka: WCA_IMAGE ?= wca
wca_package_in_docker_with_kafka: WCA_TAG ?= $(shell git rev-parse HEAD)
wca_package_in_docker_with_kafka:
	@echo "Building wca pex (version with Kafka) file inside docker and copying to ./dist/wca.pex"
	sudo docker build --network host -f Dockerfile.kafka -t $(WCA_IMAGE):$(WCA_TAG) .
	rm -rf .cidfile && sudo docker create --cidfile=.cidfile $(WCA_IMAGE):$(WCA_TAG)
	CID=$$(cat .cidfile); \
	mkdir -p dist; \
	sudo docker cp $$CID:/wca/dist/wca.pex dist/ && \
	sudo docker rm $$CID && \
	sudo chown -R $$USER:$$USER dist/wca.pex && sudo rm .cidfile
	@echo WCA image name is: $(WCA_IMAGE):$(WCA_TAG)
	@echo WCA pex file: dist/wca.pex
	# ---
	@echo "Please follow docs/kafka_storage.rst to be able to use created wca.pex"

wca_package:
	@echo Building wca pex file.
	-rm .pex-build/wca*
	-rm -rf .pex-build
	-rm dist/wca.pex
	-rm -rf wca.egg-info
	pipenv run env PYTHONPATH=. pex . $(OPTIONAL_MODULES) $(PEX_OPTIONS) -o dist/wca.pex -m wca.main:main
	./dist/wca.pex --version

wrapper_package_in_docker_with_kafka: WCA_IMAGE ?= wca
wrapper_package_in_docker_with_kafka: WCA_TAG ?= $(shell git rev-parse HEAD)
wrapper_package_in_docker_with_kafka:
	@echo "Building wrappers pex (versions with Kafka) file inside docker and copying to ./dist/"
	sudo docker build --build-arg MAKE_WRAPPER_PACKAGE=yes --network host -f Dockerfile.kafka -t $(WCA_IMAGE):$(WCA_TAG) .
	# Extract pex to dist folder
	rm -rf .cidfile && sudo docker create --cidfile=.cidfile $(WCA_IMAGE):$(WCA_TAG)
	CID=$$(cat .cidfile); \
	mkdir -p dist; \
	sudo docker cp $$CID:/wca/dist/. dist/ && \
	sudo docker rm $$CID && \
	sudo chown -R $$USER:$$USER dist/*.pex && sudo rm .cidfile
	@echo WCA image name is: $(WCA_IMAGE):$(WCA_TAG)
	@echo WCA pex file: dist/wca.pex
	# ---
	@echo "Please follow docs/kafka_storage.rst to be able to use created pex files."

wrapper_package:
	@echo "Building wrappers pex files."
	-sh -c 'rm -f .pex-build/*wrapper.pex'
	-rm -rf .pex-build
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/wrapper.pex -m wrapper.wrapper_main
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/example_workload_wrapper.pex -m wrapper.parser_example_workload
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/specjbb_wrapper.pex -m wrapper.parser_specjbb
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/ycsb_wrapper.pex -m wrapper.parser_ycsb
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/rpc_perf_wrapper.pex -m wrapper.parser_rpc_perf
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/mutilate_wrapper.pex -m wrapper.parser_mutilate
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/cassandra_stress_wrapper.pex -m wrapper.parser_cassandra_stress
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/stress_ng_wrapper.pex -m wrapper.parser_stress_ng
	pipenv run pex . $(OPTIONAL_MODULES) -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/memtier_benchmark_wrapper.pex -m wrapper.parser_memtier
	./dist/wrapper.pex --help >/dev/null

#-----------------------------------------------------------------------------------------------
# Private or deprecated

# Do not build pex file, just copy python source and install dependencies into docker container.
_wca_docker_devel: WCA_IMAGE ?= wca
_wca_docker_devel: WCA_TAG ?= devel
_wca_docker_devel:
	@echo "Preparing development WCA container (only source code without pex)"
	sudo docker build --network host --target devel -f Dockerfile -t $(WCA_IMAGE):$(WCA_TAG) .
	@echo WCA image name is: $(WCA_IMAGE):$(WCA_TAG)
	@echo Push: sudo docker push $(WCA_IMAGE):$(WCA_TAG)
	@echo Run: sudo docker run --privileged -ti --rm $(WCA_IMAGE):$(WCA_TAG) -0 -c /wca/configs/extra/static_measurements.yaml


ENV_UNSAFE = env PYTHONPATH=. INCLUDE_UNSAFE_CONFLUENT_KAFKA_WHEEL=yes
_unsafe_wrapper_package:
	@echo Building wrappers pex files. Unsafe method, do not use in production environment.
	-sh -c 'rm -f .pex-build/*wrapper.pex'
	-rm -rf .pex-build
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/wrapper.pex -m wrapper.wrapper_main
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/example_workload_wrapper.pex -m wrapper.parser_example_workload
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/specjbb_wrapper.pex -m wrapper.parser_specjbb
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/ycsb_wrapper.pex -m wrapper.parser_ycsb
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/rpc_perf_wrapper.pex -m wrapper.parser_rpc_perf
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/mutilate_wrapper.pex -m wrapper.parser_mutilate
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/cassandra_stress_wrapper.pex -m wrapper.parser_cassandra_stress
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/stress_ng_wrapper.pex -m wrapper.parser_stress_ng
	pipenv run $(ENV_UNSAFE) pex . -D examples/workloads/wrapper $(PEX_OPTIONS) -o dist/memtier_benchmark_wrapper.pex -m wrapper.parser_memtier
	./dist/wrapper.pex --help >/dev/null
#-----------------------------------------------------------------------------------------------

check: flake8 unit bandit check_outdated

dist: wca_package wrapper_package

clean:
	@echo Cleaning.
	rm -rf .pex-build
	rm -rf wca.egg-info
	rm -rf dist
	pipenv --rm

tester:
	@echo Integration tests.
	sh -c 'sudo chmod 700 $$(pwd)/tests/tester/configs/tester_example.yaml'
	sh -c 'sudo PEX_INHERIT_PATH=fallback PYTHONPATH="$$(pwd):$$(pwd)/tests/tester" dist/wca.pex -c $$(pwd)/tests/tester/configs/tester_example.yaml -r tester:IntegrationTester -r tester:MetricCheck -r tester:FileCheck --log=debug --root'

generate_docs:
	@echo Generate documentation.
	pipenv run env PYTHONPATH=. python util/docs.py
