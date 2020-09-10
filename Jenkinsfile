// Copyright (c) 2020 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

pipeline {
    agent any
    parameters {
      booleanParam defaultValue: true, description: 'Run all pre-checks.', name: 'PRECHECKS'
      booleanParam defaultValue: true, description: 'Build WCA image.', name: 'BUILD_WCA_IMAGE'
      booleanParam defaultValue: true, description: 'Build workload images.', name: 'BUILD_IMAGES'
      booleanParam defaultValue: true, description: 'E2E for Kubernetes as Daemonset.', name: 'E2E_K8S_DS'
      booleanParam defaultValue: true, description: 'E2E for wca-scheduler', name: 'E2E_WCA_SCHEDULER'
      string defaultValue: '300', description: 'Sleep time for E2E tests', name: 'SLEEP_TIME'
    }
    environment {
        DOCKER_REPOSITORY_URL = '100.64.176.12:80'
        CADVISOR_REVISION = 'master'
    }
    stages{
        stage("Flake8 formatting scan") {
            when {expression{return params.PRECHECKS}}
            steps {
                sh '''
                  make venv flake8
                '''
            }
        }
        stage("Run unit tests suite") {
            when {expression{return params.PRECHECKS}}
            steps {
                sh '''
                  make junit
                '''
            }
            post {
                always {
                    junit 'unit_results.xml'
                }
            }
        }
        stage("Generate documentation") {
            when {expression{return params.PRECHECKS}}
            steps {
                generate_docs()
            }
        }
        stage("Build WCA pex (in docker and images)") {
            when {expression{return params.BUILD_WCA_IMAGE}}
            steps {
                sh '''
                  echo GIT_COMMIT=${GIT_COMMIT}
                  export WCA_IMAGE=${DOCKER_REPOSITORY_URL}/wca
                  export WCA_TAG=${GIT_COMMIT}
                  make wca_package_in_docker
                  docker push $WCA_IMAGE:$WCA_TAG
                  # tag with branch name and push
                  docker tag $WCA_IMAGE:$WCA_TAG $WCA_IMAGE:${GIT_BRANCH}
                  docker push $WCA_IMAGE:${GIT_BRANCH}

                  # Just for completeness (not used later)
                  export WCA_TAG=${GIT_BRANCH}-devel
                  make _wca_docker_devel
                  docker push $WCA_IMAGE:$WCA_TAG
                  # Delete all wca images from Jenkins nodes
                  docker rmi $WCA_IMAGE:${GIT_COMMIT} $WCA_IMAGE:${GIT_BRANCH} $WCA_IMAGE:${WCA_TAG}
                '''
            }
        }
        stage("Check code with bandit") {
            when {expression{return params.PRECHECKS}}
             steps {
             sh '''
                source env/bin/activate

                echo Install bandit.
                pip install wheel==0.33.6 bandit==1.6.2;

                echo Checking code with bandit.
                bandit -r wca -x wca/scheduler/simulator_experiments -s B101 -f html -o wca-bandit.html

                echo Checking pex with bandit.
                unzip dist/wca.pex -d dist/wca-pex-bandit
                bandit -r dist/wca-pex-bandit/.deps -s B101 -f html -o wca-pex-bandit.html || true
                rm -rf dist/wca-pex-bandit

                deactivate
             '''
             archiveArtifacts(artifacts: "wca-bandit.html, wca-pex-bandit.html")
           }
        }
        stage("Building Docker images and do tests in parallel") {
            parallel {
                 stage("Using tester") {
                     when {expression{return params.PRECHECKS}}
                     steps {
                     sh '''
			         make tester
                     '''
                     }
                 }
                // cadvisor
                stage("Build and push cAdvisor Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/cadvisor:${CADVISOR_REVISION}
                    IMAGE_DIR=${WORKSPACE}/cadvisor
                    if [ -d cadvisor ]; then
                        rm -fr cadvisor
                    fi
                    mkdir cadvisor
                    pushd cadvisor
                    git init .
                    git remote add origin https://github.com/google/cadvisor.git
                    git fetch origin ${CADVISOR_REVISION} --depth=1
                    git checkout FETCH_HEAD

                    docker build -t ${IMAGE_NAME} -f ../examples/kubernetes/monitoring/cadvisor/Dockerfile.cadvisor .
                    docker push ${IMAGE_NAME}
                    popd
                    rm -fr cadvisor
                    '''
                    }
                }
                stage("Build and push wca_scheduler Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca-scheduler:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca-scheduler:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/kubernetes/wca-scheduler
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile .
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // memtier_benchmark
                stage("Build and push memtier_benchmark Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/memtier_benchmark:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/memtier_benchmark:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/memtier_benchmark
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // stress_ng
                stage("Build and push stress_ng Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/stress_ng:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/stress_ng:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/stress_ng
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // rpc_perf
                stage("Build and push rpc_perf Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/rpc_perf:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/rpc_perf:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/rpc_perf
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // Twemcache
                stage("Build and push Twemcache Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/twemcache:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/twemcache:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/twemcache
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // YCSB
                stage("Build and push YCSB Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/ycsb:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/ycsb:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/ycsb
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // Stress
                stage("Build and push Cassandra Stress Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/cassandra_stress:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/cassandra_stress:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/cassandra_stress
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    # Building Cassandra Stress Docker image take too long (30min),
                    # the commented line below is for caching purpose
                    # docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // Sysbench
                stage("Build and push Sysbench Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/sysbench:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/sysbench:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/sysbench
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // Mutilate
                stage("Build and push Mutilate Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/mutilate:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/mutilate:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/mutilate
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // HammerDB
                stage("Build and push HammerDB Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/hammerdb:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/hammerdb:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/hammerdb
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                stage("Build and push mysql_tpm_gauge Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                    sh '''
                    IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/mysql_tpm_gauge:${GIT_COMMIT}
                    BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/mysql_tpm_gauge:${GIT_BRANCH}
                    IMAGE_DIR=${WORKSPACE}/examples/workloads/mysql_tpm_gauge
                    cp -r dist ${IMAGE_DIR}
                    docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                    docker push ${IMAGE_NAME}
                    docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    docker push ${BRANCH_IMAGE_NAME}
                    docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                    '''
                    }
                }
                // SpecJBB
                stage("Build and push SpecJBB Docker image") {
                    when {expression{return params.BUILD_IMAGES}}
                    steps {
                        withCredentials([file(credentialsId: 'specjbb', variable: 'SPECJBB_TAR')]) {
                            sh '''
                            IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/specjbb:${GIT_COMMIT}
                            BRANCH_IMAGE_NAME=${DOCKER_REPOSITORY_URL}/wca/specjbb:${GIT_BRANCH}
                            IMAGE_DIR=${WORKSPACE}/examples/workloads/specjbb
                            cp ${SPECJBB_TAR} ${IMAGE_DIR}
                            tar -xC ${IMAGE_DIR} -f ${IMAGE_DIR}/specjbb.tar.bz2
                            cp -r dist ${IMAGE_DIR}
                            docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                            docker push ${IMAGE_NAME}
                            docker tag ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                            docker push ${BRANCH_IMAGE_NAME}
                            docker rmi ${IMAGE_NAME} ${BRANCH_IMAGE_NAME}
                            '''
                        }
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/examples/workloads/specjbb/specjbb.tar.bz2 ${WORKSPACE}/examples/workloads/specjbb/specjbb ${WORKSPACE}/examples/workloads/specjbb/dist
                            '''
                        }
                    }
                }
            }
            post {
                always {
                    sh '''
                    rm -f kaggle.json
                    '''
                }
            }
        }
        stage('WCA E2E tests') {
            agent { label 'Daemonset' }
            when {expression{return params.E2E_K8S_DS}}
            environment {
                BUILD_COMMIT="${GIT_COMMIT}"
                RUN_WORKLOADS_SLEEP_TIME = "${params.SLEEP_TIME}"
                PROMETHEUS='http://100.64.176.18:30900'
                KUBERNETES_HOST='100.64.176.32'
                KUBECONFIG="${HOME}/.kube/admin.conf"
                KUSTOMIZATION_MONITORING='examples/kubernetes/monitoring/'
                KUSTOMIZATION_WORKLOAD='examples/kubernetes/workloads/'
            }
            steps {
                kustomize_wca_and_workloads_check()
            }
            post {
                always {
                    print('Cleaning workloads and wca...')
                    sh "kubectl delete -k ${WORKSPACE}/${KUSTOMIZATION_WORKLOAD} --wait=false"
                    sh "kubectl delete -k ${WORKSPACE}/${KUSTOMIZATION_MONITORING} --wait=false"
                    sh "kubectl delete svc prometheus-nodeport-service --namespace prometheus"
                    junit 'unit_results.xml'
                }
            }
        }
        stage('E2E wca-scheduler') {
                when {expression{return params.E2E_WCA_SCHEDULER}}
                agent { label 'kubernetes' }
                environment {
                    PROMETHEUS='http://100.64.176.18:30900'
                    KUBERNETES_HOST='100.64.176.18'
                    PORT_WCA_SCHEDULER=32180
                    KUBECONFIG="${HOME}/.kube/admin.conf"
                    KUSTOMIZATION_MONITORING='examples/kubernetes/monitoring/'
                    KUSTOMIZATION_WORKLOAD='examples/kubernetes/workloads/'
                    WCA_SCHEDULER_PATH='examples/kubernetes/wca-scheduler/'
                }
                steps {

                    print('Set configs wca-wcheduler...')
                    sh "sed -i 's#/var/run/secrets/kubernetes.io/serviceaccount/ca.crt;#/var/run/secrets/kubernetes.io/cert/CA.crt;#g' ${WORKSPACE}/${WCA_SCHEDULER_PATH}wca-scheduler-server.conf"
                    sh "sed -i 's/node36/node18/g' ${WORKSPACE}/${WCA_SCHEDULER_PATH}wca-scheduler-deployment.yaml"
                    sh "sed -i 's/100.64.176.36/${KUBERNETES_HOST}/g' ${WORKSPACE}/${WCA_SCHEDULER_PATH}config.yaml"
                    sh "sed -i 's/master/${GIT_COMMIT}/g' ${WORKSPACE}/${WCA_SCHEDULER_PATH}kustomization.yaml"

                    sh "kubectl --namespace wca-scheduler create secret generic wca-scheduler-cert \
                        --from-file ${WORKSPACE}/tests/e2e/nginx/server.crt \
                        --from-file ${WORKSPACE}/tests/e2e/nginx/server-key.pem \
                        --from-file ${WORKSPACE}/tests/e2e/nginx/CA.crt"

                    print('Starting wca-wcheduler...')
                    sh "kubectl apply -k ${WORKSPACE}/${WCA_SCHEDULER_PATH}"

                    print('Create Service for wca-scheduler, for E2E only')
                    sh "kubectl expose deployment wca-scheduler --type=NodePort --port=30180 --name=wca-scheduler-nodeport-service --namespace wca-scheduler && \
                        kubectl patch service wca-scheduler-nodeport-service --namespace=wca-scheduler --type='json' --patch='[ \
                        {\"op\": \"replace\", \"path\": \"/spec/ports/0/nodePort\", \"value\":32180}]'"

                    wait_for_wca_wcheduler()

                    sh "make venv; source env/bin/activate && \
                        pytest ${WORKSPACE}/tests/e2e/nginx/test_wca_nginx_ssl.py::test_wca_nginx_ssl_incorrect_cert --junitxml=unit_results.xml --log-level=debug --log-cli-level=debug -v && \
                        deactivate"

                }
                post {
                    always {
                        print('Cleaning wca-scheduler...')
                        sh "kubectl delete -k ${WORKSPACE}/${WCA_SCHEDULER_PATH} --wait=false"
                        sh "kubectl delete secret  wca-scheduler-cert -n wca-scheduler"
                        sh "kubectl delete svc wca-scheduler-nodeport-service --namespace wca-scheduler"
                        print('Asserting unit tests status...')
                        junit 'unit_results.xml'
                    }
                }
            }
    }
}



/*----------------------------------------------------------------------------------------------------------*/
/* Helper function */
/*----------------------------------------------------------------------------------------------------------*/

def kustomize_wca_and_workloads_check() {
    print('-kustomize_wca_and_workloads_check-')
    sh "echo GIT_COMMIT=$GIT_COMMIT"

    print('Image checks wca and workloads...')
    image_check("wca")
    // examaples/kubernetes workloads like: mysql, memcached, memtier, redis use official images
    def images = ["mutilate", "hammerdb", "mysql_tpm_gauge", "memtier_benchmark", "stress_ng", "sysbench", "specjbb"]
    for(image in images){
        image_check("wca/$image")
    }

    print('Configure workloads...')
    kustomize_replace_commit_in_wca()
    def workloads = ["memcached-mutilate", "mysql-hammerdb", "redis-memtier", "stress", "sysbench-memory", "specjbb"]
    for(workload in workloads){
        kustomize_configure_workload_to_test("$workload")
    }

    print('Starting wca...')
    sh "kubectl apply -k ${WORKSPACE}/${KUSTOMIZATION_MONITORING}"
    sleep 40

    print('Create Service for Prometheus, for E2E only')
    sh "kubectl expose pod prometheus-prometheus-0 --type=NodePort --port=9090 --name=prometheus-nodeport-service --namespace prometheus && \
        kubectl patch service prometheus-nodeport-service --namespace=prometheus --type='json' --patch='[ \
        {\"op\": \"replace\", \"path\": \"/spec/ports/0/nodePort\", \"value\":30900}]'"

    print('Deploy workloads...')
    sh "kubectl apply -k ${WORKSPACE}/${KUSTOMIZATION_WORKLOAD}"

    print('Scale up workloads...')
    def list = ["mysql-hammerdb", "stress-stream", "redis-memtier", "sysbench-memory", "memcached-mutilate", "specjbb-preset"]
    for(item in list){
        sh "kubectl scale --replicas=1 statefulset $item-small"
    }

    print('Sleep while workloads are running...')
    sleep RUN_WORKLOADS_SLEEP_TIME
    print('Test kustomize metrics...')
    test_wca_metrics_kustomize()
}

def kustomize_replace_commit_in_wca() {
    contentReplace(
        configs: [
            fileContentReplaceConfig(
                configs: [
                    fileContentReplaceItemConfig( search: 'master', replace: "${GIT_COMMIT}", matchCount: 0),
                ],
                fileEncoding: 'UTF-8',
                filePath: "${WORKSPACE}/examples/kubernetes/monitoring/wca/kustomization.yaml")])
}

def kustomize_configure_workload_to_test(workload) {
    contentReplace(
    configs: [
        fileContentReplaceConfig(
            configs: [
                fileContentReplaceItemConfig( search: 'newTag: master', replace: "newTag: ${GIT_COMMIT}", matchCount: 0),
            ],
            fileEncoding: 'UTF-8',
            filePath: "${WORKSPACE}/examples/kubernetes/workloads/${workload}/kustomization.yaml")])

    contentReplace(
        configs: [
            fileContentReplaceConfig(
                configs: [
                    fileContentReplaceItemConfig( search: 'commonLabels:', replace:
                    "commonLabels:\n" +
                        "  build_commit: '${GIT_COMMIT}'\n" +
                        "  build_number: '${BUILD_NUMBER}'\n" +
                        "  node_name: '${NODE_NAME}'\n" +
                        "  workload_name: '${workload}'\n" +
                        "  env_uniq_id: '32'\n",
                    matchCount: 0),
                ],
                fileEncoding: 'UTF-8',
                filePath: "${WORKSPACE}/examples/kubernetes/workloads/${workload}/kustomization.yaml")])
}

def test_wca_metrics_kustomize() {
    sh "make venv; source env/bin/activate && \
        pytest ${WORKSPACE}/tests/e2e/test_wca_metrics.py::test_wca_metrics_kustomize --junitxml=unit_results.xml --log-level=debug --log-cli-level=debug -v && \
        pytest ${WORKSPACE}/tests/e2e/test_wca_metrics.py::test_wca_metrics_kustomize_throughput --junitxml=unit_results.xml --log-level=debug --log-cli-level=debug -v && \
        deactivate"
}

def image_check(image_name) {
    print("Check if workload (${image_name}) docker image build for this PR ${GIT_COMMIT}")
    check_image = sh(script: "curl -s ${DOCKER_REPOSITORY_URL}/v2/${image_name}/manifests/${GIT_COMMIT} | jq -r .name", returnStdout: true).trim()
    if (check_image == 'null') {
        print("Workload '${image_name}' docker image is not available!")
        sh "exit 1"
    } else {
        print("Found '${image_name}' image - curl output: ${check_image}")
    }
}


def generate_docs() {
    sh '''cp docs/metrics.rst docs/metrics.tmp.rst
          cp docs/metrics.csv docs/metrics.tmp.csv
          make generate_docs
          diff docs/metrics.csv docs/metrics.tmp.csv
          diff docs/metrics.rst docs/metrics.tmp.rst
          rm docs/metrics.tmp.rst
          rm docs/metrics.tmp.csv'''
}

def wait_for_wca_wcheduler() {
    def count = 1
    while(count <= 15) {
        check_image = sh(script: "kubectl -n wca-scheduler get pod | grep wca-scheduler | awk '{ print \$3 }'", returnStdout: true).trim()
        if (check_image == 'Running') {
            print("wca-scheduler is running")
            break
        }
        echo "Attempt $count. Sleeping for 1 second..."
        sleep(1)
        count++
    }
}
