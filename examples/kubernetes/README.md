Kubernetes
==========

This folder contains 

# Getting started

Files in `monitoring` folder will deploy:

- **fluentd** for APMs metrics
- **grafana** for visualization
- **prometheus** using (prometheus-opearator) with custom rules for metrics collection, storage and 
  evaluation
- **wca** as daemonset (on nodes marked with label goal=service) - image build instructions [here](wca/README.md)
- **dashboard** for graphic cluster interface
- **kube-state-metrics** is a simple service that listens to the Kubernetes API server and generates metrics about the state of the objects

Files in `workloads` folder will deploy:

Files in `scheduler` folder will deploy:


## Deploy

### Monitoring deploy

1. You need to create dedicated namespaces for those applications like this:

```shell
kubectl create -f namespaces.yaml
```

2. Create hostPath based directory as grafana volume and Prometheus (PV).

```shell 
# on master node
sudo mkdir /var/lib/grafana
sudo chmod o+rw /var/lib/grafana
sudo mkdir /var/lib/prometheus
sudo chmod o+rw /var/lib/prometheus


kubectl create -f prometheus/persistent_volume.yaml
```

Grafana is deployed on master and hostPath as volume at accessible `/var/lib/grafana`

3. Using kustomize (-k) deploy all applications:

```shell
kubectl apply -k .
```

Note: in case of 

`unable to recognize ".": no matches for kind "Prometheus" in version "monitoring.coreos.com/v1"` 

warnings, please run `kubectl apply -k .` once again. This is a problem of invalid order of objects
when CRDs are created by kustomize and prometheus-operator.

You can check progress of deployment using `kubectl get -k .`.

#### Access

**Dashboard**  is exposed at: https://worker-node:6443/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#

**Prometheus** is exposed at: http://worker-node:30900/graph

**Grafana** is exposed at: http://worker-node:32135

Note that, after deployment remember to add prometheus source in Grafana.

```
URL: http://prometheus.prometheus:9090
Access: Server(default)
```

##### Dashboard

After deploy, token for access to Kubernetes Dashboard is available:

```
kubectl -n kubernetes-dashboard describe secret $(kubectl -n kubernetes-dashboard get secret | grep admin-user | awk '{print $1}')
```

Using version of Kubernetes Dashbord is v2.0.0-beta4.
https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-beta4/aio/deploy/recommended.yaml

To get token, used this instruction:
https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/creating-sample-user.md

#### Grafana configuration (addons)

##### Grafana boomtable plugin

Required for 2LM contention demo:

https://grafana.com/grafana/plugins/yesoreyeram-boomtable-panel

Grafana is deployed on master and hostPath as volume at accessible `/var/lib/grafana`

```shell 
kubectl exec --namespace grafana -ti `kubectl get pod -n grafana -oname --show-kind=false | cut -f 2 -d '/'` bash
grafana-cli plugins install yesoreyeram-boomtable-panel
# restart 
kubectl delete -n grafana `kubectl get pod -n grafana -oname`
```

##### Configuring Kubernetes-app for Grafana

Manually import dashboards from `grafana/dashboards`.

##### Configuring Kubernetes-app for Grafana

Parameters:

- URL: https://100.64.176.36:6443
- TLS Client Auth: checked
- With CA Cert: checked

```shell
# CA cert
kubectl config view --raw -ojsonpath="{@.clusters[0].cluster.certificate-authority-data}" | base64 -d
# Client cert
kubectl config view --raw -ojsonpath="{@.users[0].user.client-certificate-data}" | base64 -d
# Client key
kubectl config view --raw -ojsonpath="{@.users[0].user.client-key-data}" | base64 -d
```

### Workloads deploy

#### Node affinity

Load generators are only scheduled to nodes labeled with **goal="load_generator"**.
All "services" are only scheduled to nodes labeled with **goal="service"**.

##### Example node configuration

```
kubectl label node node10                      goal=load_generator
kubectl label node node10 node11 node13 node14 goal=service

kubectl label node node10 node11 node12 memory=1lm
kubectl label node node13 node14        memory=2lm
```

# Scheduler

## Installation

```sh
# after upload to /home/ppalucki/wca_remote_pycharm
sudo ln -vfs ~/wca_remote_pycharm/example/k8s_scheduler/kube-scheduler.yaml /etc/kubernetes/manifests/kube-scheduler.yaml
sudo ln -vfs ~/wca_remote_pycharm/example/k8s_scheduler/scheduler-policy.json /etc/kubernetes/scheduler-policy.json
sudo journalctl -u kubelet -f
```

# Troubleshooting

### Access WCA and fluentd

Both applications are running in **host** network namespace as daemonsets on ports:

- **WCA** : http://worker-node:9100
- **Fluentd** : http://worker-node:24231

### Cleaning up

**Warning!**: this removes all the objects (excluding CRDs and namespaces), but it will not remove
 hostPath based data for Grafana and Prometheus.

```shell
kubectl delete -f prometheus/persistent_volume.yaml
kubectl delete persistentvolumeclaim/prometheus-prometheus-db-prometheus-prometheus-0 -n prometheus
kubectl delete -k .
kubectl delete -f namespaces.yaml
```

### Remove namespace if stuck in "Terminating" state

**Warning!**: there might be orphaned resources left after that

```shell
kubectl proxy &
for NS in fluentd grafana prometheus wca; do
kubectl get namespace $NS -o json | sed '/kubernetes/d' | curl -k -H "Content-Type: application/json" -X PUT --data-binary @- 127.0.0.1:8001/api/v1/namespaces/$NS/finalize
done
```

### Service Monitor configuration

https://github.com/coreos/prometheus-operator/blob/master/Documentation/troubleshooting.md#L38

### Missing metrics from node_exporter (e.g. node_cpu)

This setup uses new version of node_exporter (>18.0) and Grafana kubernetes-app is based on old naminch scheme 
from node_exporter v 0.16
Prometheus rules "16-compatibilit-rules-new-to-old" are used to configured new evaluation rules from backward compatibility.


## Usefull links

- extra dashboards: https://github.com/coreos/kube-prometheus/blob/master/manifests/grafana-dashboardDefinitions.yaml
- coreos/kube-prometheus: https://github.com/coreos/kube-prometheus
- compatibility rules for node-exporter: https://github.com/prometheus/node_exporter/blob/master/docs/V0_16_UPGRADE_GUIDE.md
- prometheus operator API spec for Prometheus: https://github.com/coreos/prometheus-operator/blob/master/Documentation/api.md#prometheusspec
- Kubernetes-app for Grafana: https://grafana.com/grafana/plugins/grafana-kubernetes-app
- Boomtable widget for Grafana: https://grafana.com/grafana/plugins/yesoreyeram-boomtable-panel
- hostPath support for Prometheus operator: https://github.com/coreos/prometheus-operator/pull/1455
- create user for Dashboard: https://github.com/kubernetes/dashboard/blob/master/docs/user/access-control/creating-sample-user.md
- Docker images Kubernetes Dashboard: https://hub.docker.com/r/kubernetesui/dashboard/tags
