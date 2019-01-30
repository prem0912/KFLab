#!/usr/local/env bash

## Namespace to be used in k8s cluster for your application
NAMESPACE=default

## Ksonnet app name
APP_NAME=kubebench

## GITHUB version for official kubeflow components
KUBEFLOW_GITHUB_VERSION=v0.4.1

## GITHUB version for ciscoai components
CISCOAI_GITHUB_VERSION=master

## GITHUB version for kubebench components
KB_VERSION=v0.4.0
## Ksonnet environment name
KF_ENV=nativek8s

## Name of the NFS Persistent Volume
CONFIG_NAME="job-config"
JOB_NAME="my-benchmark"
