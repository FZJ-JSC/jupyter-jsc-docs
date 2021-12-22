from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class UserCredentials(APITestCase):
    user_unauthorized_username = "unauthorized"
    user_authorized_username = "authorized"
    user_authorized = None
    user_unauthorized = None
    user_password = "12345"
    authorized_group_webservice = "access_to_webservice"
    authorized_group_logs = "access_to_logging"
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
        group1 = Group.objects.create(name=self.authorized_group_webservice)
        group2 = Group.objects.create(name=self.authorized_group_logs)
        self.user_authorized.groups.add(group1)
        self.user_authorized.groups.add(group2)
        self.client.credentials(**self.credentials_authorized)
        return super().setUp()
