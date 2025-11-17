import docker


def create_client():
    return docker.DockerClient(base_url="unix://var/run/docker.sock")


docker_client = create_client()
