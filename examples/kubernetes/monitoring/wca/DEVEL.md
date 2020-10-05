ADVANCED WCA DEPLOY
==================

WCA can be deployed in 3 different ways

1. as daemonset - described in README.md
2. as daemonset, but using kubelet to scrape workloads (historical option)
3. outside pod


WCA USING KUBELET
-----------

Add private key and certificate to Secrets

Workload Collocation Agent requires private key and certificate to connect with kubelet.
Example how add this files to Secrets:

.. code-block:: bash

    sudo kubectl create secret generic kubelet-key-crt --from-file=./client.crt --from-file=./client.key --namespace=wca
    
    
WCA OUTSIDE OF KUBERNETES
---------------

Optionally, you can use token to connect to Kube API Server, while WCA is using outside pod.
Save Bearer token and CA cert to enable connection. Set their path in wca configuration.  

```
SERVICE_ACCOUNT=wca

# Get the serviceaccount token secret name
SECRET=$(kubectl get serviceaccount ${SERVICE_ACCOUNT} -o json | jq -Mr '.secrets[].name | select(contains("token"))')

# Extract the Bearer token from the Secret and decode
kubectl get secret ${SECRET} -o json | jq -Mr '.data.token' | base64 -d > token

# Extract ca.crt from the Secret and decode
kubectl get secret ${SECRET} -o json | jq -Mr '.data["ca.crt"]' | base64 -d > ca.crt

# Get the API Server location
echo https://$(kubectl -n default get endpoints kubernetes --no-headers | awk '{ print $2 }') > server
```

Example config for wca:

```
node: !KubernetesNode
  client_token_path: "/home/user/wca/cert/token"
  server_cert_ca_path: "/home/user/wca/cert/ca.crt"
  kubeapi_host: "123.45.123.45"
  kubeapi_port: "6443"
  node_ip: "123.45.123.46"
```

Additionally, you can use following variables to connect to Kube API Server.
```
TOKEN=$(cat token)
APISERVER=$(cat server)
curl -s $APISERVER/openapi/v2  --header "Authorization: Bearer $TOKEN" --cacert ca.crt | less
```
