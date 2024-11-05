from traitlets.config.application import get_config

c = get_config()

import sys

custom_path = "/src/jupyterhub-custom"
sys.path.insert(1, custom_path)

from spawner import BackendSpawner
from apihandler import SpawnProgressUpdateAPIHandler
from apihandler import user_cancel_message
from customauthenticator import CustomGenericOAuthenticator

c.JupyterHub.log_level = 10
c.JupyterHub.custom_config_file = "/home/jupyterhub/jupyterhub_custom_config.json"
c.JupyterHub.db_url = "sqlite:////home/jupyterhub/jupyterhub.sqlite"
c.JupyterHub.pid_file = "/home/jupyterhub/jupyterhub.pid"
c.JupyterHub.cookie_secret_file = "/home/jupyterhub/jupyterhub_cookie_secret"
c.ConfigurableHTTPProxy.pid_file = "/home/jupyterhub/jupyterhub-proxy.pid"

c.JupyterHub.cleanup_proxy = True
c.JupyterHub.default_url = "/hub/home"

c.JupyterHub.spawner_class = BackendSpawner
c.BackendSpawner.http_timeout = 900
c.BackendSpawner.backend_services_url = (
    "http://backend-6515fb85.gitlab.svc/api/services/"
)

c.JupyterHub.authenticator_class = CustomGenericOAuthenticator

c.CustomGenericOAuthenticator.custom_config_file = (
    "/home/jupyterhub/jupyterhub_custom_config.json"
)
c.CustomGenericOAuthenticator.enable_auth_state = True
c.CustomGenericOAuthenticator.client_id = "oauth-client"
c.CustomGenericOAuthenticator.client_secret = "oauth-pass1"
c.CustomGenericOAuthenticator.oauth_callback_url = (
    "http://jupyterhub-6515fb85.gitlab.svc/hub/oauth_callback"
)
c.CustomGenericOAuthenticator.authorize_url = (
    "https://unity-6515fb85.gitlab.svc/oauth2-as/oauth2-authz"
)
c.CustomGenericOAuthenticator.token_url = (
    "https://unity-6515fb85.gitlab.svc/oauth2/token"
)
c.CustomGenericOAuthenticator.tokeninfo_url = (
    "https://unity-6515fb85.gitlab.svc/oauth2/tokeninfo"
)
c.CustomGenericOAuthenticator.userdata_url = (
    "https://unity-6515fb85.gitlab.svc/oauth2/userinfo"
)
c.CustomGenericOAuthenticator.username_key = "email"
c.CustomGenericOAuthenticator.scope = "single-logout;hpc_infos;x500;authenticator;eduperson_entitlement;username;profile".split(
    ";"
)
c.CustomGenericOAuthenticator.tls_verify = False


# def foo():
#    ret = {"key1": ["value1", "value2"]}
#    return ret


# c.CustomGenericOAuthenticator.extra_params_allowed_runtime = foo
# http://localhost:8000/hub/oauth_login?extra_param_key1=value1


c.JupyterHub.template_paths = ["/home/jupyterhub/jupyterhub-static/templates"]
c.JupyterHub.template_vars = {
    "spawn_progress_update_url": "users/progress/update",
    "user_cancel_message": user_cancel_message,
    "hostname": "jupyterhub-6515fb85.gitlab.svc",
}
c.JupyterHub.data_files_path = "/home/jupyterhub/jupyterhub-static"

c.JupyterHub.extra_handlers = [
    ("/api/users/progress/update/([^/]+)", SpawnProgressUpdateAPIHandler),
    ("/api/users/progress/update/([^/]+)/([^/]+)", SpawnProgressUpdateAPIHandler),
]
