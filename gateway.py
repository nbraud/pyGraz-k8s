from collections.abc import Sequence
from functools import cache, reduce

import pulumi
import pulumi_kubernetes as k8s


@cache
def crds():
    return k8s.yaml.v2.ConfigFile(
        "gateway-api-CRDs",
        file = "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml",
    )

def deploy(depends_on: Sequence[pulumi.Resource] = frozenset()):
    namespace = k8s.core.v1.Namespace("gateway")

    chart = k8s.helm.v4.Chart(
        "nginx-gateway-fabric",
        chart = "oci://ghcr.io/nginx/charts/nginx-gateway-fabric",
        version = "1.6.2",
        namespace = namespace,
        opts = pulumi.ResourceOptions(depends_on = [ crds(), *depends_on ]),
    )

    # TODO: find a reasonable way to handle CRDs, crd2pulumi is not useable as-is
    default_gw = k8s.apiextensions.CustomResource(
        "default-gw",
        api_version = "gateway.networking.k8s.io/v1",
        kind = "Gateway",
        metadata = k8s.meta.v1.ObjectMetaArgs(namespace = namespace),
        opts = pulumi.ResourceOptions(depends_on = crds()),
        spec = {
            "gatewayClassName": "nginx",
            "listeners": [ {
                "name": "http",
                "port": 80,
                "protocol": "HTTP",
                "hostname": "*.k8s.local",
                "allowedRoutes": {
                    "kinds": [ { "kind": "HTTPRoute" } ],
                    "namespaces": { "from": "All" },  # TODO: restrict exposure to specific namespaces
                },
            } ],
        }
    )

    pulumi.export(
        "nginx-ingress",
        chart.resources.apply(lambda resources: pulumi.Output.all(*(
            pulumi.Output.all(
                ips = svc.status.load_balancer.apply(lambda lb: [ ingress.ip for ingress in lb.ingress or [] ]),
                pred = svc.metadata.apply(lambda m: m.name == "nginx-gateway-fabric"),
            )
            for svc in resources
            if isinstance(svc, k8s.core.v1.Service)
        ))).apply(lambda out: reduce(lambda acc, x: acc + (x["ips"] if x["pred"] else []), out, [])),
    )

    return {
        "namespace": namespace,
        "chart": chart,
        "crd": crds(),
        "gw": default_gw,
    }
