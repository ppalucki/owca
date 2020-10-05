Getting started
===============

Below instruction is about run wca as DaemonSet in a cluster. This method uses kustomize to deploy all components.
Kustomize is available from kubectl 1.14 or as sperate binary from https://kustomize.io/.

1. Prepare cluster

   Workload Collocation Agent requires existing `wca` namespace and label `monitoring=wca` on nodes,
   where it will be deployed.

   1. Create `wca` namespace
   
      Namespace can be crated by using kubectl by the following command:
      
      ```bash
          kubectl create namespace wca
      ```

   2. Choose monitoring node 
      
      Label can be crated by using kubectl by the following command:
      
      ```bash
          kubectl label nodes node100 node101 node102 monitoring=wca
      ```
      
      Where names `node100 node101 node102` should be replaced by your kubernetes node names.
      If you want to deploy wca on all nodes, you can delete affinity in daemonset spec.


2. Build image (from main project repo) and push to your registry

   Build Docker image and push to private repo. Like in example below.
   You have to replace `DOCKER_REPOSITORY_URL` variable to your own docker registry.
   
   ```bash
       WCA_IMAGE=${DOCKER_REPOSITORY_URL}/wca
       WCA_TAG=master
       sudo docker build --build-arg MAKE_WCA_PACKAGE=yes --network host --target standalone -f Dockerfile -t $WCA_IMAGE:$WCA_TAG .
       docker push $WCA_IMAGE:$WCA_TAG
   ```
   
3. Overwrite docker image name to your local repository in examples/kubernetes/monitoring/wca/kustomization.yaml

   In kustomization.yaml, you can find field **images**. You have to replace `DOCKER_REPOSITORY_URL` variable to yours own docker registry.
   
   ```yaml
       ...
       images:
         - name: wca
           newName: ${DOCKER_REPOSITORY_URL}/wca
           newTag: master
       ...
   ```
   
   Note the default image (from **kustomization.yaml**) is using private repository in testing cluster and **master** tag.

4. (Optionally) Adjust the wca configuration

   Workload Collocation Agent requires configuration file. 
   You can use an example [wca config using by Daemonset](wca-config.yaml) or modify them.

5. Deploy wca
   Finally use the command below to deploy all wca components.
   
   ```bash
       kubectl apply -k examples/kubernetes/monitoring/wca
   ```


After deploying wca, you can deploy Prometheus operator to collect metrics from wca and visual them in Prometheus.
Create `prometheus` namespace and deploy using kustomize `kubectl apply -k examples/kubernetes/monitoring/prometheus`.
More information you'll find in `examples/kubernetes/monitoring/README.md`.

[README](DEVEL.md) for more advance wca configuration.


