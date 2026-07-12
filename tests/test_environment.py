from testcontainers.postgres import PostgresContainer


def test_docker_environment_works():
    with PostgresContainer("postgres:16-alpine") as postgres:
        container = postgres.get_wrapped_container()
        container.reload()

        assert container.status == "running"
