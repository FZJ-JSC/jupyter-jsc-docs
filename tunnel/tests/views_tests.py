import os
from unittest import mock

from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import RemoteModel
from ..models import TunnelModel
from .mocks import mocked_popen_init
from .mocks import mocked_popen_init_all_fail
from .mocks import mocked_popen_init_cancel_fail
from .mocks import mocked_popen_init_check_fail
from .mocks import mocked_popen_init_forward_fail
from .mocks import mocked_remote_popen_init
from .mocks import mocked_remote_popen_init_218


class RemoteViewTests(APITestCase):
    remote_data = {"hostname": "demo_site"}

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init,
    )
    def test_create_data_received(self, mocked_popen_init):
        url = reverse("remote-list")
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertTrue("running" in resp.data.keys())

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init,
    )
    def test_create_model_created(self, mocked_popen_init):
        url = reverse("remote-list")
        self.assertEqual(len(RemoteModel.objects.all()), 0)
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertEqual(resp.status_code, 201)
        models = RemoteModel.objects.all()
        model = models[0]
        self.assertEqual(model.hostname, self.remote_data["hostname"])
        self.assertTrue(model.running)
        self.assertEqual(len(models), 1)
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(model.hostname, self.remote_data["hostname"])
        self.assertTrue(model.running)
        self.assertEqual(len(models), 1)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init,
    )
    def test_retrieve_not_existing_running(self, mocked_popen_init):
        url = reverse("remote-list")
        url = f"{url}demo_site/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["running"])

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init_218,
    )
    def test_retrieve_not_existing_not_running(self, mocked_popen_init):
        url = reverse("remote-list")
        url = f"{url}demo_site/"
        resp = self.client.get(url, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["running"])

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_remote_popen_init_218,
    )
    def test_stop_not_existing(self, mocked_popen_init):
        url = reverse("remote-list")
        url = f"{url}demo_site/"
        resp = self.client.delete(url, format="json")
        self.assertEqual(resp.status_code, 200)


class TunnelViewTests(APITestCase):
    tunnel_data = {
        "backend_id": 5,
        "hostname": "hostname",
        "target_node": "targetnode",
        "target_port": 34567,
    }

    expected_popen_args_tunnel_check = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
        "-O",
        "check",
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_forward = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
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
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
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
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_create_v = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
        "-v",
        f"tunnel_{tunnel_data['hostname']}",
    ]

    expected_popen_args_tunnel_cancel = [
        "timeout",
        "3",
        "ssh",
        "-F",
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
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
        os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
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
        self.assertEqual(model.backend_id, self.tunnel_data["backend_id"])
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
        self.assertEqual(response.status_code, 550)

        self.assertEqual(
            mocked_popen_init.call_args_list[0][0][0],
            self.expected_popen_args_tunnel_check,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0],
            self.expected_popen_args_tunnel_create,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0],
            self.expected_popen_args_tunnel_create,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0],
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
        self.assertEqual(response.status_code, 551)

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
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0],
            self.expected_popen_args_tunnel_create,
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0][:-1],
            self.expected_popen_args_tunnel_forward,
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
        self.assertEqual(
            mocked_popen_init.call_args_list[4][0][0][:-1],
            self.expected_popen_args_tunnel_cancel_v,
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
    def test_create_backend_id_already_exists(self, mocked_popen_init):
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
