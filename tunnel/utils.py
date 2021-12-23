import copy
import json
import logging
import os
import socket
import subprocess

from kubernetes import client
from kubernetes import config

from jupyterjsc_tunneling.decorators import TimedCacheProperty
from jupyterjsc_tunneling.settings import LOGGER_NAME


log = logging.getLogger(LOGGER_NAME)

SYSTEM_NOT_AVAILABLE_STATUS = 550


class SystemNotAvailableException(Exception):
    pass


COULD_NOT_START_TUNNEL = 551


class CouldNotStartTunnelException(Exception):
    pass


COULD_NOT_START_REMOTE = 552


class CouldNotStartRemoteException(Exception):
    pass


K8S_ACTION_ERROR = 553


class K8sActionException(Exception):
    pass


def get_random_open_local_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_base_cmd(verbose=False):
    base_cmd = [
        "timeout",
        os.environ.get("SSHTIMEOUT", "3"),
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
    ]
    if verbose:
        base_cmd.append("-v")
    return base_cmd


def get_remote_cmd(action, verbose=False, **kwargs):
    base_cmd = get_base_cmd(verbose=verbose)
    return base_cmd + [f"remote_{kwargs['hostname']}", action]


def get_tunnel_cmd(action, verbose=False, **kwargs):
    base_cmd = get_base_cmd(verbose=verbose)
    action_cmd = [
        "-O",
        action,
        f"tunnel_{kwargs['hostname']}",
        "-L",
        f"0.0.0.0:{kwargs['local_port']}:{kwargs['target_node']}:{kwargs['target_port']}",
    ]
    check_cmd = [
        "-O",
        "check",
        f"tunnel_{kwargs['hostname']}",
    ]
    create_cmd = [f"tunnel_{kwargs['hostname']}"]
    cmds = {
        "cancel": base_cmd + action_cmd,
        "check": base_cmd + check_cmd,
        "create": base_cmd + create_cmd,
        "forward": base_cmd + action_cmd,
    }
    return cmds[action]


def get_cmd(prefix, action, verbose=False, **kwargs):
    if prefix == "remote":
        return get_remote_cmd(action, verbose=verbose, **kwargs)
    elif prefix == "tunnel":
        return get_tunnel_cmd(action, verbose=verbose, **kwargs)
    return []


alert_admins_log = {True: log.critical, False: log.warning}
action_log = {
    "cancel": log.info,
    "check": log.debug,
    "create": log.debug,
    "forward": log.info,
    "start": log.info,
    "status": log.debug,
    "stop": log.info,
}


def run_popen_cmd(
    prefix,
    action,
    log_msg,
    alert_admins=False,
    max_attempts=1,
    verbose=False,
    expected_returncodes=[0],
    **kwargs,
):
    cmd = get_cmd(prefix, action, verbose=verbose, **kwargs)
    log_extra = copy.deepcopy(kwargs)
    log_extra["cmd"] = cmd
    action_log[action](
        f"{log_msg} ...",
        extra=log_extra,
    )

    with subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE) as p:
        stdout, stderr = p.communicate()
        returncode = p.returncode

    log_extra["stdout"] = stdout.decode("utf-8").strip()
    log_extra["stderr"] = stderr.decode("utf-8").strip()
    log_extra["returncode"] = returncode

    action_log[action](
        f"{log_msg} done",
        extra=log_extra,
    )

    if returncode not in expected_returncodes:
        if max_attempts > 1:
            return run_popen_cmd(
                prefix,
                action,
                log_msg,
                alert_admins=alert_admins,
                max_attempts=max_attempts - 1,
                verbose=max_attempts == 2,
                **kwargs,
            )
        alert_admins_log[alert_admins](
            f"{log_msg} failed. Action may be required",
            extra=log_extra,
        )
    return returncode


def check_tunnel_connection(func):
    def build_up_connection(*args, **kwargs):
        # check if ssh connection to the node is up
        if (
            run_popen_cmd("tunnel", "check", "SSH tunnel check connection", **kwargs)
            != 0
        ):
            if (
                run_popen_cmd(
                    "tunnel",
                    "create",
                    "SSH tunnel create connection",
                    alert_admins=True,
                    max_attempts=3,
                    **kwargs,
                )
                != 0
            ):
                raise SystemNotAvailableException(
                    f"uuidcode={kwargs['uuidcode']} - Could not connect to {kwargs['hostname']}"
                )
        return func(*args, **kwargs)

    return build_up_connection


class TimedCachedProperties:
    @TimedCacheProperty(timeout=60)
    def system_config(self):
        systems_config_path = os.environ.get("SYSTEMS_PATH", "")
        with open(systems_config_path, "r") as f:
            systems_config = json.load(f)
        return systems_config


@check_tunnel_connection
def stop_tunnel(**kwargs):
    run_popen_cmd(
        "tunnel",
        "cancel",
        "SSH stop tunnel",
        alert_admins=True,
        max_attempts=2,
        **kwargs,
    )


@check_tunnel_connection
def start_tunnel(**kwargs):
    return (
        run_popen_cmd(
            "tunnel",
            "forward",
            "SSH start tunnel",
            alert_admins=True,
            max_attempts=3,
            **kwargs,
        )
        == 0
    )


def start_remote(**kwargs):
    return (
        run_popen_cmd(
            "remote",
            "start",
            "SSH start remote",
            alert_admins=True,
            max_attempts=3,
            expected_returncodes=[217],
            **kwargs,
        )
        == 217
    )


def status_remote(**kwargs):
    return (
        run_popen_cmd(
            "remote",
            "status",
            "SSH status remote",
            alert_admins=False,
            max_attempts=1,
            expected_returncodes=[217, 218],
            **kwargs,
        )
        == 217
    )


def stop_remote(**kwargs):
    run_popen_cmd(
        "remote",
        "stop",
        "SSH stop remote",
        alert_admins=True,
        max_attempts=3,
        expected_returncodes=[218],
        **kwargs,
    ) == 218


import os
from kubernetes import client, config


def k8s_get_client():
    config.load_incluster_config()
    return client.CoreV1Api()


def k8s_get_svc_name(backend_id):
    return f"{os.environ.get('DEPLOYMENT_NAME', 'tunneling')}-{backend_id}"


def k8s_get_svc_namespace():
    return os.environ.get("DEPLOYMENT_NAMESPACE", "default")


def k8s_create_svc(**kwargs):
    v1 = k8s_get_client()
    name = k8s_get_svc_name(kwargs["backend_id"])
    namespace = k8s_get_svc_namespace()
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "labels": {
                "name": name,
            },
            "name": name,
            "resourceversion": "v1",
        },
        "spec": {
            "ports": [
                {
                    "name": "port",
                    "port": kwargs["local_port"],
                    "protocol": "TCP",
                    "targetPort": kwargs["local_port"],
                }
            ],
            "selector": {"name": name},
        },
    }
    return v1.create_namespaced_service(
        body=service_manifest, namespace=namespace
    ).to_dict()


# def k8s_get_svc(backend_id, **kwargs):
#     v1 = k8s_get_client()
#     name = k8s_get_svc_name(backend_id)
#     namespace = k8s_get_svc_namespace()
#     return v1.read_namespaced_service(name=name, namespace=namespace).to_dict()


def k8s_delete_svc(**kwargs):
    v1 = k8s_get_client()
    name = k8s_get_svc_name(kwargs["backend_id"])
    namespace = k8s_get_svc_namespace()
    return v1.delete_namespaced_service(name=name, namespace=namespace).to_dict()


k8s_log = {
    "create": log.debug,
    # "get": log.debug,
    "delete": log.debug,
}

k8s_func = {
    "create": k8s_create_svc,
    # "get": k8s_get_svc,
    "delete": k8s_delete_svc,
}


def k8s_svc(action, alert_admins=False, **kwargs):
    log_extra = copy.deepcopy(kwargs)
    k8s_log[action](f"Call K8s API to {action} svc ...", extra=log_extra)
    try:
        response = k8s_func[action](**kwargs)
        log_extra["k8s_response"] = response
    except Exception as e:
        alert_admins_log[alert_admins](
            f"Call K8s API to {action} svc failed", exc_info=True, extra=log_extra
        )
        raise K8sActionException(
            f"uuidcode={log_extra.get('uuidcode', 'no-uuidcode')} - Call K8s API to {action} svc failed"
        )
    k8s_log[action](f"Call K8s API to {action} svc done", extra=log_extra)
