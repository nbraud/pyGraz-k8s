"""A Kubernetes Python Pulumi program"""

import pulumi
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service

import cilium

cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    'hubble', 'l7'
})

pulumi.export(
    "cilium-ingress",
    # FIXME: this should be a flat list, either filter by svc name or flatten
    cilium_chart.resources.apply(lambda resources: pulumi.Output.all(*[
        svc.metadata.name.apply(lambda name: [name == "cilium-ingress", svc])
        for svc in resources
    ])).apply(lambda resources: pulumi.Output.all(*[
        svc #.status.load_balancer.ingress
        for [p, svc] in resources
        if p
    ]))
)

app_name = "nginx"
app_labels = { "app": app_name }

# Deploy Nginx
deployment = Deployment(
    app_name,
    opts = pulumi.ResourceOptions(
        depends_on = [ cilium_chart ],  # Necessary to ensure the pod is managed by cilium
    ),
    spec = {
        "selector": { "match_labels": app_labels },
        "replicas": 1,
        "template": {
            "metadata": { "labels": app_labels },
            "spec": { "containers": [{ "name": app_name, "image": "nginx" }] }
        },
    },
)

# Allocate an IP to the Deployment.
frontend = Service(
    app_name,
    metadata = {
        "labels": deployment.spec["template"]["metadata"]["labels"],
    },
    spec = {
        "type": "LoadBalancer",
        "ports": [{ "port": 80, "target_port": 80, "protocol": "TCP" }],
        "selector": app_labels,
    }
)

ingress = frontend.status.load_balancer.apply(lambda v: v["ingress"][0] if "ingress" in v else "output<string>")
pulumi.export(
    "ip",
    ingress.apply(lambda v: v["ip"] if v and "ip" in v else (v["hostname"] if v and "hostname" in v else "output<string>"))
)
