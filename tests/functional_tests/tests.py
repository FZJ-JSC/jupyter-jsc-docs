import os
import unittest

import requests
from kubernetes import client
from kubernetes.config import load_kube_config


class FunctionalTests(unittest.TestCase):
    namespace = ""
    tunnel_url = ""
    tunnel_pod = ""
    unicore_url = ""
    unicore_pod = ""
    v1 = None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {os.environ.get('TUNNEL_JHUB_BASIC', '')}",
    }

    def setUp(self):
        self.namespace = os.environ.get("NAMESPACE")
        self.tunnel_url = os.environ.get("TUNNEL_URL")
        self.tunnel_pod = os.environ.get("TUNNEL_POD")
        self.unicore_url = os.environ.get("UNICORE_URL")
        self.unicore_pod = os.environ.get("UNICORE_POD")
        load_kube_config()
        self.v1 = client.CoreV1Api()
        return super().setUp()

    def logtest_stream(self):
        logtest_url = f"{self.tunnel_url}api/logs/logtest/"
        logs_1 = (
            self.v1.read_namespaced_pod_log(
                name=self.tunnel_pod, namespace=self.namespace
            )
            .strip()
            .split("\n")
        )
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)
        self.assertNotEqual(r.status_code, 401, self.headers)
        self.assertEqual(r.status_code, 200, logtest_url)
        logs_2 = (
            self.v1.read_namespaced_pod_log(
                name=self.tunnel_pod, namespace=self.namespace
            )
            .strip()
            .split("\n")
        )
        return logs_1, logs_2

    def test(self):
        self.logtest_stream()
