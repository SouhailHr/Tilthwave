# Broker Sandbox

Broker Sandbox is a Python project aimed at facilitating the development and testing of microservice architecture projects. It contains two services: Redpanda broker and its console.

## Introduction

This project is intended for development purposes to test microservice architectures. It provides a Redpanda broker and console, allowing developers to simulate and interact with a distributed messaging system.

## Usage

### Prerequisites

- Docker
- Docker Compose

### Getting Started

1. **Clone the Repository:**

    ```bash
    git clone <repository-url>
    cd BrokerSandbox
    ```

2. **Create the Network:**

    The lifecycle targets create the `farm-network-dev` network on demand. If you prefer to create it manually:

    ```bash
    make network
    ```


### Verifying Network Connectivity

After starting all the containers, verify that they are connected to the `farm-network-dev` network by running the following command:

```bash
docker network inspect farm-network-dev
```


Result example : 
```bash
"Containers": {
            "1568b033c426a1807afa3fc8e98747165a3d879d9618e22af06f7da69418d740": {
                "Name": "farm-redpanda-console",
                "EndpointID": "c05af86b44950750adbf40dafd0ccc50422dafb264db5e821546a7af84a2719c",
                "MacAddress": "02:42:c0:a8:b0:03",
                "IPv4Address": "192.168.176.3/20",
                "IPv6Address": ""
            },
            "b560ce45e86b8b987f8e43a2ca0cf55756153140d2d6ba81182cc3e1e23e5e34": {
                "Name": "farm-sandbox-redpanda",
                "EndpointID": "cbf522ca88c63885c69630503cd93ffd6a38be2440ab79724fe7c05eb66b37e5",
                "MacAddress": "02:42:c0:a8:b0:02",
                "IPv4Address": "192.168.176.2/20",
                "IPv6Address": ""
            },
            "ffc0a86077dfc79c88042dbc5734a67db8bf172fece0a46af2fef144e0569283": {
                "Name": "sensors-guard-mocker",
                "EndpointID": "872dd5f937acf0fef56946c83adbd99ecff571093282fb9fa15580448e4c5c85",
                "MacAddress": "02:42:c0:a8:b0:04",
                "IPv4Address": "192.168.176.4/20",
                "IPv6Address": ""
            }
        },


```
- Ensure that your project that wants to use Broker Sandbox is in the same network (`farm-network-dev`) to communicate with it effectively.

```bash

  my-service:
    .....
    networks:
      - farm-network-dev

networks:
  farm-network-dev:
    external: true  # Specify that this network is external
    
```



### Start project

1. **Start the Services:**

    ```bash
    make up
    ```

2. **Access the Console:**

    The console is accessible at `http://localhost:8082`.

3. **Stop the Services:**

    ```bash
    make down
    ```

## Makefile

The Makefile provides shortcut commands for managing the stack and driving the broker. Run `make help` to list every target. Useful ones:

| Target | Description |
| --- | --- |
| `make up` / `make down` | Start / stop the broker + console |
| `make ps` | Show running services |
| `make logs` | Follow logs for all services |
| `make broker-logs` / `make console-logs` | Per-service logs |
| `make broker-bash` | Shell into the broker container |
| `make cluster-info` / `make cluster-health` | `rpk` cluster diagnostics |
| `make topic-list` / `make topic-create` / `make topic-delete` | Topic management |
| `make produce` / `make consume` | Interactive produce / consume against a topic |
| `make superclean` | Stop the stack and drop the broker volume (DESTRUCTIVE) |
