import logging
import socket
import time

from django.urls import reverse

from ..models import TunnelModel
from common.logger import LOGGER_NAME


def netcat(host, port, content):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.sendall(content.encode())
        s.shutdown(socket.SHUT_WR)
        while True:
            data = s.recv(4096)
            if not data:
                break
        s.close()
    except:
        return False
    return True


from rest_framework.test import APITestCase


class CICDTests(APITestCase):
    # At the moment we run this tests, remote tunneling will never work.
    # So if it's returning 218 (as expected for not running), we're happy for now
    remote_data = {"hostname": "demo_site"}

    tunnel_data = {
        "backend_id": 5,
        "hostname": "demo_site",
        "target_node": "localhost",
        "target_port": 41582,
    }

    logger_config_stream = {
        "class": "logging.StreamHandler",
        "formatter": "simple",
        "level": 10,
        "stream": "ext://sys.stdout",
    }

    def setUp(self):
        url = reverse("handler-list")
        self.client.post(f"{url}stream/", data=self.logger_config_stream, format="json")
        return super().setUp()

    def test_create_remote(self):
        url = reverse("remote-list")
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertFalse(resp.data["running"])

    def test_status_remote(self):
        url = reverse("remote-list")
        resp = self.client.get(f"{url}demo_site/", format="json")
        self.assertEqual(resp.status_code, 200)

    def test_stop_remote(self):
        url = reverse("remote-list")
        resp = self.client.delete(f"{url}demo_site/", format="json")
        self.assertEqual(resp.status_code, 200)

    def test_remote_complete(self):
        url = reverse("remote-list")
        resp = self.client.post(url, data=self.remote_data, format="json")
        self.assertFalse(resp.data["running"])
        resp = self.client.get(f"{url}demo_site/", format="json")
        self.assertFalse(resp.data["running"])
        resp = self.client.delete(f"{url}demo_site/", format="json")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(f"{url}demo_site/", format="json")
        self.assertFalse(resp.data["running"])

    def test_create_tunnel(self):
        log = logging.getLogger(LOGGER_NAME)
        log.setLevel(10)
        url = reverse("tunnel-list")
        resp = self.client.post(url, data=self.tunnel_data, format="json")
        self.assertEqual(resp.status_code, 201)
        backend_id = int(resp.headers["Location"])
        models = TunnelModel.objects.all()
        for model in models:
            if model.backend_id == backend_id:
                local_port = model.local_port
        self.assertTrue(netcat("localhost", local_port, "test"))

    def test_stop_tunnel(self):
        url = reverse("tunnel-list")
        resp = self.client.post(url, data=self.tunnel_data, format="json")
        self.assertEqual(resp.status_code, 201)
        backend_id = int(resp.headers["Location"])
        models = TunnelModel.objects.all()
        for model in models:
            if model.backend_id == backend_id:
                local_port = model.local_port
        self.assertTrue(netcat("localhost", local_port, "test"))
        response_del = self.client.delete(url + f"{backend_id}/", format="json")
        self.assertEqual(response_del.status_code, 204)
        self.assertFalse(netcat("localhost", local_port, "test"))

    def test_get_tunnel(self):
        url = reverse("tunnel-list")
        resp = self.client.post(url, data=self.tunnel_data, format="json")
        self.assertEqual(resp.status_code, 201)
        backend_id = int(resp.headers["Location"])
        models = TunnelModel.objects.all()
        for model in models:
            if model.backend_id == backend_id:
                local_port = model.local_port
        self.assertTrue(netcat("localhost", local_port, "test"))
        resp_get = self.client.get(url + f"{backend_id}/", format="json")
        self.assertEqual(resp_get.status_code, 200)
        self.assertTrue(resp_get.data["running"])
        response_del = self.client.delete(url + f"{backend_id}/", format="json")
        self.assertEqual(response_del.status_code, 204)
        resp_get = self.client.get(url + f"{backend_id}/", format="json")
        self.assertEqual(resp_get.status_code, 404)
