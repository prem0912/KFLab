#!/usr/bin/env python3

import kfp.dsl as dsl
from kubernetes import client as k8s_client


def mnist_train_op(tf_data_dir: str, tf_model_dir: str,
                   tf_export_dir: str, train_steps: int, batch_size: int,
                   learning_rate: float, step_name='mnist-training'):
    return dsl.ContainerOp(
        name=step_name,
        image='docker.io/jinchi/mnist_model:0.2',
        arguments=[
            '/opt/model.py',
            '--tf-data-dir', tf_data_dir,
            '--tf-model-dir', tf_model_dir,
            '--tf-export-dir', tf_export_dir,
            '--tf-train-steps', train_steps,
            '--tf-batch-size', batch_size,
            '--tf-learning-rate', learning_rate,
        ],
        file_outputs={'export': '/tf_export_dir.txt'}
    )


def kubeflow_deploy_op(tf_export_dir:str, server_name: str, pvc_name: str, step_name='deploy_serving'):
    return dsl.ContainerOp(
        name=step_name,
        image='gcr.io/ml-pipeline/ml-pipeline-kubeflow-deployer:7775692adf28d6f79098e76e839986c9ee55dd61',
        arguments=[
            '--cluster-name', 'mnist-pipeline',
            '--model-export-path', tf_export_dir,
            '--server-name', server_name,
            '--pvc-name', pvc_name,
        ]
    )


@dsl.pipeline(
    name='TF Mnist Pipeline',
    description='Mnist Pipelines for on-prem cluster'
)
def tf_mnist_pipeline(
        model_name='mnist',
        pvc_name='nfs',
        tf_data_dir='data',
        tf_model_dir='model',
        tf_export_dir='model/export',
        training_steps=200,
        batch_size=100,
        learning_rate=0.01):

    # k8s volume resources for workflow
    nfs_pvc = k8s_client.V1PersistentVolumeClaimVolumeSource(claim_name='nfs')
    nfs_volume = k8s_client.V1Volume(name='nfs', persistent_volume_claim=nfs_pvc)
    nfs_volume_mount = k8s_client.V1VolumeMount(mount_path='/mnt/', name='nfs')

    mnist_training = mnist_train_op(
        '/mnt/%s' % tf_data_dir,
        '/mnt/%s' % tf_model_dir,
        '/mnt/%s' % tf_export_dir,
        training_steps,
        batch_size,
        learning_rate)
    mnist_training.add_volume(nfs_volume)
    mnist_training.add_volume_mount(nfs_volume_mount)

    deploy_serving = kubeflow_deploy_op('/mnt/%s' % tf_export_dir, model_name, pvc_name)
    deploy_serving.add_volume(nfs_volume)
    deploy_serving.add_volume_mount(nfs_volume_mount)
    deploy_serving.after(mnist_training)

if __name__ == "__main__":
    import kfp.compiler as compiler
    compiler.Compiler().compile(tf_mnist_pipeline, __file__+'.tar.gz')
