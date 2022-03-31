import os
from unittest import mock

from django.urls import reverse
from tests.user_credentials import UserCredentials
from tunnel.models import TunnelModel

from .mocks import mocked_popen_init
from .mocks import mocked_popen_init_all_fail
from .mocks import mocked_popen_init_cancel_fail
from .mocks import mocked_popen_init_check_fail
from .mocks import mocked_popen_init_forward_fail
from .mocks import mocked_remote_popen_init
from .mocks import mocked_remote_popen_init_218
from .mocks import mocked_restart_popen_init


class TunnelViewTests(UserCredentials):
    tunnel_data = {
        "servername": "uuidcode",
        "hostname": "hostname",
        "svc_port": 8080,
        "target_node": "targetnode",
        "target_port": 34567,
    }

    expected_popen_args_tunnel_check = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-O",
        "check",
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_forward = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-O",
        "forward",
        f"tunnel_{tunnel_data['hostname']}",
        "-L",
    ]

    expected_popen_args_tunnel_forward_v = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-v",
        "-O",
        "forward",
        f"tunnel_{tunnel_data['hostname']}",
        "-L",
    ]

    expected_popen_args_tunnel_create = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_create_v = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-v",
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_cancel = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-O",
        "cancel",
        f"tunnel_{tunnel_data['hostname']}",
        "-L",
    ]

    expected_popen_args_tunnel_cancel_v = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "/home/tunnel/.ssh/config"),
        "-v",
        "-O",
        "cancel",
        f"tunnel_{tunnel_data['hostname']}",
        "-L",
    ]

    header = {"uuidcode": "uuidcode123"}

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_create_model_created(self, mocked_popen_init):
        url = reverse("tunnel-list")
        self.assertEqual(len(TunnelModel.objects.all()), 0)
        self.client.post(url, headers=self.header, data=self.tunnel_data, format="json")
        models = TunnelModel.objects.all()
        model = models[0]
        self.assertEqual(model.servername, self.tunnel_data["servername"])
        self.assertEqual(model.hostname, self.tunnel_data["hostname"])
        self.assertEqual(model.target_node, self.tunnel_data["target_node"])
        self.assertEqual(model.target_port, self.tunnel_data["target_port"])
        self.assertEqual(len(models), 1)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_create_popen_called(self, mocked_popen_init):
        url = reverse("tunnel-list")
        resp = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(resp.status_code, 201)

        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_all_fail,
    )
    def test_create_popen_called_all_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 500)

        # First check call when trying to start tunnel, then 3 create calls
        # Second check call when trying to stop tunnel
        # Both fail, so no further calls
        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )
        for i in range(1, 3):
            self.assertEqual(
                mocked_popen_init.call_args_list[i][0][0],
                self.expected_popen_args_tunnel_create,
            )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0],
            self.expected_popen_args_tunnel_create_v,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[4][0][0],
            self.expected_popen_args_tunnel_check,
        )
        for i in range(5, 7):
            self.assertEqual(
                mocked_popen_init.call_args_list[i][0][0],
                self.expected_popen_args_tunnel_create,
            )
        self.assertEqual(
            mocked_popen_init.call_args_list[7][0][0],
            self.expected_popen_args_tunnel_create_v,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_forward_fail,
    )
    def test_create_popen_called_forward_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 500)

        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1],
            self.expected_popen_args_tunnel_forward_v,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_check_fail,
    )
    def test_create_popen_called_check_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_cancel_popen_all_good(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        id = response.headers.get("Location", None)
        self.assertIsNotNone(id)
        response_del = self.client.delete(
            url + f"{id}/", headers=self.header, format="json"
        )
        self.assertEqual(response_del.status_code, 204)
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1],
            self.expected_popen_args_tunnel_cancel,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_cancel_fail,
    )
    def test_cancel_popen_cancel_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        id = response.headers.get("Location", None)
        self.assertIsNotNone(id)
        response_del = self.client.delete(
            url + f"{id}/", headers=self.header, format="json"
        )
        self.assertEqual(response_del.status_code, 204)
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1],
            self.expected_popen_args_tunnel_cancel,
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_retrieve_popen_all_good_not_running(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        id = response.headers.get("Location", None)
        self.assertIsNotNone(id)
        response_get = self.client.get(
            url + f"{id}/", headers=self.header, format="json"
        )
        self.assertEqual(response_get.status_code, 200)
        self.assertFalse(response_get.data["running"])

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_create_servername_already_exists(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            url, headers=self.header, data=self.tunnel_data, format="json"
        )
        self.assertEqual(response.status_code, 201)

        # Create first tunnel
        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
        )

        # Stop first tunnel
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1],
            self.expected_popen_args_tunnel_cancel,
        )

        # Create second tunnel
        self.assertEqual(
            mocked_popen_init.call_args_list[4][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[5][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
        )


class RemoteViewTests(UserCredentials):
    def setUp(self):
        return super().setUp()

    remote_data = {"hostname": "demo_site"}

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init,
    )
    def test_create_data_received(self, mocked_popen_init):
        url = "/api/remote/"
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertTrue("running" in resp.data.keys())

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init,
    )
    def test_retrieve_not_existing_running(self, mocked_popen_init):
        url = "/api/remote/"
        resp = self.client.get(url, headers=self.remote_data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["running"])

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init_218,
    )
    def test_retrieve_not_existing_not_running(self, mocked_popen_init):
        url = "/api/remote/"
        resp = self.client.get(url, headers=self.remote_data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["running"])

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init_218,
    )
    def test_stop_not_existing(self, mocked_popen_init):
        url = "/api/remote/"
        resp = self.client.delete(url, headers=self.remote_data, format="json")
        self.assertEqual(resp.status_code, 204)

    url = "/api/restart/"

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_restart_popen_init,
    )
    def test_restart_view(self, mocked_popen_init):
        data = {"hostname": "demo_hostname"}
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked_popen_init.call_count, 2)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_restart_popen_init,
    )
    def test_restart_view_missing_hostname(self, mocked_popen_init):
        data = {"no_hostname": "demo_hostname"}
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mocked_popen_init.call_count, 0)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_restart_popen_init,
    )
    def test_restart_view_existing_tunnels(self, mocked_popen_init):
        data = {"hostname": "demo_hostname"}
        tunnel_url = reverse("tunnel-list")
        tunnel_data = {
            "servername": "uuidcode",
            "hostname": data["hostname"],
            "svc_port": 8080,
            "target_node": "targetnode",
            "target_port": 34567,
        }
        tunnel_response = self.client.post(tunnel_url, data=tunnel_data, format="json")
        self.assertEqual(tunnel_response.status_code, 201)
        models = TunnelModel.objects.all()
        self.assertEqual(len(models), 1)
        response = self.client.post(self.url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        # 8 Calls expected
        # check/forward to create tunnel before (1-2)
        # check/cancel + check/forward for previously created tunnel (3-6)
        # remote_stop / remote_start (7-8)
        self.assertEqual(mocked_popen_init.call_count, 8)
