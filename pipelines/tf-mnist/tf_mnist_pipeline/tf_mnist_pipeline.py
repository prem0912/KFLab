#!/usr/bin/env python3

import kfp.dsl as dsl
from kubernetes import client as k8s_client


def mnist_train_op(tf_export_dir: str, train_steps: int, batch_size: int,
                   learning_rate: float, step_name='mnist-training'):
    return dsl.ContainerOp(
        name=step_name,
        image='gcr.io/kubeflow-examples/mnist/model:v20190304-v0.2-176-g15d997b',
        arguments=[
            '/opt/model.py',
            '--tf-export-dir', tf_export_dir,
            '--tf-train-steps', train_steps,
            '--tf-batch-size', batch_size,
            '--tf-learning-rate', learning_rate
        ]
    )


def kubeflow_serve_op(model_export_dir:str, step_name='deploy-serving'):
    return dsl.ContainerOp(
        name=step_name,
        image='krishnadurai/ml-pipelines-tf-mnist-deploy-service:0.2',
        arguments=[
            '--model-export-path', model_export_dir,
            '--server-name', 'mnist-service'
        ]
    )

def kubeflow_web_ui_op(step_name='web-ui'):
    return dsl.ContainerOp(
        name='web-ui',
        image='gcr.io/kubeflow-examples/mnist/deploy-service:latest',
        arguments=[
            '--image', 'gcr.io/kubeflow-examples/mnist/web-ui:'
                       'v20190304-v0.2-176-g15d997b-pipelines',
            '--name', 'web-ui',
            '--container-port', '5000',
            '--service-port', '80',
            '--service-type', "LoadBalancer"
        ]
    )

@dsl.pipeline(
    name='TF Mnist Pipeline',
    description='Mnist Pipelines for on-prem cluster'
)
def tf_mnist_pipeline(
        model_name='mnist',
        model_export_dir='model/export',
        training_steps=200,
        batch_size=100,
        learning_rate=0.01):

    # k8s volume resources for workflow
    nfs_pvc = k8s_client.V1PersistentVolumeClaimVolumeSource(claim_name='nfs')
    nfs_volume = k8s_client.V1Volume(name='nfs', persistent_volume_claim=nfs_pvc)
    nfs_volume_mount = k8s_client.V1VolumeMount(mount_path='/mnt/', name='nfs')

    mnist_training = mnist_train_op(
        '/mnt/%s' % model_export_dir,
        training_steps,
        batch_size,
        learning_rate)
    mnist_training.add_volume(nfs_volume)
    mnist_training.add_volume_mount(nfs_volume_mount)

    deploy_serving = kubeflow_serve_op('/mnt/%s' % model_export_dir)
    deploy_serving.add_volume(nfs_volume)
    deploy_serving.add_volume_mount(nfs_volume_mount)
    deploy_serving.after(mnist_training)

    web_ui = kubeflow_web_ui_op()
    web_ui.add_volume(nfs_volume)
    web_ui.add_volume_mount(nfs_volume_mount)
    web_ui.after(deploy_serving)

if __name__ == "__main__":
    import kfp.compiler as compiler
    compiler.Compiler().compile(tf_mnist_pipeline, __file__+'.tar.gz')
