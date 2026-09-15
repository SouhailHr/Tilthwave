# Tilthwave - Backend
Tilthwave employs a full IoT architecture with 
several microservices working together seamlessly. 
The backend consists of three primary services: 
Streamer, API, and Flow Runner, 
each performing specific roles to ensure the smooth functioning of the system.

## Backend Services Overview
### Streamer
#### Functionality: 
Listens for incoming data from the Broker Sandbox, processes it in real time, and stores it in the database.

#### Technology: 
FastStream for high-throughput data streaming.
#### Key Features:
Efficient handling of large data volumes.
Ensures data integrity during the streaming process.

### API
#### Functionality: 
Provides RESTful endpoints for CRUD operations on the database.
#### Technology: 
FastAPI for building modern, fast (high-performance) web APIs with Python.
#### Key Features:
Secure and efficient communication between frontend and backend.
Role-Based Access Control (RBAC) for protecting data.

### Flow Runner
#### Functionality: 
Automates irrigation based on real-time data analysis, 
initiating actions according to predefined rules.
#### Technology: 
Kafka Producer for asynchronous communication and data streaming.
#### Key Features:
Real-time data analysis and decision-making.
Event-driven communication with sensors to control irrigation.

## Usage

#### Setting Up the Development Environment

##### 1 - Prerequisites 
###### Docker
###### Docker Compose

##### 2 - Clone the Repository
```bash
git clone https://github.com/souhailharrathi/tilthwave.git
cd tilthwave
```
##### 3 - Build and Run the Services:

```bash
docker-compose up --build
```

## Configuration

Environment Variables:

1 - Database
```bash
 POSTGRES_HOST= YOUR DB HOST 
 POSTGRES_DB= YOUR DB 
 POSTGRES_USER= YOUR DB USER 
 POSTGRES_PASSWORD= YOUR DB PASSWORD 
 POSTGRES_PORT = YOUR DB HOST PORT 
 POSTGRES_DUMP_PATH = 'app/infrastructure/data/dump.sql'
```

2- Environment settings for FastAPI application
```bash
API_SECRET_KEY=YOUR_VERY_SECRET_KEY
API_ALGORITHM=HS256 // YOU CAN CHANGE IT 
API_ACCESS_TOKEN_EXPIRE=120  // YOU CAN CHANGE IT 
```

3 - Broker settings
```bash
 STREAMER_BROKER_HOSTS=["farm-sandbox-redpanda:29092"]
 STREAMER_SENSORS_TOPIC="tilthwave.sensors.dev"
 STREAMER_WATER_CONTROL_TOPIC="tilthwave.water-control.dev"
 STREAMER_LOG_LEVEL="INFO"
 STREAMER_LOG_FILENAME="logs/streamer.log"
```

4 - Settings for flow runner
```bash
 FLOW_RUNNER_MINUTES = 0.2 // YOU CAN CHANGE IT 
```

####  Source Code Links of other needed projects for the app 

##### Broker Sandbox : 
../broker (apps/broker in this monorepo)

##### Sensors Guard Sandbox : 

../simulator (apps/simulator in this monorepo)

### Conclusion
Tilthwave's backend is a robust system designed to handle the complexities of farm management 
through real-time data processing, efficient communication, and automation. 
By leveraging modern technologies and containerization, it ensures scalability, reliability, and ease of deployment.


## Contributing

Contributions are welcome! If you'd like to contribute to this project, please fork the repository and submit a pull
request.

## License

This project is licensed under the [MIT License](LICENSE).


