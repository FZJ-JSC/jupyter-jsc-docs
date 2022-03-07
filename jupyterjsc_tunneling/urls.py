"""jupyterjsc_tunneling URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include
from django.urls import path

from tunnel.views import RemoteViewSet
from tunnel.views import RestartViewSet

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("tunnel.urls")),
    path("api/remote/", RemoteViewSet.as_view(), name="remote"),
    path("api/restart/", RestartViewSet.as_view(), name="restart"),
    path("api/health/", lambda r: HttpResponse()),
    path("api/logs/", include("logs.urls")),
    path("api-auth/", include("rest_framework.urls")),
]
