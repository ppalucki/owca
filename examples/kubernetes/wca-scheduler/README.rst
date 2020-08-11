Example deployment
==================
Lets assume that:

- ``100.64.176.12`` - is node with docker image repository.
- ``100.64.176.36`` - is kubernetes master node with name `node36`
- there is ``wca-scheduler`` namespace on cluster

kube-scheduler configuration
----------------------------

Add new policy as config map:

``kubectl apply -f scheduler-policy.yaml``

Give access to read configmaps for kube-scheduler:

``kubectl apply -f scheduler-policy-role.yaml``

Edit kube-scheduler pod manifest on master node (``/etc/kubernetes/manifests/kube-scheduler.yaml``) to use policy with external scheduler.
For that, add in command `--policy-configmap=scheduler-policy` and `--policy-configmap-namespace=kube-system`.
Add to spec extra parametr `dnsPolicy: ClusterFirstWithHostNet`

.. code-block:: yaml

        spec:
          containers:
          - command:
            ...
            - --policy-configmap=scheduler-policy
            - --policy-configmap-namespace=kube-system
          ...
          dnsPolicy: ClusterFirstWithHostNet
   

wca-scheduler deployment
------------------------

Build wca-scheduler image with "100.64.176.12:80/wca-scheduler:latest" tag:

``docker build -t 100.64.176.12:80/wca-scheduler:latest -f examples/kubernetes/wca-scheduler/Dockerfile .``

Push image to repository:

``docker push 100.64.176.12:80/wca-scheduler:latest``

Apply wca-scheduler deployment:

``kubectl apply -k examples/kubernetes/wca-scheduler/``


TLS connection of wca-scheduler with kube-scheduler
------------------------------------------------

TLS is required to secure a connection between wca-scheduler and kube-scheduler.

Instructions are based on https://kubernetes.io/docs/tasks/tls/managing-tls-in-a-cluster/

You must generate a private key and Certificate Signing Request based on the private key.
Openssl is used below as a tool, but you can use another tools to generate CSR, for example cfssl.
In Certificate Signing Request the key ``subjectAltName`` has two values.
``wca-scheduler.wca-scheduler.svc`` is SVC's DNS name.
``100.64.176.36`` is example IP address, where wca-scheduler will be deployed.
You should change this IP address to address, where the wca-scheduler will be deployed.

Recommended parameters for key generations are:
- ECDSA at least 256 bits
- NIST p-256 curve for 256 bits

.. code-block:: shell

    # Generate a private key
    openssl ecparam -out key.pem -name prime256v1 -genkey

    # Generate a CSR. Change IP address to wca-scheduler node address!
    openssl req -new -key key.pem \
    -subj "/CN=wca-scheduler.wca-scheduler.svc" \
    -addext "subjectAltName=DNS:wca-scheduler.wca-scheduler.svc,IP:100.64.176.36" \
    -out server.csr \

The next step is to create CSR Kubernetes object and send it to apiserver.
It contains previously created CSR.
Created Kubernetes CertificateSigningRequest must be approved.
It can be done by an automated approval process or by a cluster administrator.
Below script uses example certificate approved by the administrator.
It is recommended to create a certificate with an expiry date of 3 years.

.. code-block:: shell

    # Create CSR K8S object
    cat <<EOF | kubectl apply -f -
    apiVersion: certificates.k8s.io/v1beta1
    kind: CertificateSigningRequest
    metadata:
      name: wca-scheduler.wca-scheduler
    spec:
      request: $(cat server.csr | base64 | tr -d '\n')
      usages:
      - digital signature
      - key encipherment
      - server auth
    EOF

    # The CSR must be approved by administrator (or automated approval process)
    kubectl certificate approve wca-scheduler.wca-scheduler

Now, you can download the signed certificate.
When you have a set of the certificate and the private key, you can create Secret using them.
The Secret will be forwarded to wca-scheduler.

.. code-block:: shell

    # Download the Certificate
    kubectl get csr wca-scheduler.wca-scheduler -o jsonpath='{.status.certificate}' | base64 --decode > server.crt

    # Create Secret with the certificate and the private key
    kubectl create secret generic wca-scheduler-cert --from-file server.crt --from-file server-key.pem --namespace wca-scheduler

mTLS connection
---------------

Implementing mTLS is easiest when there is a service mesh on the cluster.
This is due to the complicated exchange of certificates and the service mesh enables automation.
We checked (June, 2020) that Istio (version 1.6.2) does not support the use of sidecars in Pod
from Control Plane. Check out new versions of Istio,
because it is possible that feature will be added.
