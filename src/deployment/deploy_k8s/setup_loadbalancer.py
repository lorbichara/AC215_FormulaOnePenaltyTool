import pulumi
import pulumi_gcp as gcp
from pulumi import StackReference, ResourceOptions, Output
import pulumi_kubernetes as k8s


def setup_loadbalancer(
    namespace, k8s_provider, api_service, frontend_service, app_name, custom_domain=None
):
    # Nginx Ingress Controller using Helm and Create Ingress Resource
    nginx_helm = k8s.helm.v3.Release(
        "nginx-f5",
        chart="nginx-ingress",
        version="2.3.1",  # pick a current stable version from F5 docs/releases
        namespace=namespace.metadata.name,
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="https://helm.nginx.com/stable"
        ),
        values={
            "controller": {
                # Service exposed as a LoadBalancer with your static IP
                "service": {
                    "type": "LoadBalancer",
                },
                # Resource requests/limits (similar to what you had)
                "resources": {
                    "requests": {
                        "memory": "128Mi",
                        "cpu": "100m",
                    },
                    "limits": {
                        "memory": "256Mi",
                        "cpu": "200m",
                    },
                },
                "replicaCount": 1,
                # IngressClass config – default class name is "nginx" in this chart
                "ingressClass": {
                    "name": "nginx",
                    "create": True,
                    "setAsDefaultIngress": True,
                },
            },
        },
        opts=ResourceOptions(provider=k8s_provider),
    )

    # Get the service created by Helm to extract the LoadBalancer IP
    nginx_service = k8s.core.v1.Service.get(
        "nginx-ingress-service",
        pulumi.Output.concat(
            nginx_helm.status.namespace,
            "/",
            nginx_helm.status.name,
            "-nginx-ingress-controller",  # often resolves to <release-name>-ingress-nginx-controller
        ),
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_helm]),
    )
    ip_address = nginx_service.status.load_balancer.ingress[0].ip
    # Use custom domain if provided, otherwise use sslip.io
    if custom_domain:
        host = pulumi.Output.from_input(custom_domain)
    else:
        host = ip_address.apply(lambda ip: f"{ip}.sslip.io")

    # Create separate Ingress for API to avoid path conflicts
    api_ingress = k8s.networking.v1.Ingress(
        f"{app_name}-api-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=f"{app_name}-api-ingress",
            namespace=namespace.metadata.name,
            annotations={
                "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                "ingress.kubernetes.io/ssl-redirect": "false",
                # No rewrite needed - API accepts /api-service/query/ directly
            },
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            ingress_class_name="nginx",
            rules=[
                k8s.networking.v1.IngressRuleArgs(
                    host=host,
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                # Simple prefix match - no rewrite needed
                                # API has routes for both /query/ and /api-service/query/
                                path="/api-service",
                                path_type="Prefix",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name=api_service.metadata["name"],
                                        port=k8s.networking.v1.ServiceBackendPortArgs(
                                            number=9000
                                        ),
                                    )
                                ),
                            ),
                        ]
                    ),
                )
            ],
        ),
        opts=ResourceOptions(
            provider=k8s_provider,
            depends_on=[nginx_helm],
            ignore_changes=["status"],
        ),
    )

    # Frontend Ingress (no rewrite needed)
    frontend_ingress = k8s.networking.v1.Ingress(
        f"{app_name}-frontend-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=f"{app_name}-frontend-ingress",
            namespace=namespace.metadata.name,
            annotations={
                "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                "ingress.kubernetes.io/ssl-redirect": "false",
            },
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            ingress_class_name="nginx",
            rules=[
                k8s.networking.v1.IngressRuleArgs(
                    host=host,
                    http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                        paths=[
                            k8s.networking.v1.HTTPIngressPathArgs(
                                path="/",
                                path_type="Prefix",
                                backend=k8s.networking.v1.IngressBackendArgs(
                                    service=k8s.networking.v1.IngressServiceBackendArgs(
                                        name=frontend_service.metadata["name"],
                                        port=k8s.networking.v1.ServiceBackendPortArgs(
                                            number=3000
                                        ),
                                    )
                                ),
                            ),
                        ]
                    ),
                )
            ],
        ),
        opts=ResourceOptions(
            provider=k8s_provider,
            depends_on=[nginx_helm],
            ignore_changes=["status"],
        ),
    )

    # Return the frontend ingress for backwards compatibility
    ingress = frontend_ingress

    return ip_address, ingress, host