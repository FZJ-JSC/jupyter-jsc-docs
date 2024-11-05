# Tunnel Manager
This service is used as an additional backend service for JupyterHub. It allows you to start JupyterLabs (or other webservices) remotely. The tunnel manager will create a ssh tunnel to the remote JupyterLab, so JupyterHub will be able to communicate with the JupyterLab, even if it's not reachable from the outside world.  
  
You can find a full deployment of the tunnel manager [here](https://github.com/FZJ-JSC/jupyter-jsc-deployment/tree/jupyterjsc-production/tunnel)
