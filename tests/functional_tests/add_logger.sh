curl -X "GET" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/logtest/ --fail
curl -X "POST" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" -d '{"handler": "stream", "configuration": {"level": 10, "formatter": "simple", "stream": "ext://sys.stdout"}}'  http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/handler/ --fail
curl -X "POST" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" -d '{"handler": "file", "configuration": {"level": 10, "formatter": "simple", "filename": "/tmp/tunnel.log"}}'  http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/handler/ --fail
curl -X "GET" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/logtest/ --fail
kubectl exec -it tunneling-devel-${CI_COMMIT_SHA} -- ls /tmp/tunnel.log
if [[ $? -ne 0 ]]; then
    echo "/tmp/tunnel.log does not exist"
fi
WC1=$(kubectl exec -it tunneling-devel-${CI_COMMIT_SHA} -- cat /tmp/tunnel.log | wc -l)
curl -X "GET" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/logtest/ --fail
WC2=$(kubectl exec -it tunneling-devel-${CI_COMMIT_SHA} -- cat /tmp/tunnel.log | wc -l)
if [[ ! $(($WC1 + 5)) -eq $WC2 ]]; then
    echo "Expected five new lines. $WC1 -> $WC2"
fi
curl -X "PATCH" -u admin:${TUNNEL_SUPERUSER_PASS} -H "Content-Type: application/json" -d '{"handler": "file", "configuration": {"level": 30, "formatter": "simple", "filename": "/tmp/tunnel.log"}}'  http://tunneling-devel-${CI_COMMIT_SHA}:8080/api/logs/handler/ --fail
