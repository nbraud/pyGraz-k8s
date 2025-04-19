"""A Kubernetes Python Pulumi program"""

import pulumi
import pulumi_kubernetes as k8s

import cilium, gateway


# Setup Cilium
cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    "hubble",
})

# Setup Nginx Gateway Fabric, as the Gateway API implementation
#  see https://gateway-api.sigs.k8s.io/
gateway = gateway.deploy(depends_on = [ cilium_chart ])

# Demo application
# taken from https://docs.nginx.com/nginx-gateway-fabric/get-started/
demo_app = k8s.yaml.v2.ConfigFile(
    "demo-app",
    file = "./demo_app.yaml",
)
demo_routes = k8s.yaml.v2.ConfigFile(
    "demo-routes",
    file = "./demo_routes.yaml",
    opts = pulumi.ResourceOptions(depends_on = [ gateway["crd"] ]),
)
