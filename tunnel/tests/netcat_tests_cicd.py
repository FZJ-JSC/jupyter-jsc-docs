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
    full_data = {
        "backend_id": 5,
        "hostname": "demo_site",
        "target_node": "localhost",
        "target_port": 41582,
    }

    def test_create_tunnel(self):
        log = logging.getLogger(LOGGER_NAME)
        log.setLevel(10)
        url = reverse("tunnel-list")
        resp = self.client.post(url, data=self.full_data, format="json")
        self.assertEqual(resp.status_code, 201)
        backend_id = int(resp.headers["Location"])
        models = TunnelModel.objects.all()
        print(backend_id)
        print(models)
        for model in models:
            print(f"Compare: {model.backend_id} - {backend_id}")
            if model.backend_id == backend_id:
                print("Define local_port")
                local_port = model.local_port
        # print("Sleep 10")
        # time.sleep(10)
        self.assertTrue(netcat("localhost", local_port, "test"))

    # def test_stop_tunnel(self):
    #     url = reverse("tunnel-list")
    #     resp = self.client.post(url, data=self.full_data, format="json")
    #     self.assertEqual(resp.status_code, 201)
    #     backend_id = resp.headers["Location"]
    #     models = TunnelModel.objects.all()
    #     for model in models:
    #         if model.backend_id == backend_id:
    #             local_port = model.local_port
    #     self.assertTrue(netcat("localhost", local_port, "test"))
    #     response_del = self.client.delete(url+f"{backend_id}/", format="json")
    #     self.assertEqual(response_del.status_code, 204)
    #     self.assertFalse(netcat("localhost", local_port, "test"))

    # def test_get_tunnel(self):
    #     url = reverse("tunnel-list")
    #     resp = self.client.post(url, data=self.full_data, format="json")
    #     self.assertEqual(resp.status_code, 201)
    #     backend_id = resp.headers["Location"]
    #     models = TunnelModel.objects.all()
    #     for model in models:
    #         if model.backend_id == backend_id:
    #             local_port = model.local_port
    #     self.assertTrue(netcat("localhost", local_port, "test"))
    #     resp_get = self.client.get(url+f"{backend_id}/", format="json")
    #     self.assertEqual(resp_get.status_code, 200)
    #     self.assertTrue(resp_get.data["running"])
    #     response_del = self.client.delete(url+f"{backend_id}/", format="json")
    #     self.assertEqual(response_del.status_code, 204)
    #     resp_get = self.client.get(url+f"{backend_id}/", format="json")
    #     self.assertEqual(resp_get.status_code, 404)
