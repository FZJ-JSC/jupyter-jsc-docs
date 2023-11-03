from unittest import mock

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


def mocked_k8s_svc(*args, **kwargs):
    return True


class K8sMockedTestCase(APITestCase):
    mock_patches = {}

    def addMock(self, name, side_effect, object=None):
        if object:
            self.mock_patches[name] = mock.patch.object(
                object, name, side_effect=side_effect
            )
        else:
            self.mock_patches[name] = mock.patch(name, side_effect=side_effect)
        self.mock_patches[name].start()
        self.addCleanup(self.mock_patches[name].stop)

    def setUp(self):
        self.addMock("tunnel.utils.k8s_svc", mocked_k8s_svc)
        return super().setUp()


class UserCredentials(K8sMockedTestCase):
    user_unauthorized_username = "unauthorized"
    user_authorized_username = "authorized"
    user_authorized_username_2 = "authorized2"
    user_authorized = None
    user_authorized_2 = None
    user_unauthorized = None
    user_password = "12345"
    user_password_2 = "12346"
    authorized_group_webservice = "access_to_webservice"
    authorized_group_webservice_restart = "access_to_webservice_restart"
    credentials_authorized = {}
    credentials_authorized_2 = {}
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
        self.user_authorized_2 = self.create_user(
            self.user_authorized_username_2, self.user_password_2
        )
        self.credentials_authorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_authorized.auth_token.key}"
        }
        self.credentials_authorized_2 = {
            "HTTP_AUTHORIZATION": f"token {self.user_authorized_2.auth_token.key}"
        }
        self.user_unauthorized = self.create_user(
            self.user_unauthorized_username, self.user_password
        )
        self.credentials_unauthorized = {
            "HTTP_AUTHORIZATION": f"token {self.user_unauthorized.auth_token.key}"
        }
        group1 = Group.objects.create(name=self.authorized_group_webservice)
        group3 = Group.objects.create(name=self.authorized_group_webservice_restart)
        self.user_authorized.groups.add(group1)
        self.user_authorized.groups.add(group3)
        self.user_authorized_2.groups.add(group1)
        self.user_authorized_2.groups.add(group3)
        self.client.credentials(**self.credentials_authorized)
        return super().setUp()
