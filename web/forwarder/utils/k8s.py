import os

from kubernetes import client
from kubernetes import config


def _k8s_get_client_core():
    config.load_incluster_config()
    return client.CoreV1Api()


def _k8s_get_namespace():
    return os.environ.get("DEPLOYMENT_NAMESPACE", "default")


def get_tunnel_sts_pod_names():
    v1 = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    label = f"app={os.environ.get('DEPLOYMENT_NAME', 'drf-tunnel')}"
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label)

    pod_names = []
    for pod in pods.items:
        # there might be other pods of drf-tunnel, such as the down scaler
        if "statefulset.kubernetes.io/pod-name" in pod.metadata.labels:
            name = pod.metadata.labels['statefulset.kubernetes.io/pod-name']
            pod_names.append(name)
    return pod_names


def edit_service_selector(service_name, pod_name, port):
    v1 = _k8s_get_client_core()
    namespace = _k8s_get_namespace()
    service = v1.read_namespaced_service(service_name, namespace)
    service.spec.selector["statefulset.kubernetes.io/pod-name"] = pod_name
    service.spec.ports[0].target_port = port
    v1.patch_namespaced_service(
        service_name, namespace,
        body=service
    )