import os
import pulumi
import pulumi_docker_build as docker_build
from pulumi_gcp import artifactregistry
from pulumi import CustomTimeouts
import datetime

# 🔧 Get project info
project = pulumi.Config("gcp").require("project")
location = os.environ["GCP_REGION"]

# 🕒 Timestamp for tagging
timestamp_tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
repository_name = "f1penalty-repository"
registry_url = f"us-central1-docker.pkg.dev/{project}/{repository_name}"

# Create Artifact Registry repository first
artifact_registry_repo = artifactregistry.Repository(
    "f1penalty-repo",
    location=location,
    repository_id=repository_name,
    format="docker",
    description="Docker repository for F1 Penalty Tool application"
)

# Docker Build + Push -> Main F1 Penalty Tool App
image_config = {
    "image_name": "f1penalty-app",
    "context_path": "/project-root",  # Mounted project root
    "dockerfile": "Dockerfile"
}
f1penalty_app_image = docker_build.Image(
    f"build-{image_config['image_name']}",
    tags=[pulumi.Output.concat(registry_url, "/", image_config["image_name"], ":", timestamp_tag)],
    context=docker_build.BuildContextArgs(location=image_config["context_path"]),
    dockerfile={"location": "/project-root/Dockerfile"},
    platforms=[docker_build.Platform.LINUX_AMD64],
    push=True,
    opts=pulumi.ResourceOptions(custom_timeouts=CustomTimeouts(create="30m"),
                                retain_on_delete=True,
                                depends_on=[artifact_registry_repo])
)
# Docker Build + Push -> Frontend App
frontend_config = {
    "image_name": "f1penalty-frontend",
    "context_path": "/project-root/src/frontend/frontend-template",
    "dockerfile": "Dockerfile"
}
f1penalty_frontend_image = docker_build.Image(
    f"build-{frontend_config['image_name']}",
    tags=[pulumi.Output.concat(registry_url, "/", frontend_config["image_name"], ":", timestamp_tag)],
    context=docker_build.BuildContextArgs(location=frontend_config["context_path"]),
    dockerfile={"location": f"{frontend_config['context_path']}/{frontend_config['dockerfile']}"},
    platforms=[docker_build.Platform.LINUX_AMD64],
    push=True,
    opts=pulumi.ResourceOptions(custom_timeouts=CustomTimeouts(create="30m"),
                                retain_on_delete=True,
                                depends_on=[artifact_registry_repo])
)

# Export references to stack
pulumi.export("f1penalty-app-ref", f1penalty_app_image.ref)
pulumi.export("f1penalty-app-tags", f1penalty_app_image.tags)
pulumi.export("f1penalty-frontend-ref", f1penalty_frontend_image.ref)
pulumi.export("f1penalty-frontend-tags", f1penalty_frontend_image.tags)