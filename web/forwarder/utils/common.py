import logging
import os

from django.db.models import Count
from jupyterjsc_tunneling.settings import LOGGER_NAME
from tunnel.models import TunnelModel

from .k8s import get_tunnel_sts_pod_names

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


def get_request_properties():
    service_name = os.environ.get("TUNNEL_USERNAME", "tunnel")
    authentication_token = os.environ.get(
        f"{service_name.upper()}_AUTHENTICATION_TOKEN", None
    )
    if not authentication_token:
        log.critical(
            f"{service_name.upper()}_AUTHENTICATION_TOKEN env variable not defined. Cannot communicate with {service_name}."
        )
    headers = {"Authorization": authentication_token}
    ca = os.environ.get("CERTIFICATE_PATH", "/mnt/shared-data/certs/ca.pem")

    return {"headers": headers, "ca": ca}


def _get_active_tunnel_pods():
    active_replicas_path = os.environ.get(
        "ACTIVE_REPLICAS_PATH", "/mnt/replicas/desired_replicas"
    )
    with open(active_replicas_path) as f:
        active_tunnel_pods = f.read()
    return active_tunnel_pods


def get_pod_with_least_tunnels():
    query_set = TunnelModel.objects.values("tunnel_pod")
    # Check if a new tunnel pod exists
    db_tunnel_pods = list(
        query_set.values_list("tunnel_pod", flat=True).distinct("tunnel_pod")
    )
    sts_tunnel_pods = get_tunnel_sts_pod_names()
    active_tunnel_pods = _get_active_tunnel_pods()
    if active_tunnel_pods == "all":
        available_pods = sts_tunnel_pods
    else:
        available_pods = sts_tunnel_pods[0 : int(active_tunnel_pods)]
    for pod in available_pods:
        # If a pod exists but has no db entry, it does not have any tunnels
        # and hence has the least amount of tunnels
        if pod not in db_tunnel_pods:
            return pod
    # Otherwise check database for pod with least tunnels
    min_tunnel_pod_query = query_set.annotate(count=Count("tunnel_pod")).order_by(
        "count"
    )
    min_tunnel_pod = min_tunnel_pod_query.first()["tunnel_pod"]
    while min_tunnel_pod not in available_pods:
        min_tunnel_pod_query = min_tunnel_pod_query.exclude(tunnel_pod=min_tunnel_pod)
        min_tunnel_pod = min_tunnel_pod_query.first()["tunnel_pod"]
    return min_tunnel_pod


def get_service_url(pod=None, suffix="", endpoint="tunnel"):
    subdomain = os.environ.get("DEPLOYMENT_NAME", "tunnel")
    namespace = os.environ.get("DEPLOYMENT_NAMESPACE", "default")
    port = os.environ.get("REQUEST_PORT", "8443")
    proto = os.environ.get("REQUEST_PROTOCOL", "https")
    if pod:
        url = f"{proto}://{'.'.join([pod, subdomain, namespace,'svc'])}:{port}/api/{endpoint}/"
    else:
        # service url if no pod is specified
        url = f"{proto}://{'.'.join([subdomain, namespace,'svc'])}/api/{endpoint}/"
    if suffix:
        url += f"{suffix}" if suffix.endswith("/") else f"{suffix}/"
    return url


def get_least_tunnel_pod_url():
    forward_pod = get_pod_with_least_tunnels()
    return get_service_url(forward_pod)


def get_responsible_pod_url(instance, suffix=""):
    responsible_pod = instance.tunnel_pod
    service_url = get_service_url(responsible_pod)
    if suffix:
        service_url += f"{suffix}" if suffix.endswith("/") else f"{suffix}/"
    return service_url


def get_first_pod_url():
    pods = get_tunnel_sts_pod_names()
    return get_service_url(pods[0])
