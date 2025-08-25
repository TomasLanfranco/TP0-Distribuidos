import sys

COMPOSE_NAME = 'tp0'
NETWORK_NAME = 'testing_net'
NARGS = 3


def format_dict_to_yaml(d, indentation=0):
    compose = ''
    for key, value in d.items():
        compose += f"{'  ' * indentation}{key}:"
        if isinstance(value, dict):
            compose += "\n"
            compose += format_dict_to_yaml(value, indentation + 1)
        elif isinstance(value, list):
            compose += "\n"
            for item in value:
                compose += f"{'  ' * (indentation + 1)}- {item}\n"
        else:
            compose += f" {value}\n"
    return compose


def build_server_definition():
    server = {
        'container_name': 'server',
        'image': 'server:latest',
        'entrypoint': 'python3 /main.py',
        'environment': [
            'PYTHONUNBUFFERED=1',
        ],
        'volumes': ['./server/config.ini:/config.ini'],
        'networks': [NETWORK_NAME]
    }
    return format_dict_to_yaml({'server': server}, 1)


def build_client_definition(n):
    client = {
        'container_name': f'client{n}',
        'image': 'client:latest',
        'entrypoint': '/client',
        'environment': [
            f'CLI_ID={n}',
            f'CLI_NOMBRE=fulano{n}',
            f'CLI_APELLIDO=mengano{n}',
            f'CLI_DOCUMENTO={40000000 + n}',
            f'CLI_FECHA_NACIMIENTO=2000-01-{n:02d}',
            f'CLI_NUMERO_APOSTADO={7770 + n}',
        ],
        'volumes': ['./client/config.yaml:/config.yaml'],
        'networks': [NETWORK_NAME],
        'depends_on': ['server']
    }
    return format_dict_to_yaml({f'client{n}': client}, 1)


def build_networks_definition():
    networks = {
        NETWORK_NAME: {
            'ipam': {
                'driver': 'default',
                'config': [
                    'subnet: 172.25.125.0/24'
                ]
            }
        }
    }
    return format_dict_to_yaml({'networks': networks})


def build_compose(client_n):
    compose = ''
    compose += f'name: {COMPOSE_NAME}\n'
    compose += f'services:\n'

    compose += build_server_definition()

    for i in range(1, int(client_n) + 1):
        compose += "\n"
        compose += build_client_definition(i)

    compose += "\n"
    compose += build_networks_definition()

    return compose


def main():
    if len(sys.argv) != NARGS:
        print("Usage: python3 generar-compose.py <num_clients> <output_file>")
        sys.exit(1)

    _, output_file, client_n = sys.argv

    with open(output_file, 'w') as docker_compose_yaml:
        docker_compose_yaml.write(build_compose(client_n))


if __name__ == "__main__":
    main()
