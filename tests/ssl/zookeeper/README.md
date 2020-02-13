## Zookeeper SSL test
#### Make workspace.
```
mkdir /tmp/zk
```
#### Generate server certs.
```
keytool -keystore /tmp/zk/keyStore.jks -genkey -keyalg RSA -v -dname "CN=server" -alias server -storepass zookeeper -keypass zookeeper
```
#### Because keytool prepared self-signed cert, we need to import it to recognize zookeeper.
```
keytool -export -alias server -keystore /tmp/zk/keyStore.jks -rfc -file /tmp/zk/serverCA.crt -storepass zookeeper -keypass zookeeper 
```
#### Generate CA certs.
```
openssl genrsa -out /tmp/zk/root.key 2048
```

```
openssl req -x509 -new -nodes -key /tmp/zk/root.key -sha256 -days 1024 -out /tmp/zk/root.crt -subj="/CN=root"
```
#### Import CA to zk truststore.
```
keytool -import -file /tmp/zk/root.crt -alias theCARoot -keystore /tmp/zk/trustStore.jks -storepass zookeeper -noprompt 
```
#### Generate client certs and sign with CA.
```
openssl genrsa -out /tmp/zk/client.key 2048
```

```
openssl req -new -sha256 -key /tmp/zk/client.key -subj "/CN=client" -out /tmp/zk/client.csr
```

```
openssl x509 -req -in /tmp/zk/client.csr -CA /tmp/zk/root.crt -CAkey /tmp/zk/root.key -CAcreateserial -out /tmp/zk/client.crt -days 500 -sha256
```

#### Generate client weak certs and sign by CA.
```
openssl genrsa -out /tmp/zk/weak.key 1024
```

```
openssl req -new -sha256 -key /tmp/zk/weak.key -subj "/CN=weak" -out /tmp/zk/weak.csr
```

```
openssl x509 -req -in /tmp/zk/weak.csr -CA /tmp/zk/root.crt -CAkey /tmp/zk/root.key -CAcreateserial -out /tmp/zk/weak.crt -days 500 -sha256
```
#### Install zookeeper.
```
wget https://www-eu.apache.org/dist/zookeeper/zookeeper-3.5.5/apache-zookeeper-3.5.5-bin.tar.gz -P /tmp/zk
```

```
tar -xf /tmp/zk/apache-zookeeper-3.5.5-bin.tar.gz -C /tmp/zk
```
#### Prepare configuration.
```
cp /tmp/zk/apache-zookeeper-3.5.5-bin/conf/zoo_sample.cfg /tmp/zk/apache-zookeeper-3.5.5-bin/conf/zoo.cfg
```

```
echo "secureClientPort=2281" >> /tmp/zk/apache-zookeeper-3.5.5-bin/conf/zoo.cfg
```
## Test for good configuration.
#### Run zk.
```
export SERVER_JVMFLAGS="
-Djavax.net.debug=all
-Dzookeeper.ssl.keyStore.type=JKS
-Dzookeeper.serverCnxnFactory=org.apache.zookeeper.server.NettyServerCnxnFactory
-Dzookeeper.ssl.keyStore.location=/tmp/zk/keyStore.jks
-Dzookeeper.ssl.keyStore.password=zookeeper
-Dzookeeper.ssl.trustStore.location=/tmp/zk/trustStore.jks
-Dzookeeper.ssl.trustStore.password=zookeeper
"
```

```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh start
```
#### Run python script.
```
source env/bin/activate
env PYTHONPATH=. python tests/ssl/zookeeper/good_configuration.py
```
#### Stop zk.
```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh stop
```
## Test weak protocol condition.
Zookeeper 3.5.5 uses TLSv1.2 by default.
## Test weak algorithm condition.
#### Run zk.
```
export SERVER_JVMFLAGS="
-Djavax.net.debug=all
-Dzookeeper.ssl.keyStore.type=JKS
-Dzookeeper.serverCnxnFactory=org.apache.zookeeper.server.NettyServerCnxnFactory
-Dzookeeper.ssl.keyStore.location=/tmp/zk/keyStore.jks
-Dzookeeper.ssl.keyStore.password=zookeeper
-Dzookeeper.ssl.trustStore.location=/tmp/zk/trustStore.jks
-Dzookeeper.ssl.trustStore.password=zookeeper
-Djdk.tls.server.cipherSuites=TLS_ECDHE_ECDSA_WITH_3DES_EDE_CBC_SHA"
```

```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh start
```
#### Run python script.
```
source env/bin/activate
env PYTHONPATH=. python tests/ssl/zookeeper/good_configuration.py
```
#### Stop zk.
```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh stop
```
## Test too small client key size condition.
#### Run zk.
```
export SERVER_JVMFLAGS="
-Djavax.net.debug=all
-Dzookeeper.ssl.keyStore.type=JKS
-Dzookeeper.serverCnxnFactory=org.apache.zookeeper.server.NettyServerCnxnFactory
-Dzookeeper.ssl.keyStore.location=/tmp/zk/keyStore.jks
-Dzookeeper.ssl.keyStore.password=zookeeper
-Dzookeeper.ssl.trustStore.location=/tmp/zk/trustStore.jks
-Dzookeeper.ssl.trustStore.password=zookeeper
"
```

```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh start
```
#### Run python script.
```
source env/bin/activate
env PYTHONPATH=. python tests/ssl/zookeeper/weak_client_cert.py
```
#### Stop zk.
```
sudo -E /tmp/zk/apache-zookeeper-3.5.5-bin/bin/zkServer.sh stop
```
#### Clean workspace.
```
sudo rm -rf /tmp/zk
```
