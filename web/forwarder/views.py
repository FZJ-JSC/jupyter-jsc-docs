import logging
import json
import requests

from django.forms.models import model_to_dict
from json import JSONDecodeError
from kubernetes.client.exceptions import ApiException as K8sApiException
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from jupyterjsc_tunneling.decorators import request_decorator
from jupyterjsc_tunneling.settings import LOGGER_NAME
from tunnel.serializers import TunnelSerializer
from tunnel.models import TunnelModel

from .utils.common import *
from .utils.k8s import get_tunnel_sts_pod_names 
from .utils.k8s import edit_service_selector

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class RestartForwarderViewSet(GenericAPIView):
    required_groups = ["access_to_webservice_restart"]
    
    @request_decorator
    def post(self, request, *args, **kwargs):
        request_properties = get_request_properties()
        
        # This needs to be forwarded to all pods
        tunnel_pods = get_tunnel_sts_pod_names()
        _errors = {}
        for pod in tunnel_pods:
            url = get_service_url(pod, endpoint="restart")
            try:
                r = requests.post(
                    url, 
                    data=request.data.dict(), 
                    headers=request_properties["headers"],
                    verify=request_properties["ca"]
                )
                r.raise_for_status()
            except requests.exceptions.HTTPError:
                try:
                    details = r.json()
                    _errors[pod] = details
                    log.info(f"Could not restart tunnels on {pod}", extra={
                        **request.data.dict(), 
                        **{ "error": details }
                    })
                except JSONDecodeError:
                    details = {"detail": "Request response could not be serialized"}
                    log.info(f"Could not restart tunnels on {pod}", extra={
                        **request.data.dict(), 
                        **{ 
                            "request_url": r.url,
                            "status_code": r.status_code,
                            "request_text": r.text 
                        }
                    })
                    _errors[pod] = f"{r.status_code} {r.text}"
            except Exception as e:
                _errors[pod] = str(e)
                log.info(f"Could not restart tunnels on {pod}", extra={
                    **request.data.dict(), 
                    **{ "error": str(e) }
                })
        if _errors:
            return Response(json.dumps(_errors), status=status.HTTP_200_OK)
        return Response(status=status.HTTP_200_OK)


class TunnelForwarderViewSet(GenericAPIView):
    serializer_class = TunnelSerializer
    lookup_field = "servername"
    required_groups = ["access_to_webservice"]

    def get_queryset(self):
        if self.request.user.username == "tunnel":
            queryset = TunnelModel.objects.filter()
        else:
            queryset = TunnelModel.objects.filter(jhub_credential=self.request.user)
        return queryset

    @request_decorator
    def get(self, request, *args, **kwargs):
        if 'servername' in kwargs:
            instance = self.get_object()
            redirect_url = get_responsible_pod_url(instance, suffix=instance.servername)
        else:
            redirect_url = get_service_url()
        log.debug(f"Redirecting tunnel POST request to {redirect_url}")
        return Response(status=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": redirect_url})

    @request_decorator
    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        if "new_pod" not in request.data:
            raise ValidationError("Missing key in request data: new_pod")
        
        old_tunnel_pod = instance.tunnel_pod
        request_properties = get_request_properties()
        # Create tunnel on new pod
        new_tunnel_pod = request.data["new_pod"]
        new_tunnel_url = get_service_url(new_tunnel_pod, suffix=instance.servername)
        new_tunnel_data = model_to_dict(instance)
        new_tunnel_data["tunnel_pod"] = new_tunnel_pod
        new_tunnel_data.update({ 
            "start_tunnel": True,
            "uuidcode": "StartTunnel via PUT"
        })
        try:
            new_tunnel_request = requests.put(
                new_tunnel_url, 
                data=new_tunnel_data, 
                headers=request_properties["headers"],
                verify=request_properties["ca"]
            )
            new_tunnel_request.raise_for_status()
        except requests.exceptions.HTTPError:
            return Response(new_tunnel_request.json(), status=new_tunnel_request.status_code)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Patch service to use new pod
        new_instance = self.get_object()
        try:
            edit_service_selector(new_instance.svc_name, new_instance.tunnel_pod, new_instance.local_port)
        except K8sApiException as e:
            return Response(e.body, status=e.status)


        # Delete tunnel on old pod
        old_tunnel_url = get_service_url(old_tunnel_pod, suffix=instance.servername)
        old_tunnel_data = model_to_dict(instance)
        old_tunnel_data.update({ 
            "start_tunnel": False,
            "uuidcode": "StopTunnel via PUT"
        })
        try:
            old_tunnel_request = requests.put(
                old_tunnel_url,
                data=old_tunnel_data, 
                headers=request_properties["headers"],
                verify=request_properties["ca"]
            )
            old_tunnel_request.raise_for_status()
        except requests.exceptions.HTTPError:
            return Response(old_tunnel_request.json(), status=old_tunnel_request.status_code)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(new_tunnel_request.json(), status=status.HTTP_200_OK)
    
    @request_decorator
    def post(self, request, *args, **kwargs):
        redirect_url = get_least_tunnel_pod_url()
        log.debug(f"Redirecting tunnel POST request to {redirect_url}")
        return Response(status=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": redirect_url})

    @request_decorator
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        redirect_url = get_responsible_pod_url(instance, suffix=instance.servername)
        log.debug(f"Redirecting tunnel POST request to {redirect_url}")
        return Response(status=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": redirect_url})