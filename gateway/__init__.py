from collections.abc import Sequence
from functools import reduce
import importlib.resources

import pulumi
import pulumi_kubernetes as k8s

def deploy(depends_on: Sequence[pulumi.Resource] = frozenset()):
    namespace = k8s.core.v1.Namespace("gateway")
    gatewayAPI_CRDs = k8s.yaml.v2.ConfigFile(
        "gateway-api-CRDs",
        file = "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml",
    )

    chart = k8s.helm.v4.Chart(
        "nginx-gateway-fabric",
        chart = "oci://ghcr.io/nginx/charts/nginx-gateway-fabric",
        version = "1.6.2",
        namespace = namespace,
        opts = pulumi.ResourceOptions(depends_on = [ gatewayAPI_CRDs, *depends_on ]),
    )

    # TODO: find a reasonable way to handle CRDs, crd2pulumi is not useable as-is
    # TODO: should this be in the default namespace?
    with importlib.resources.path(__name__, "http-gateway.yaml") as yaml_path:
        default_gw = k8s.yaml.v2.ConfigFile(
            "http-gateway",
            file = str(yaml_path),
            opts = pulumi.ResourceOptions(depends_on = [ gatewayAPI_CRDs ]),
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
        "crd": gatewayAPI_CRDs,
        "gw": default_gw,
    }
