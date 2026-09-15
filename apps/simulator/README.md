# Sensor Mocker

The Sensor Mocker is a tool designed to generate mock data about sensors and send it to a Redpanda queue. It simulates
sensor readings for testing and development purposes.

## Installation

To run the Sensor Mocker, you'll need Docker installed on your system.

1. Clone this repository:

    ```bash
    git clone <repository-url>
    cd BrokerSandbox
    ```

2. Create a `.env` file based on the provided `.env.example` and fill in the required configuration variables.

3. Run the following command to start the Sensor Mocker:

## Configuration

The Sensor Mocker can be configured via environment variables. Edit the `.env` file to adjust settings such as the
Redpanda server address and sensor data generation parameters.

Example:
```bash
STREAMER_BROKER_HOSTS=["farm-sandbox-redpanda:29092"]
STREAMER_SENSORS_TOPIC="farm-commander.sensors.dev"
STREAMER_WATER_CONTROL_TOPIC="farm-commander.water-control.dev"
STREAMER_LOG_LEVEL="INFO"
STREAMER_LOG_FILENAME="logs/streamer.log"
```

## Usage

#####  Build and Run the Services:

```bash
docker-compose up --build
```

Once the Sensor Mocker is running, it will continuously generate mock sensor data and publish it to the specified Redpanda queue.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please fork the repository and submit a pull
request.

## License

This project is licensed under the [MIT License](LICENSE).