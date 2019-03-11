#!/bin/bash -e

# Install Istio
kubectl apply --filename https://gist.githubusercontent.com/swiftdiaries/04847b5dc194df0e1357441054bd240d/raw/2f84e8b9addb2b605a4d4742cc33aef820e2177e/Istio%2520installation%2520YAML

# Create a kubeflow namespace
kubectl create ns kubeflow

# Set label to enable istio-injection on the kubeflow namespace
kubectl label namespace kubeflow istio-injection=enabled


# Create the ksonnet app to deploy Pipelines
ks init mnist-pipelines-app --skip-default-registries --env pipelines --namespace kubeflow
cd mnist-pipelines-app

# Google Kubernetes Engine clusters have their name beginning with 'gke' prefix
#TODO: Store the outcome of this expression in a variable
if [[ $(kubectl config current-context | cut -c1-3) != "gke" ]]; then
  # Create Volumes, Volume Claims for Pipeline components
  # For GKE clusters, pipeline ksonnet config sets volumes up on its own with google
  # persistent storage
  kubectl create -f ../pipeline-config/storage-class.yaml
  # Annotate storage class local storage as the default storage for the cluster
  kubectl patch storageclass local-storage -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
  kubectl create -f ../pipeline-config/pv-mysql.yaml
  kubectl create -f ../pipeline-config/pv-minio.yaml
fi

ks registry add kubeflow https://github.com/kubeflow/kubeflow/tree/master/kubeflow
ks registry add ciscoai-global github.com/CiscoAI/ks-packages/tree/master/pkg

ks pkg install kubeflow/common
ks pkg install kubeflow/pipeline
ks pkg install kubeflow/argo
ks pkg install ciscoai-global/nfs-server
ks pkg install ciscoai-global/nfs-volume
ks generate ambassador ambassador
ks generate pipeline pipeline
ks generate argo argo
ks generate nfs-server nfs-server

if [[ $(kubectl config current-context | cut -c1-3) != "gke" ]]; then
  ks param set pipeline mysqlPvName pv-mysql
  ks param set pipeline minioPvName pv-minio
fi

ks apply pipelines

NFS_SERVER_IP=`kubectl -n kubeflow get svc/nfs-server  --output=jsonpath={.spec.clusterIP}`
echo "NFS Server IP: ${NFS_SERVER_IP}"
ks generate io.ksonnet.pkg.nfs-volume nfs-volume  --name=nfs --nfs_server_ip=${NFS_SERVER_IP}
ks apply pipelines -c nfs-volume


# Install Pipelines SDK
RELEASE_VERSION=0.1.7
pip3 install https://storage.googleapis.com/ml-pipeline/release/${RELEASE_VERSION}/kfp.tar.gz --upgrade

cd ..
dsl-compile --py tf_mnist_pipeline/tf_mnist_pipeline.py --output tf_mnist_pipeline.tar.gz

export NAMESPACE=kubeflow
kubectl port-forward -n ${NAMESPACE} $(kubectl get pods -n ${NAMESPACE} --selector=service=ambassador -o jsonpath='{.items[0].metadata.name}') 8080:80
