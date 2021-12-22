import copy
import json
import logging
import os
import socket
import subprocess

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
    expected_returncode=0,
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

    if returncode != expected_returncode:
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
    return returncode == expected_returncode


def check_tunnel_connection(func):
    def build_up_connection(*args, **kwargs):
        # check if ssh connection to the node is up
        if not run_popen_cmd(
            "tunnel", "check", "SSH tunnel check connection", **kwargs
        ):
            if not run_popen_cmd(
                "tunnel",
                "create",
                "SSH tunnel create connection",
                alert_admins=True,
                max_attempts=3,
                **kwargs,
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
    return run_popen_cmd(
        "tunnel",
        "forward",
        "SSH start tunnel",
        alert_admins=True,
        max_attempts=3,
        **kwargs,
    )


def start_remote(**kwargs):
    return run_popen_cmd(
        "remote",
        "start",
        "SSH start remote",
        alert_admins=True,
        max_attempts=3,
        expected_returncode=217,
        **kwargs,
    )


def status_remote(**kwargs):
    return run_popen_cmd(
        "remote",
        "status",
        "SSH status remote",
        alert_admins=False,
        max_attempts=1,
        expected_returncode=217,
        **kwargs,
    )


def stop_remote(**kwargs):
    run_popen_cmd(
        "remote",
        "stop",
        "SSH stop remote",
        alert_admins=True,
        max_attempts=3,
        expected_returncode=218,
        **kwargs,
    )
