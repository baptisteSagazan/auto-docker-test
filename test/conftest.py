import logging
import os
import time
from logging import Logger
from typing import List

import docker
from docker.models.containers import Container

import pytest

logging.basicConfig()
logger: Logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.fixture(scope="session", autouse=True)
def setup_containers(request):
    env_variables = {
        "INFLUXDB_HTTP_ADDR": "localhost",
        "INFLUXDB_HTTP_PORT": "8090",
        "INFLUXDB_USER": "test",
        "INFLUXDB_PASSWORD": "test",
        "INFLUXDB_DB": "test",
        "MINIO_HTTP_ADDR": "localhost:9001",
        "MINIO_ACCESS_KEY": "access_key",
        "MINIO_SECRET_KEY": "secret_key",
    }

    is_set_up = set(env_variables).issubset(set(os.environ))

    if is_set_up:
        logger.info("Environment is already running")
    else:
        containers: List[Container] = []

        def cleanup():
            for container in containers:
                try:
                    container.kill()
                except docker.DockerException:
                    pass

        request.addfinalizer(cleanup)
        os.environ.update(env_variables)
        client = docker.from_env()

        influxdb = client.containers.run(
            image="influxdb:1.7-alpine",
            remove=True,
            detach=True,
            ports={"8086": 8090},
            name="influx-tests",
        )
        containers.append(influxdb)

        minio = client.containers.run(
            image="minio/minio:latest",
            command=["server", "/data"],
            ports={"9000": 9001},
            remove=True,
            detach=True,
            name="minio-tests",
            environment={
                "MINIO_ACCESS_KEY": env_variables.get("MINIO_ACCESS_KEY"),
                "MINIO_SECRET_KEY": env_variables.get("MINIO_SECRET_KEY"),
            },
            volumes={
                os.path.join(os.getcwd(), "test", "files"): {
                    "bind": "/data",
                    "mode": "rw",
                }
            },
        )
        containers.append(minio)

        time.sleep(1)  # Wait influxdb
