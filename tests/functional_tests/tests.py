import copy
import json
import os
import unittest

import requests
from kubernetes import client
from parameterized import parameterized
from utils import check_if_port_is_listening
from utils import delete_tunneling_pod_and_svcs
from utils import delete_unicore_pod_and_svcs
from utils import load_env
from utils import load_k8s_client
from utils import prepare_tunneling_pod
from utils import start_tunneling_pod_and_svcs
from utils import start_unicore_pod_and_svcs
from utils import wait_for_tunneling_svc
from utils import wait_for_unicore_svc


class FunctionalTests(unittest.TestCase):
    suffix = None
    image = None
    v1 = None
    name = None
    unicore_name = None
    namespace = None
    k8s_host = None
    k8s_user_token = None
    k8s_ca_auth_path = None
    remote_tunnel_port_at_unicore = 56789

    v1 = None
    url = None
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {os.environ.get('TUNNEL_SUPERUSER_PASS_B64', '')}",
    }

    def setUp(self):
        (
            self.suffix,
            self.name,
            self.namespace,
            self.image,
            self.k8s_host,
            self.k8s_user_token,
            self.k8s_ca_auth_path,
            self.url,
        ) = load_env()
        self.v1 = load_k8s_client(
            self.k8s_host, self.k8s_user_token, self.k8s_ca_auth_path
        )
        self.unicore_name = f"unicore-server-{self.suffix}"
        return super().setUp()

    @classmethod
    def setUpClass(cls):
        (
            suffix,
            name,
            namespace,
            image,
            k8s_host,
            k8s_user_token,
            k8s_ca_auth_path,
            url,
        ) = load_env()
        v1 = load_k8s_client(k8s_host, k8s_user_token, k8s_ca_auth_path)
        unicore_version = os.environ.get("UNICORE_SERVER_VERSION")
        unicore_image = f"registry.jsc.fz-juelich.de/jupyterjsc/k8s/images/unicore-test-server/unicore-server:{unicore_version}"
        unicore_name = f"unicore-server-{suffix}"
        start_unicore_pod_and_svcs(
            v1, unicore_name, namespace, unicore_image, f"{name}-ssh"
        )
        start_tunneling_pod_and_svcs(v1, name, namespace, image)
        prepare_tunneling_pod(v1, name, namespace, unicore_name)
        wait_for_tunneling_svc(url)
        wait_for_unicore_svc(v1, unicore_name, namespace)

    @classmethod
    def tearDownClass(cls):
        (
            suffix,
            name,
            namespace,
            image,
            k8s_host,
            k8s_user_token,
            k8s_ca_auth_path,
            url,
        ) = load_env()
        v1 = load_k8s_client(k8s_host, k8s_user_token, k8s_ca_auth_path)
        delete_tunneling_pod_and_svcs(v1, name, namespace)
        unicore_name = f"unicore-server-{suffix}"
        delete_unicore_pod_and_svcs(v1, unicore_name, namespace)

        # Delete pre-tunnel / pre-remote pods and svcs, if test failed it's still running
        try:
            delete_tunneling_pod_and_svcs(v1, f"{name}-pre-tunnel", namespace)
        except:
            pass
        try:
            v1.delete_namespaced_service(name=f"{name}-5", namespace=namespace)
        except:
            pass
        try:
            v1.delete_namespaced_service(name=f"{name}-6", namespace=namespace)
        except:
            pass
        try:
            delete_tunneling_pod_and_svcs(v1, f"{name}-pre-remote", namespace)
        except:
            pass

    def logtest_stream(self):
        logtest_url = f"{self.url}/logs/logtest/"
        logs_1 = (
            self.v1.read_namespaced_pod_log(name=self.name, namespace=self.namespace)
            .strip()
            .split("\n")
        )
        r = requests.get(url=logtest_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.url)
        logs_2 = (
            self.v1.read_namespaced_pod_log(name=self.name, namespace=self.namespace)
            .strip()
            .split("\n")
        )
        return logs_1, logs_2

    def test_health(self):
        r = requests.get(url=f"{self.url}/health/", headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.url)

    configurations = {
        "stream": {
            "handler": "stream",
            "configuration": {
                "formatter": "simple",
                "level": 10,
                "stream": "ext://sys.stdout",
            },
        },
        "file": {
            "handler": "file",
            "configuration": {
                "formatter": "json",
                "level": 10,
                "stream": "ext://sys.stdout",
            },
        },
    }

    @parameterized.expand(
        [
            ("stream", "simple"),
            ("stream", "json"),
        ]
    )
    def test_stream_handler(self, handler, formatter):
        handler_url = f"{self.url}/logs/handler/"
        stream_url = f"{self.url}/logs/handler/stream/"
        body = copy.deepcopy(self.configurations[handler])
        body["configuration"]["formatter"] = formatter

        # Check that nothing's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200, self.headers)
        self.assertEqual(r.json(), [])

        # Test stdout with no handler defined
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 4, len(logs_2))
        self.assertEqual(logs_2[-4:-1], ["Warn", "Error", "Critical"])

        # Add Stream handler
        r = requests.post(url=handler_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 201)

        # Check that something's defined
        r = requests.get(url=handler_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])
        r = requests.get(url=stream_url, headers=self.headers, timeout=2)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), {})

        # Test Stream handler
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 6, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-6].endswith("function=list : Debug"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-6])["Message"], "Debug")

        # Test mix_extra in formatter
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

        # Update Stream handler Loglevel with POST
        body["configuration"]["level"] = 5
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with TRACE
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 7, len(logs_2))
        if formatter == "simple":
            self.assertTrue(logs_2[-7].endswith("function=list : Trace"))
        elif formatter == "json":
            self.assertEqual(json.loads(logs_2[-7])["Message"], "Trace")

        # Update LogLevel to DEACTIVATE
        body["configuration"]["level"] = "DEACTIVATE"
        r = requests.patch(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # Test Stream handler with DEACTIVATE
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 1, len(logs_2))

        # Delete handler
        r = requests.delete(url=stream_url, json=body, headers=self.headers)
        self.assertEqual(r.status_code, 204)

        # Test stdout with no handler defined
        logs_1, logs_2 = self.logtest_stream()
        self.assertEqual(len(logs_1) + 4, len(logs_2))
        self.assertEqual(logs_2[-4:-1], ["Warn", "Error", "Critical"])

    def test_remote_tunnel(self):
        # Get status of ssh remote tunnel
        remote_url = f"{self.url}/remote/"
        demo_site_url = f"{remote_url}demo_site/"
        r = requests.get(url=remote_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

        # Start remote tunnel
        body = {"hostname": "demo_site"}
        r = requests.post(url=remote_url, headers=self.headers, json=body)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"running": True})

        # list all remote tunnel
        r = requests.get(url=remote_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])

        # retrieve demo site remote tunnel
        r = requests.get(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"running": True})

        # Check if something is listening on port 56789
        listening_at_unicore = check_if_port_is_listening(
            self.v1,
            self.unicore_name,
            self.namespace,
            self.remote_tunnel_port_at_unicore,
        )
        self.assertTrue(listening_at_unicore)

        # delete demo site remote tunnel
        r = requests.delete(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # retrieve demo site remote tunnel
        r = requests.get(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"running": False})

        # Check that nothing is listening on port 56789
        listening_at_unicore = check_if_port_is_listening(
            self.v1,
            self.unicore_name,
            self.namespace,
            self.remote_tunnel_port_at_unicore,
        )
        self.assertFalse(listening_at_unicore)

        # Remote Tunnel connection and db entry will stay (intended behaviour)
        r = requests.get(url=remote_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])

    def delete_tunnel(self, tunnel_url, backend_id, local_port):
        tunnel_i_url = f"{tunnel_url}{backend_id}/"
        # Delete tunnels
        r = requests.delete(tunnel_i_url, headers=self.headers)
        self.assertEqual(r.status_code, 204)

        # try to retrieve information again
        r = requests.get(tunnel_i_url, headers=self.headers)
        self.assertEqual(r.status_code, 404)
        is_listening = check_if_port_is_listening(
            self.v1, self.name, self.namespace, local_port
        )
        self.assertFalse(is_listening)
        with self.assertRaises(client.exceptions.ApiException) as context:
            svc = self.v1.read_namespaced_service(
                name=f"{self.name}-{backend_id}", namespace=self.namespace
            ).to_dict()

    def test_tunnel(self):
        def check_post_resp(resp_data, tunnel_data):
            self.assertEqual(resp_data["backend_id"], tunnel_data["backend_id"])
            self.assertEqual(resp_data["hostname"], tunnel_data["hostname"])
            self.assertEqual(resp_data["target_node"], tunnel_data["target_node"])
            self.assertEqual(resp_data["target_port"], tunnel_data["target_port"])
            self.assertEqual(type(resp_data["local_port"]), int)

        tunnel_url = f"{self.url}/tunnel/"

        # Verify that nothing's running
        r = requests.get(tunnel_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

        # Start tunnel
        tunnel_data = {
            "backend_id": 5,
            "hostname": "demo_site",
            "target_node": "targetnode",
            "target_port": 34567,
        }
        r = requests.post(tunnel_url, headers=self.headers, json=tunnel_data)
        self.assertEqual(r.status_code, 201)
        resp_post = r.json()
        check_post_resp(resp_post, tunnel_data)

        # If it does not exists, an exception is thrown
        svc_1 = self.v1.read_namespaced_service(
            name=f"{self.name}-{tunnel_data['backend_id']}", namespace=self.namespace
        ).to_dict()
        self.assertEqual(svc_1["spec"]["ports"][0]["port"], resp_post["local_port"])

        # Verify that something's running
        r = requests.get(tunnel_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        resp_get = r.json()
        self.assertNotEqual(resp_get, [])
        self.assertEqual(resp_get[0], resp_post)
        is_listening = check_if_port_is_listening(
            self.v1, self.name, self.namespace, resp_post["local_port"]
        )
        self.assertTrue(is_listening)

        # Try to start another one for the same backend_id.
        # Expected behaviour: Delete previous tunnel, start new one
        r = requests.post(tunnel_url, headers=self.headers, json=tunnel_data)
        self.assertEqual(r.status_code, 201)
        resp_post_2 = r.json()
        check_post_resp(resp_post_2, tunnel_data)

        # Verify that new tunnel config's running
        r = requests.get(tunnel_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        resp_get = r.json()
        self.assertNotEqual(resp_get, [])
        self.assertEqual(resp_get[0], resp_post_2)
        is_listening_1 = check_if_port_is_listening(
            self.v1, self.name, self.namespace, resp_post["local_port"]
        )
        is_listening_2 = check_if_port_is_listening(
            self.v1, self.name, self.namespace, resp_post_2["local_port"]
        )
        self.assertFalse(is_listening_1)
        self.assertTrue(is_listening_2)

        # If it does not exists, an exception is thrown
        svc_2 = self.v1.read_namespaced_service(
            name=f"{self.name}-{tunnel_data['backend_id']}", namespace=self.namespace
        ).to_dict()
        self.assertEqual(svc_2["spec"]["ports"][0]["port"], resp_post_2["local_port"])

        # Start a second tunnel
        tunnel_data["backend_id"] = 6
        tunnel_data["target_port"] = 34568
        tunnel_data["target_node"] = "targetnode2"
        r = requests.post(tunnel_url, headers=self.headers, json=tunnel_data)
        self.assertEqual(r.status_code, 201)
        resp_post_3 = r.json()
        check_post_resp(resp_post_3, tunnel_data)

        # If it does not exists, an exception is thrown
        svc_2 = self.v1.read_namespaced_service(
            name=f"{self.name}-{resp_post_2['backend_id']}", namespace=self.namespace
        ).to_dict()
        svc_3 = self.v1.read_namespaced_service(
            name=f"{self.name}-{tunnel_data['backend_id']}", namespace=self.namespace
        ).to_dict()
        self.assertEqual(svc_2["spec"]["ports"][0]["port"], resp_post_2["local_port"])
        self.assertEqual(svc_3["spec"]["ports"][0]["port"], resp_post_3["local_port"])

        # Verify that both are running
        r = requests.get(tunnel_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        resp_get = r.json()
        self.assertNotEqual(resp_get, [])
        self.assertEqual(resp_get[0], resp_post_2)
        self.assertEqual(resp_get[1], resp_post_3)
        is_listening_2 = check_if_port_is_listening(
            self.v1, self.name, self.namespace, resp_post_2["local_port"]
        )
        is_listening_3 = check_if_port_is_listening(
            self.v1, self.name, self.namespace, resp_post_3["local_port"]
        )
        self.assertTrue(is_listening_2)
        self.assertTrue(is_listening_3)

        # Retrieve information about a tunnel
        r = requests.get(f"{tunnel_url}5/", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"running": True})

        # Delete tunnels
        self.delete_tunnel(tunnel_url, 5, resp_post_2["local_port"])
        self.delete_tunnel(tunnel_url, 6, resp_post_3["local_port"])

    def test_tunnel_with_preexisting_tunnels_in_db(self):
        name = f"{self.name}-pre-tunnel"
        url = f"http://{name}:8080/api"
        tunnel_url = f"{url}/tunnel/"
        resp_post_2 = {
            "backend_id": 5,
            "hostname": "demo_site",
            "target_node": "targetnode",
            "target_port": 34567,
            "local_port": 51759,
        }
        resp_post_3 = {
            "backend_id": 6,
            "hostname": "demo_site",
            "target_node": "targetnode2",
            "target_port": 34568,
            "local_port": 57907,
        }

        # Start tunnel service with prefilled database
        additional_envs = [
            {
                "name": "SQL_DATABASE",
                "value": "tests/functional_tests/db.sqlite3.two_running_tunnels",
            },
            {"name": "DELAYED_START_IN_SEC", "value": "15"},
        ]

        start_tunneling_pod_and_svcs(
            self.v1, name, self.namespace, self.image, additional_envs=additional_envs
        )
        prepare_tunneling_pod(self.v1, name, self.namespace, self.unicore_name)
        wait_for_tunneling_svc(url)

        # Check if logs are shown
        logs = self.v1.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        ).strip()
        self.assertIn("Start db-tunnels --- uuidcode=StartUp", logs)

        # Verify that both predefined tunnels are running
        r = requests.get(tunnel_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        resp_get = r.json()
        self.assertNotEqual(resp_get, [])
        self.assertEqual(resp_get[0], resp_post_2)
        self.assertEqual(resp_get[1], resp_post_3)
        is_listening_2 = check_if_port_is_listening(
            self.v1, name, self.namespace, resp_post_2["local_port"]
        )
        is_listening_3 = check_if_port_is_listening(
            self.v1, name, self.namespace, resp_post_3["local_port"]
        )
        self.assertTrue(is_listening_2)
        self.assertTrue(is_listening_3)

        # If it does not exists, an exception is thrown
        svc_2 = self.v1.read_namespaced_service(
            name=f"{name}-{resp_post_2['backend_id']}", namespace=self.namespace
        ).to_dict()
        svc_3 = self.v1.read_namespaced_service(
            name=f"{name}-{resp_post_3['backend_id']}", namespace=self.namespace
        ).to_dict()
        self.assertEqual(svc_2["spec"]["ports"][0]["port"], resp_post_2["local_port"])
        self.assertEqual(svc_3["spec"]["ports"][0]["port"], resp_post_3["local_port"])

        # tearDown
        delete_tunneling_pod_and_svcs(self.v1, name, self.namespace)
        self.v1.delete_namespaced_service(
            name=f"{name}-{resp_post_2['backend_id']}", namespace=self.namespace
        )
        self.v1.delete_namespaced_service(
            name=f"{name}-{resp_post_3['backend_id']}", namespace=self.namespace
        )

    def test_remote_with_preexisting_db_entry(self):
        name = f"{self.name}-pre-remote"
        url = f"http://{name}:8080/api"
        remote_url = f"{url}/remote/"
        demo_site_url = f"{remote_url}demo_site"

        # Check that nothing is listening on port 56789
        listening_at_unicore = check_if_port_is_listening(
            self.v1,
            self.unicore_name,
            self.namespace,
            self.remote_tunnel_port_at_unicore,
        )
        self.assertFalse(listening_at_unicore)

        # Start tunnel service with prefilled database
        additional_envs = [
            {
                "name": "SQL_DATABASE",
                "value": "tests/functional_tests/db.sqlite3.one_running_remote",
            },
            {"name": "DELAYED_START_IN_SEC", "value": "15"},
        ]

        start_tunneling_pod_and_svcs(
            self.v1, name, self.namespace, self.image, additional_envs=additional_envs
        )
        prepare_tunneling_pod(self.v1, name, self.namespace, self.unicore_name)
        wait_for_tunneling_svc(url)

        # Check if logs are shown
        logs = self.v1.read_namespaced_pod_log(
            name=name, namespace=self.namespace
        ).strip()
        self.assertIn("Start db-remote-tunnels --- uuidcode=StartUp", logs)

        # list all remote tunnel
        r = requests.get(url=remote_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.json(), [])

        # retrieve demo site remote tunnel
        r = requests.get(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"running": True})

        # Check if something is listening on port 56789
        listening_at_unicore = check_if_port_is_listening(
            self.v1,
            self.unicore_name,
            self.namespace,
            self.remote_tunnel_port_at_unicore,
        )
        self.assertTrue(listening_at_unicore)

        # delete demo site remote tunnel
        r = requests.delete(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)

        # retrieve demo site remote tunnel
        r = requests.get(url=demo_site_url, headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"running": False})

        # Check that nothing is listening on port 56789
        listening_at_unicore = check_if_port_is_listening(
            self.v1,
            self.unicore_name,
            self.namespace,
            self.remote_tunnel_port_at_unicore,
        )
        self.assertFalse(listening_at_unicore)

        delete_tunneling_pod_and_svcs(self.v1, name, self.namespace)
