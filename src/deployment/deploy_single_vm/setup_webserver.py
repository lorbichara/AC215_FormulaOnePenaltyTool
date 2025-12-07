import hashlib
import pulumi
from pulumi import ResourceOptions
from pulumi_command import remote
import pulumi_docker as docker


def file_checksum(path: str) -> str:
    """
    Compute SHA256 checksum of a file.

    Args:
        path: Path to the file

    Returns:
        str: Hexadecimal checksum string
    """
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def setup_webserver(connection, docker_provider, docker_network):
    """
    Setup and deploy Nginx webserver:
    - Create nginx configuration directory
    - Create nginx configuration file directly on remote server
    - Deploy nginx container
    - Restart nginx to ensure configuration is loaded
    """
    # Create nginx config directory
    create_nginx_conf_dir = remote.Command(
        "create-nginx-conf-directory",
        connection=connection,
        create="""
            sudo mkdir -p /conf/nginx
            sudo chmod 0755 /conf/nginx
        """,
        opts=ResourceOptions(depends_on=[docker_provider]),
    )

    # Create nginx configuration file directly on remote server
    create_nginx_conf = remote.Command(
        "create-nginx-conf",
        connection=connection,
        create="""
            cat << 'EOF' | sudo tee /conf/nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream f1penalty_app {
        server f1penalty-app:9000;
    }
    
    upstream frontend {
        server frontend:3000;
    }
    
    server {
        listen 80;
        server_name _;
        
        # API requests go to the backend
        location /api {
            rewrite ^/api(.*)$ $1 break;
            proxy_pass http://f1penalty_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Everything else goes to the frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF
            
            sudo chmod 0644 /conf/nginx/nginx.conf
        """,
        opts=ResourceOptions(depends_on=[create_nginx_conf_dir]),
    )

    # Nginx container
    deploy_nginx = docker.Container(
        "deploy-nginx-container",
        image="nginx:stable",
        name="nginx",
        restart="always",
        ports=[
            docker.ContainerPortArgs(
                internal=80,
                external=80,
            ),
            docker.ContainerPortArgs(
                internal=443,
                external=443,
            ),
        ],
        volumes=[
            docker.ContainerVolumeArgs(
                host_path="/conf/nginx/nginx.conf",
                container_path="/etc/nginx/nginx.conf",
                read_only=True,
            )
        ],
        networks_advanced=[
            docker.ContainerNetworksAdvancedArgs(
                name=docker_network.name,
            )
        ],
        opts=ResourceOptions(
            provider=docker_provider,
            depends_on=[create_nginx_conf],
        ),
    )

    # Restart nginx to ensure config is loaded
    restart_nginx = remote.Command(
        "restart-nginx-container",
        connection=connection,
        create="""
            docker container restart nginx
        """,
        opts=ResourceOptions(depends_on=[deploy_nginx]),
    )

    return restart_nginx