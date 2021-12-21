import os
from unittest import mock

from django.urls import reverse
from rest_framework.test import APITestCase

from ..models import TunnelModel
from .mocks import mocked_popen_init
from .mocks import mocked_popen_init_all_fail
from .mocks import mocked_popen_init_cancel_fail
from .mocks import mocked_popen_init_check_fail
from .mocks import mocked_popen_init_forward_fail


class TunnelViewSets(APITestCase):
    full_data = {
        "backend_id": 5,
        "hostname": "hostname",
        "target_node": "targetnode",
        "target_port": 34567,
    }

    header = {"uuidcode": "uuidcode123"}

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_create_model_created(self, mocked_popen_init):
        url = reverse("tunnel-list")
        self.assertEqual(len(TunnelModel.objects.all()), 0)
        self.client.post(url, headers=self.header, data=self.full_data, format="json")
        models = TunnelModel.objects.all()
        model = models[0]
        self.assertEqual(model.backend_id, self.full_data["backend_id"])
        self.assertEqual(model.hostname, self.full_data["hostname"])
        self.assertEqual(model.target_node, self.full_data["target_node"])
        self.assertEqual(model.target_port, self.full_data["target_port"])
        self.assertEqual(len(models), 1)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_create_popen_called(self, mocked_popen_init):
        url = reverse("tunnel-list")
        resp = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1], expected_args_2
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_all_fail,
    )
    def test_create_popen_called_all_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 550)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_4 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-v",
            f"tunnel_{self.full_data['hostname']}",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(mocked_popen_init.call_args_list[1][0][0], expected_args_2)
        self.assertEqual(mocked_popen_init.call_args_list[2][0][0], expected_args_3)
        self.assertEqual(mocked_popen_init.call_args_list[3][0][0], expected_args_4)

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_forward_fail,
    )
    def test_create_popen_called_forward_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 551)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        expected_args_4 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        expected_args_5 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-v",
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1], expected_args_3
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0][:-1], expected_args_4
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1], expected_args_5
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_check_fail,
    )
    def test_create_popen_called_check_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(mocked_popen_init.call_args_list[1][0][0], expected_args_2)
        self.assertEqual(
            mocked_popen_init.call_args_list[2][0][0][:-1], expected_args_3
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_cancel_popen_all_good(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        id = response.headers.get("Location", None)
        self.assertIsNotNone(id)
        response_del = self.client.delete(
            url + f"{id}/", headers=self.header, format="json"
        )
        self.assertEqual(response_del.status_code, 204)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "cancel",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[2][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1], expected_args_2
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init_cancel_fail,
    )
    def test_cancel_popen_cancel_fail(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        id = response.headers.get("Location", None)
        self.assertIsNotNone(id)
        response_del = self.client.delete(
            url + f"{id}/", headers=self.header, format="json"
        )
        self.assertEqual(response_del.status_code, 204)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "cancel",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-v",
            "-O",
            "cancel",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        self.assertEqual(mocked_popen_init.call_args_list[2][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1], expected_args_2
        )
        self.assertEqual(
            mocked_popen_init.call_args_list[4][0][0][:-1], expected_args_3
        )

    @mock.patch(
        "tunnel.utils.subprocess.Popen",
        side_effect=mocked_popen_init,
    )
    def test_retrieve_popen_all_good_not_running(self, mocked_popen_init):
        url = reverse("tunnel-list")
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
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
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            url, headers=self.header, data=self.full_data, format="json"
        )
        self.assertEqual(response.status_code, 201)
        expected_args_1 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "check",
            f"tunnel_{self.full_data['hostname']}",
        ]
        expected_args_2 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "forward",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]
        expected_args_3 = [
            "timeout",
            "3",
            "ssh",
            "-F",
            os.environ.get("SSHCONFIGFILE", "~/.ssh/config"),
            "-O",
            "cancel",
            f"tunnel_{self.full_data['hostname']}",
            "-L",
        ]

        # Create first tunnel
        self.assertEqual(mocked_popen_init.call_args_list[0][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[1][0][0][:-1], expected_args_2
        )

        # Stop first tunnel
        self.assertEqual(mocked_popen_init.call_args_list[2][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[3][0][0][:-1], expected_args_3
        )

        # Create second tunnel
        self.assertEqual(mocked_popen_init.call_args_list[4][0][0], expected_args_1)
        self.assertEqual(
            mocked_popen_init.call_args_list[5][0][0][:-1], expected_args_2
        )
