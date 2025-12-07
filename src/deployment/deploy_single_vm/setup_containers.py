import pulumi
from pulumi import ResourceOptions
from pulumi_command import remote
import pulumi_docker as docker


def setup_containers(connection, configure_docker, project, instance_ip, ssh_user):
    """
    Setup and deploy all application containers:
    - Copy GCP secrets to the VM
    - Create Docker network
    - Create persistent directories
    - Deploy frontend container
    - Deploy vector DB (ChromaDB) container
    - Load vector DB data
    - Deploy API service container

    Args:
        connection: SSH connection configuration
        configure_docker: The Docker configuration command (dependency)
        project: GCP project ID

    Returns:
        remote.Command: The last container deployment command (for dependency chaining)
    """
    # Get image references from deploy_images stack
    images_stack = pulumi.StackReference("organization/deploy-images/dev")
    # Get the main app image tag
    f1penalty_app_tag = images_stack.get_output("f1penalty-app-tags")
    # Get the frontend image tag
    f1penalty_frontend_tag = images_stack.get_output("f1penalty-frontend-tags")

    # Setup GCP secrets for containers
    copy_secrets = remote.Command(
        "copy-gcp-secrets",
        connection=connection,
        create="""
            sudo mkdir -p /srv/secrets
            sudo chmod 0755 /srv/secrets
        """,
        opts=ResourceOptions(depends_on=[configure_docker]),
    )

    upload_service_account = remote.CopyToRemote(
        "upload-service-account-key",
        connection=connection,
        source=pulumi.FileAsset("/secrets/gcp-service.json"),
        remote_path="/tmp/gcp-service.json",
        opts=ResourceOptions(depends_on=[copy_secrets]),
    )

    move_secrets = remote.Command(
        "move-secrets-to-srv",
        connection=connection,
        create="""
            sudo mv /tmp/gcp-service.json /srv/secrets/gcp-service.json
            sudo chmod 0644 /srv/secrets/gcp-service.json
            sudo chown root:root /srv/secrets/gcp-service.json
            gcloud auth activate-service-account --key-file /srv/secrets/gcp-service.json
            gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
        """,
        opts=ResourceOptions(depends_on=[upload_service_account]),
    )

    # Create directories on persistent disk
    create_dirs = remote.Command(
        "create-persistent-directories",
        connection=connection,
        create="""
            sudo mkdir -p /mnt/disk-1/persistent
            sudo mkdir -p /mnt/disk-1/chromadb
            sudo chmod 0777 /mnt/disk-1/persistent
            sudo chmod 0777 /mnt/disk-1/chromadb
        """,
        opts=ResourceOptions(depends_on=[move_secrets]),
    )

    # Set up Docker provider with SSH credentials for remote access
    docker_provider = docker.Provider(
        "docker-provider",
        host=instance_ip.apply(lambda ip: f"ssh://{ssh_user}@{ip}"),
        # SSH options to handle key-based authentication and suppress host checking
        ssh_opts=[
            "-i",
            "/secrets/ssh-key-deployment",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ],
        # Authentication for Google Container Registry / Artifact Registry
        registry_auth=[
            {
                "address": "us-central1-docker.pkg.dev",
            }
        ],
        opts=ResourceOptions(depends_on=[create_dirs]),
    )

    # Create Docker network
    docker_network = docker.Network(
        "docker-network",
        name="appnetwork",
        driver="bridge",
        opts=ResourceOptions(provider=docker_provider),
    )

    # Deploy main F1 Penalty Tool application
    deploy_f1penalty_app = docker.Container(
        "deploy-f1penalty-app-container",
        image=f1penalty_app_tag.apply(lambda tags: tags[0]),
        name="f1penalty-app",
        restart="always",
        ports=[
            docker.ContainerPortArgs(
                internal=9000,  # Container port (from your docker-compose.yml)
                external=9000,  # Host port
            )
        ],
        envs=[
            "GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-service.json",
            f"GCP_PROJECT={project}",
            "GCP_BUCKET=f1penaltydocs",
            "GCP_ZONE=us-central1-a",
            "CHROMADB_HOST=vector-db",
            "CHROMADB_PORT=8000",
            "UVICORN_PORT=9000",
            "ROOT_DIR=/mnt/gcs_data",
            "DATASET_DIR=/mnt/gcs_data",
            "OUTPUT_DIR=/mnt/disk-1/persistent",
        ],
        command=[
            "/bin/bash", "-c", 
            """
            gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS &&
            gcsfuse --implicit-dirs --key-file=$GOOGLE_APPLICATION_CREDENTIALS $GCP_BUCKET /mnt/gcs_data &&
            cd /app &&
            uv run uvicorn main:app --host 0.0.0.0 --port $UVICORN_PORT
            """
        ],
        volumes=[
            docker.ContainerVolumeArgs(
                host_path="/mnt/disk-1/chromadb",
                container_path="/mnt/gcs_data",
                read_only=False,
            ),
            docker.ContainerVolumeArgs(
                host_path="/srv/secrets",
                container_path="/app/secrets",
                read_only=False,
            ),
        ],
        networks_advanced=[
            docker.ContainerNetworksAdvancedArgs(
                name=docker_network.name,
            ),
        ],
        opts=ResourceOptions(
            provider=docker_provider,
            depends_on=[docker_network, create_dirs],
        ),
    )

    # Vector DB (ChromaDB - needed by your main app)
    deploy_vector_db = docker.Container(
        "deploy-vector-db-container",
        image="chromadb/chroma:latest",
        name="vector-db",
        restart="always",
        ports=[
            docker.ContainerPortArgs(
                internal=8000,  # Container port
                external=8000,  # Host port
            )
        ],
        envs=[
            "IS_PERSISTENT=TRUE",
            "ANONYMIZED_TELEMETRY=FALSE",
        ],
        volumes=[
            docker.ContainerVolumeArgs(
                host_path="/mnt/disk-1/chromadb",
                container_path="/chroma/chroma",
                read_only=False,
            )
        ],
        networks_advanced=[
            docker.ContainerNetworksAdvancedArgs(
                name=docker_network.name,
            ),
        ],
        opts=ResourceOptions(
            provider=docker_provider,
            depends_on=[docker_network],
        ),
    )

    # Deploy Frontend container
    deploy_frontend = docker.Container(
        "deploy-frontend-container",
        image=f1penalty_frontend_tag.apply(lambda tags: tags[0] if tags else ""),
        name="frontend",
        restart="always",
        ports=[
            docker.ContainerPortArgs(
                internal=3000,
                external=3000,
            )
        ],
        envs=[
            "NEXT_PUBLIC_BASE_API_URL=/api",
        ],
        networks_advanced=[
            docker.ContainerNetworksAdvancedArgs(
                name=docker_network.name,
            ),
        ],
        opts=ResourceOptions(
            provider=docker_provider,
            depends_on=[docker_network, deploy_f1penalty_app],
        ),
    )

    return docker_provider, docker_network