from collections.abc import Set
from typing import Literal

import pulumi
import pulumi_kubernetes as k8s

def deploy(cfg: pulumi.Config, *, features: Set[Literal['hubble', 'l7']] = frozenset()):
    # address and port of the k8s API server to use
    host, port = cfg.require("k8sEndpoint").rsplit(":", 1)

    cilium = k8s.helm.v4.Chart(
        "cilium",
        chart = "./cilium-1.17.2.tgz",  # FIXME pulumi somehow gets something else from the repo?
        repository_opts = k8s.helm.v3.RepositoryOptsArgs(
            repo = "https://helm.cilium.io/",
        ),
        version = "1.17.2",  # TODO: autoupdate?
        namespace = "kube-system",
        # TODO signature verification?
        values = {
            "image": { "pullPolicy": "IfNotPresent" },
            "operator": { "replicas": 1 },  # No HA, this is a demo cluster

            # Avoid `kube-proxy`, let Cilium sling packets around
            #  requires `kubeProxyMode: "none"` in `kind-config.yaml`
            "kubeProxyReplacement": True,
            "k8sServiceHost": host,
            "k8sServicePort": port,

            # Optionally enable the Hubble observability tool
            "hubble": {
                "relay": { "enabled": True },
                "ui": { "enabled": True },
            } if "hubble" in features else {},

            # Enable L7 features & make Cilium the default Ingress controller
            "ingressController": {
                "enabled": True,
                "default": True,
                "loadbalancerMode": "shared",  # might want “dedicated” in a prod. setup
            } if "l7" in features else {},
        },
    )

    return cilium
