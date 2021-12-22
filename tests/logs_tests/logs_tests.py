import copy
import logging

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from jupyterjsc_tunneling.settings import LOGGER_NAME


class LogsUnitTest(APITestCase):
    user_unauthorized_username = "unauthorized"
    user_authorized_username = "authorized"
    user_authorized = None
    user_unauthorized = None
    user_password = "12345"
    authorized_group_jobs = "access_to_logging"
    credentials_authorized = {}
    credentials_unauthorized = {}
    header = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    def create_user(self, username, passwd):
        user = User.objects.create(username=username)
        user.set_password(passwd)
        user.save()
        user.auth_token = Token.objects.create(user=user)
        return user

    def setUp(self):
        self.user_authorized = self.create_user(
            self.user_authorized_username, self.user_password
        )
        self.credentials_authorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_authorized.auth_token.key}"
        }
        self.user_unauthorized = self.create_user(
            self.user_unauthorized_username, self.user_password
        )
        self.credentials_unauthorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_unauthorized.auth_token.key}"
        }
        group = Group.objects.create(name=self.authorized_group_jobs)
        self.user_authorized.groups.add(group)
        self.client.credentials(**self.credentials_authorized)
        return super().setUp()

    stream_config = {
        "handler": "stream",
        "configuration": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": 10,
            "stream": "ext://sys.stdout",
        },
    }

    def test_list(self):
        url = reverse("handler-list")
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)

    def test_list_forbidden(self):
        url = reverse("handler-list")
        self.client.credentials(**self.credentials_unauthorized)
        response_get = self.client.get(url)
        self.client.credentials(**self.credentials_authorized)
        self.assertEqual(response_get.status_code, 403)

    def test_list_unauthorized(self):
        url = reverse("handler-list")
        self.client.credentials(**{})
        response_get = self.client.get(url)
        self.client.credentials(**self.credentials_authorized)
        self.assertEqual(response_get.status_code, 401)

    def test_post_and_delete(self):
        url = reverse("handler-list")
        logtest_url = reverse("logtest-list")
        log = logging.getLogger(LOGGER_NAME)
        response = self.client.post(url, data=self.stream_config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        response = self.client.delete(f"{url}stream/", format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 0)

    def test_post_and_update(self):
        url = reverse("handler-list")
        logtest_url = reverse("logtest-list")
        log = logging.getLogger(LOGGER_NAME)
        response = self.client.post(url, data=self.stream_config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(
            log.handlers[0].level, self.stream_config["configuration"]["level"]
        )
        config = copy.deepcopy(self.stream_config)
        config["configuration"]["level"] = 50
        self.client.patch(f"{url}stream/", data=config, format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 1)
        self.assertEqual(log.handlers[0].level, 50)
        response = self.client.delete(f"{url}stream/", format="json")
        self.client.get(logtest_url)
        self.assertEqual(len(log.handlers), 0)
