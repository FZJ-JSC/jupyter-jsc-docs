import os
import socket
import time
from unittest import mock

from rest_framework.test import APITestCase
from tunnel import utils

from .mocks import mocked_popen_init
from .mocks import mocked_popen_init_all_fail
from .mocks import mocked_popen_init_cancel_fail
from .mocks import mocked_popen_init_check_fail


class TunnelUtilsTests(APITestCase):
    def test_is_port_in_use(self):
        port = utils.get_random_open_local_port()
        self.assertFalse(utils.is_port_in_use(port), "Port is in use")
        with socket.socket() as s:
            s.bind(("", port))
            s.listen(1)
            self.assertTrue(utils.is_port_in_use(port), "Port is not in use")

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_start_tunnel_all_good(self, mocked_popen_init):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        utils.start_tunnel(**kwargs)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{kwargs['hostname']}",
            "-L",
            f"0.0.0.0:{kwargs['local_port']}:{kwargs['target_node']}:{kwargs['target_port']}",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(mocked_popen_init.call_args_list[1][0][0], expected_args_2)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_check_fail,
    )
    def test_start_tunnel_check_255(self, mocked_popen_init_check_fail):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        utils.start_tunnel(**kwargs)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{kwargs['hostname']}",
            "-L",
            f"0.0.0.0:{kwargs['local_port']}:{kwargs['target_node']}:{kwargs['target_port']}",
        ]
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[0][0][0], expected_args_1
        )
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[1][0][0], expected_args_2
        )
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[2][0][0], expected_args_3
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_all_fail,
    )
    def test_start_tunnel_all_255(self, mocked_popen_init_all_fail):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        with self.assertRaises(Exception) as e:
            utils.start_tunnel(**kwargs)
        self.assertEqual(
            e.exception.args[0],
            "System not available: Could not connect via ssh to hostname",
        )
        self.assertEqual(mocked_popen_init_all_fail.call_count, 4)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_stop_tunnel_all_good(self, mocked_popen_init):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        utils.stop_tunnel(**kwargs)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "cancel",
            f"tunnel_{kwargs['hostname']}",
            "-L",
            f"0.0.0.0:{kwargs['local_port']}:{kwargs['target_node']}:{kwargs['target_port']}",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(mocked_popen_init.call_args_list[1][0][0], expected_args_2)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_check_fail,
    )
    def test_stop_tunnel_check_fail(self, mocked_popen_init_check_fail):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        utils.stop_tunnel(**kwargs)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            f"tunnel_{kwargs['hostname']}",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
            "-O",
            "cancel",
            f"tunnel_{kwargs['hostname']}",
            "-L",
            f"0.0.0.0:{kwargs['local_port']}:{kwargs['target_node']}:{kwargs['target_port']}",
        ]
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[0][0][0], expected_args_1
        )
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[1][0][0], expected_args_2
        )
        self.assertEqual(
            mocked_popen_init_check_fail.call_args_list[2][0][0], expected_args_3
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_all_fail,
    )
    def test_stop_tunnel_all_255(self, mocked_popen_init_all_fail):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        with self.assertRaises(Exception) as e:
            utils.stop_tunnel(**kwargs)
        self.assertEqual(
            e.exception.args[0],
            "System not available: Could not connect via ssh to hostname",
        )
        self.assertEqual(mocked_popen_init_all_fail.call_count, 4)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_cancel_fail,
    )
    def test_stop_tunnel_cancel_fail(self, mocked_popen_init_cancel_fail):
        kwargs = {
            "uuidcode": "uuidcode",
            "hostname": "hostname",
            "local_port": 56789,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        utils.stop_tunnel(raise_exception=False, **kwargs)
        self.assertEqual(mocked_popen_init_cancel_fail.call_count, 2)
