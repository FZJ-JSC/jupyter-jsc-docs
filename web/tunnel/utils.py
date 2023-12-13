import copy
import json
import logging
import os
import socket
import subprocess
import time
import uuid

from jupyterjsc_tunneling.settings import LOGGER_NAME
from kubernetes import client
from kubernetes import config


log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class RemoteExceptionError(Exception):
    pass


class TunnelExceptionError(Exception):
    pass


SYSTEM_NOT_AVAILABLE_ERROR_MESSAGE = "System is not available"


def get_random_open_local_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def get_base_cmd(verbose=False):
    base_cmd = [
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
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
    "check": log.trace,
    "create": log.trace,
    "forward": log.info,
    "start": log.trace,
    "status": log.trace,
    "stop": log.trace,
}


def run_popen_cmd(
    prefix,
    action,
    log_msg,
    alert_admins=False,
    max_attempts=1,
    verbose=False,
    expected_returncodes=[0],
    exc_info=True,
    timeout=None,
    **kwargs,
):
    cmd = get_cmd(prefix, action, verbose=verbose, **kwargs)
    log_extra = copy.deepcopy(kwargs)
    log_extra["cmd"] = cmd
    action_log[action](
        f"{log_msg} ...",
        extra=log_extra,
    )

    # gunicorn preload app feature does not use gunicorn user/group but
    # the current uid instead. Which is root. We don't want to run commands as root.
    def set_uid():
        try:
            os.setuid(1000)
        except:
            pass

    if not timeout:
        timeout = int(os.environ.get("SSHTIMEOUT", "3"))
    p = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=set_uid
    )
    try:
        stdout, stderr = p.communicate(timeout=timeout)
        returncode = p.returncode
    except subprocess.TimeoutExpired:
        p.kill()
        returncode = 124
        stdout, stderr = b"timeout", b""

    log_extra["stdout"] = stdout.decode("utf-8").strip()
    if exc_info:
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
                expected_returncodes=expected_returncodes,
                exc_info=exc_info,
                timeout=timeout,
                **kwargs,
            )
        if not action == "check":
            # Check is expected to fail. So no extra log required
            alert_admins_log[alert_admins](
                f"{log_msg} failed. Action may be required",
                extra=log_extra,
                exc_info=exc_info,
            )
        raise Exception(
            f"unexpected returncode: {returncode} not in {expected_returncodes}"
        )
    return returncode


def check_tunnel_connection(func):
    def build_up_connection(*args, **kwargs):
        # check if ssh connection to the node is up
        try:
            run_popen_cmd(
                "tunnel",
                "check",
                "SSH tunnel check connection",
                max_attempts=1,
                **kwargs,
            )
        except:
            # That's ok. Let's try to start the tunnel.
            try:
                run_popen_cmd(
                    "tunnel",
                    "create",
                    "SSH tunnel create connection",
                    max_attempts=3,
                    **kwargs,
                )
            except:
                log.warning("Could not create ssh tunnel.", extra=kwargs, exc_info=True)
                if kwargs.get("raise_exception", True):
                    # That's not ok. We could not connect to the system
                    raise TunnelExceptionError(
                        f"System not available: Could not connect via ssh to {kwargs['hostname']}",
                        f"Request identification: {kwargs['uuidcode']}",
                    )
                else:
                    log.warning(
                        f"System not available: Could not connect via ssh to {kwargs['hostname']}. Request identification: {kwargs['uuidcode']}",
                        extra=kwargs,
                    )
        return func(*args, **kwargs)

    return build_up_connection


def stop_and_delete(alert_admins=False, raise_exception=False, **kwargs):
    stop_tunnel(alert_admins=alert_admins, raise_exception=raise_exception, **kwargs)
    k8s_svc(
        "delete", alert_admins=alert_admins, raise_exception=raise_exception, **kwargs
    )


@check_tunnel_connection
def stop_tunnel(alert_admins=True, raise_exception=True, **kwargs):
    try:
        run_popen_cmd(
            "tunnel",
            "cancel",
            "SSH stop tunnel",
            alert_admins=alert_admins,
            max_attempts=1,
            **kwargs,
        )
    except Exception as e:
        alert_admins_log[alert_admins](
            "Could not stop ssh tunnel", extra=kwargs, exc_info=True
        )
        if raise_exception:
            raise TunnelExceptionError("Could not stop ssh tunnel", str(e))


@check_tunnel_connection
def start_tunnel(alert_admins=True, raise_exception=True, **validated_data):
    try:
        run_popen_cmd(
            "tunnel",
            "forward",
            "SSH start tunnel",
            alert_admins=alert_admins,
            max_attempts=3,
            **validated_data,
        )
    except Exception as e:
        alert_admins_log[alert_admins](
            "Could not start tunnel", extra=validated_data, exc_info=True
        )
        if raise_exception:
            raise TunnelExceptionError(
                "Could not forward port to system via ssh tunnel", str(e)
            )


def start_remote(
    alert_admins=True,
    raise_exception=True,
    exc_info=True,
    timeout=None,
    verbose=False,
    **validated_data,
):
    try:
        run_popen_cmd(
            "remote",
            "start",
            "SSH start remote",
            alert_admins=True,
            max_attempts=3,
            expected_returncodes=[217],
            exc_info=exc_info,
            timeout=timeout,
            **validated_data,
        )
    except Exception as e:
        # it's already logged in run_popen_cmd
        if verbose:
            alert_admins_log[alert_admins](
                "Could not start remote ssh tunnel",
                extra=validated_data,
                exc_info=exc_info,
            )
        if raise_exception:
            raise TunnelExceptionError("Could not start remote ssh tunnel", str(e))


def status_remote(alert_admins=True, raise_exception=True, **data):
    try:
        return (
            run_popen_cmd(
                "remote",
                "status",
                "SSH status remote",
                alert_admins=alert_admins,
                max_attempts=1,
                expected_returncodes=[217, 218],
                **data,
            )
            == 217
        )
    except Exception as e:
        alert_admins_log[alert_admins](
            "Could not receive status from remote ssh tunnel", extra=data, exc_info=True
        )
        if raise_exception:
            raise RemoteExceptionError(
                "Could not receive status from remote ssh tunnel", str(e)
            )


def stop_remote(alert_admins=True, raise_exception=True, **data):
    try:
        run_popen_cmd(
            "remote",
            "stop",
            "SSH stop remote",
            alert_admins=True,
            max_attempts=3,
            expected_returncodes=[218],
            **data,
        )
    except Exception as e:
        alert_admins_log[alert_admins](
            "Could not stop remote ssh tunnel", extra=data, exc_info=True
        )
        if raise_exception:
            raise RemoteExceptionError("Could not stop remote ssh tunnel", str(e))


def k8s_get_client():
    config.load_incluster_config()
    return client.CoreV1Api()


def k8s_get_svc_namespace():
    return os.environ.get("DEPLOYMENT_NAMESPACE", "default")


def k8s_create_svc(**kwargs):
    v1 = k8s_get_client()
    deployment_name = os.environ.get("DEPLOYMENT_NAME", "tunneling")
    pod_name = os.environ.get("HOSTNAME", "drf-tunnel-0")
    name = kwargs["svc_name"]
    namespace = k8s_get_svc_namespace()
    labels = {"name": name}
    if kwargs.get("labels", {}):
        labels.update(json.loads(kwargs["labels"]))
    service_manifest = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "labels": labels,
            "name": name,
            "resourceversion": "v1",
        },
        "spec": {
            "ports": [
                {
                    "name": "port",
                    "port": kwargs["svc_port"],
                    "protocol": "TCP",
                    "targetPort": kwargs["local_port"],
                }
            ],
            "selector": {
                "app": deployment_name,
                "statefulset.kubernetes.io/pod-name": pod_name,
            },
        },
    }
    return v1.create_namespaced_service(
        body=service_manifest, namespace=namespace
    ).to_dict()


# def k8s_get_svc(servername, **kwargs):
#     v1 = k8s_get_client()
#     name = k8s_get_svc_name(servername)
#     namespace = k8s_get_svc_namespace()
#     return v1.read_namespaced_service(name=name, namespace=namespace).to_dict()


def k8s_delete_svc(**kwargs):
    v1 = k8s_get_client()
    name = kwargs["svc_name"]
    namespace = k8s_get_svc_namespace()
    return v1.delete_namespaced_service(name=name, namespace=namespace).to_dict()


k8s_log = {
    "create": log.info,
    # "get": log.debug,
    "delete": log.info,
}

k8s_func = {
    "create": k8s_create_svc,
    # "get": k8s_get_svc,
    "delete": k8s_delete_svc,
}


def k8s_svc(action, alert_admins=False, raise_exception=True, **kwargs):
    log_extra = copy.deepcopy(kwargs)
    log.debug(f"Call K8s API to {action} svc ...", extra=log_extra)
    try:
        response = k8s_func[action](**kwargs)
    except Exception as e:
        alert_admins_log[alert_admins](
            f"Call K8s API to {action} svc failed", exc_info=True, extra=log_extra
        )
        if raise_exception:
            raise TunnelExceptionError(f"Call K8s API to {action} svc failed", str(e))
    else:
        k8s_log[action](f"Call K8s API to {action} svc done", extra=log_extra)


def start_remote_from_config_file(verbose=False):
    kwargs = {"uuidcode": "PeriodicCheck"}
    config_file_path = os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config")
    while True:
        try:
            with open(config_file_path, "r") as f:
                config_file = f.read().split("\n")
        except:
            log.critical(
                "PeriodicCheck - Could not load ssh config file during startup",
                exc_info=True,
                extra=kwargs,
            )
            return
        remote_prefix = "Host remote_"
        remote_hosts_lines = [
            x[len(remote_prefix) :] for x in config_file if x.startswith(remote_prefix)
        ]
        # kwargs["remote_hosts"] = remote_hosts_lines
        for _hostname in remote_hosts_lines:
            kwargs["hostname"] = _hostname
            try:
                start_remote(alert_admins=False, exc_info=False, timeout=1, **kwargs)
            except:
                # it's already logged as warning in start_remote
                if verbose:
                    log.exception(
                        f"PeriodicCheck - Could not start ssh remote tunnel (hostname={_hostname})",
                        extra=kwargs,
                    )
        time.sleep(30)


def check_all_k8s_services():
    all_k8s_tunnel_services = {}
    deployment_name = os.environ.get("DEPLOYMENT_NAME", "tunneling")
    try:
        v1 = k8s_get_client()
        all_k8s_services = v1.list_namespaced_service(namespace=k8s_get_svc_namespace())
        for svc in all_k8s_services.items:
            try:
                if svc.spec.selector.get("app", "None") == deployment_name:
                    name_as_list = svc.metadata.name.split("-")
                    jhub_userid = name_as_list[-1]
                    servicename = name_as_list[-2]
                    jhub = "-".join(name_as_list[:-2])
                    if jhub not in all_k8s_tunnel_services:
                        all_k8s_tunnel_services[jhub] = []
                    all_k8s_tunnel_services[jhub].append((servicename, jhub_userid))
            except:
                log.exception(f"PeriodicCheck - Could not check svc {svc}")
    except:
        log.exception("PeriodicCheck - Could not list services")
    return all_k8s_tunnel_services


def check_running_services():
    import os
    import requests
    import time

    from .models import TunnelModel

    jhub_cleanup_names = os.environ.get("JUPYTERHUB_CLEANUP_NAMES", "")
    jhub_cleanup_urls = os.environ.get("JUPYTERHUB_CLEANUP_URLS", "")
    jhub_cleanup_tokens = os.environ.get("JUPYTERHUB_CLEANUP_TOKENS", "")
    if jhub_cleanup_names and jhub_cleanup_urls and jhub_cleanup_tokens:
        log.info(
            f"PeriodicCheck - Env variables are all set. Start check every 30 seconds for {jhub_cleanup_names}."
        )
        jhub_cleanup_names = jhub_cleanup_names.split(";")
        jhub_cleanup_urls_list = jhub_cleanup_urls.split(";")
        jhub_cleanup_tokens_list = jhub_cleanup_tokens.split(";")
        while True:
            running_services_in_jhub = {}
            i = 0
            for jhub_cleanup_name in jhub_cleanup_names:
                # call request, check if it's running
                log.debug(f"PeriodicCheck - Call list servers {jhub_cleanup_name}.")
                try:
                    r = requests.get(
                        jhub_cleanup_urls_list[i],
                        headers={
                            "Authorization": f"token {jhub_cleanup_tokens_list[i]}",
                            "Accept": "application/json",
                        },
                    )
                    r.raise_for_status()
                    running_services_in_jhub[jhub_cleanup_name] = r.json()
                    log.debug(f"PeriodicCheck - {jhub_cleanup_name} result: {r.json()}")
                except:
                    log.exception("PeriodicCheck - Could not check running services")
                finally:
                    i += 1
            all_tunnels = TunnelModel.objects.all()
            log.debug(f"PeriodicCheck - Check for all tunnels: {all_tunnels}")
            for tunnel in all_tunnels:
                if tunnel.jhub_credential in running_services_in_jhub.keys():
                    log.debug(
                        f"PeriodicCheck - Tunnel jhub credential ( {tunnel.jhub_credential} ) is in list, check it"
                    )
                    if (
                        f"{tunnel.jhub_userid}_{tunnel.servername}"
                        not in running_services_in_jhub[tunnel.jhub_credential]
                    ):
                        log.info(
                            f"PeriodicCheck - {tunnel.servername} is no longer running at {tunnel.jhub_credential}. Stop it."
                        )
                        kwargs = {}
                        for key, value in tunnel.__dict__.items():
                            if key not in ["date", "_state"]:
                                kwargs[key] = copy.deepcopy(value)
                        stop_and_delete(
                            alert_admins=False, raise_exception=False, **kwargs
                        )
                    else:
                        log.debug(
                            f"PeriodicCheck - {tunnel.servername} is still running"
                        )
                else:
                    log.warning(
                        f"PeriodicCheck - {tunnel.jhub_credential} is not in running_services_list. Configure it in environment variables JUPYTERHUB_CLEANUP_NAMES, JUPYTERHUB_CLEANUP_URLS and JUPYTERHUB_CLEANUP_TOKENS to enabled internal cleanup feature."
                    )
            all_k8s_tunnel_services = check_all_k8s_services()
            for jhub, name_userids in all_k8s_tunnel_services.items():
                for name_userid in name_userids:
                    try:
                        tunnel = (
                            TunnelModel.objects.filter(jhub_credential=jhub)
                            .filter(servername=name_userid[0])
                            .filter(jhub_userid=name_userid[1])
                            .all()
                        )
                        if not tunnel:
                            log.info(
                                f"PeriodicCheck - Found unknown service {jhub}-{name_userid[0]}-{name_userid[1]} pointing to the tunneling service. Stop and delete it."
                            )
                            k8s_delete_svc(
                                name=f"{jhub}-{name_userid[0]}-{name_userid[1]}"
                            )
                    except:
                        log.exception(
                            f"PeriodicCheck - Could not delete unused svc {jhub}-{name_userid}"
                        )
            time.sleep(30)
    else:
        log.info(
            "PeriodicCheck - environment variables JUPYTERHUB_CLEANUP_NAMES, JUPYTERHUB_CLEANUP_URLS and JUPYTERHUB_CLEANUP_TOKENS not set. Do not run periodic cleanup check in background."
        )


def get_custom_headers(request_headers):
    if "headers" in request_headers.keys():
        ret = copy.deepcopy(request_headers["headers"])
        if "uuidcode" not in ret.keys():
            ret["uuidcode"] = uuid.uuid4().hex
        return ret
    custom_header_keys = {
        "HTTP_UUIDCODE": "uuidcode",
        "HTTP_HOSTNAME": "hostname",
        "HTTP_LABELS": "labels",
    }
    ret = {}
    for key, new_key in custom_header_keys.items():
        if key in request_headers.keys():
            ret[new_key] = request_headers[key]
    if "uuidcode" not in ret.keys():
        ret["uuidcode"] = uuid.uuid4().hex
    return ret
