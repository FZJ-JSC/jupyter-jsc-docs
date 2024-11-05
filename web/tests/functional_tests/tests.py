import copy
import json
import os
import unittest

import requests
from kubernetes import client
from kubernetes.config import load_kube_config
from parameterized import parameterized


class FunctionalTests(unittest.TestCase):
    namespace = ""
    tunnel_url = ""
    tunnel_pod = ""
    unicore_url = ""
    unicore_pod = ""
    v1 = None

    headers = {
        "Content-Type": "application/json",
        "Authorization": os.environ.get("TUNNEL_JHUB_BASIC", ""),
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
        logs1, logs2 = self.logtest_stream()

    @parameterized.expand(
        [
            ("stream", "simple"),
            ("stream", "json"),
        ]
    )
    def test_stream_handler(self, handler, formatter):
        handler_url = f"{self.tunnel_url}api/logs/handler/"
        stream_url = f"{self.tunnel_url}api/logs/handler/stream/"
        logtest_url = f"{self.tunnel_url}api/logs/logtest/"
        # Check that something's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])

        # Update Stream handler
        body = {"handler": handler, "configuration": {"formatter": formatter}}
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)

        # Test Stream handler
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 6, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-5].endswith("function=list : Info"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-5])["Message"], "Info")

        # # Test mix_extra in formatter
        if formatter == "simple":
            self.assertTrue(
                logs_2[-2].endswith(
                    "function=list : Critical --- Extra1=message1 --- mesg=msg1"
                )
            )
        elif formatter == "json":
            tmp = json.loads(logs_2[-2])
            self.assertEqual(tmp["Message"], "Critical")
            self.assertEqual(tmp["Extra1"], "message1")
            self.assertEqual(tmp["mesg"], "msg1")

        # Update Stream handler Loglevel with PATCH
        body = {"handler": "stream", "configuration": {"level": 5}}
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with TRACE
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 8, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-7].endswith("function=list : Trace"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-7])["Message"], "Trace")

        # Second partial update should not change loglevel
        swap_formatter = {"simple": "json", "json": "simple"}
        body = {
            "handler": "stream",
            "configuration": {"formatter": swap_formatter[formatter]},
        }
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with TRACE
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 8, len(logs_2))
        if swap_formatter[formatter] == "simple":
            self.assertTrue(logs_2[-7].endswith("function=list : Trace"))
        elif swap_formatter[formatter] == "json":
            self.assertEqual(json.loads(logs_2[-7])["Message"], "Trace")

        # Update LogLevel to DEACTIVATE
        body["configuration"]["level"] = "DEACTIVATE"
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)

        # Test Stream handler with DEACTIVATE
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 1, len(logs_2))

        # Delete handler
        r = requests.delete(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 204)
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)

        # Check that nothing's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.headers)
        self.assertEqual(r.json(), [])

        # Test stdout with no handler defined
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 4, len(logs_2))
        self.assertEqual(logs_2[-4:-1], ["Warn", "Error", "Critical"])

        # Add Stream handler
        body = {"handler": handler}
        r = requests.post(url=handler_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 201)
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)

        # Check that something's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])
