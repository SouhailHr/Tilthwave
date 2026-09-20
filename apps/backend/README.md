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

The backend runs as part of the full stack: `make up` at the repository root (see the root README).
It ships as one image with four entrypoints under `docker/`: `migrate` (one-shot `alembic upgrade head`),
`api`, `streamer` and `flow_runner`.

### Development

```bash
uv sync                      # creates .venv from uv.lock
uv run ruff check app tests  # lint (blocking in CI)
uv run pytest -q             # tests run against SQLite, no services needed
```

Modules are imported with `PYTHONPATH=app` (`from core.use_cases...`). Running a process locally
against the docker stack:

```bash
cp .env.example .env         # POSTGRES_HOST=localhost, real API_SECRET_KEY (>= 32 chars)
PYTHONPATH=app uv run uvicorn interfaces.api.main:app --reload --port 8080
```

### Architecture notes

- `wiring.py` is the composition root: repositories and use cases are built once per process, with a
  Kafka broker gateway only for the flow runner (`worker_use_cases`) and a no-op gateway everywhere else.
- Requests are authorized by `RBACMiddleware` (role x method x resource) and scoped to the caller's farm by
  `TenantContextMiddleware` + `TENANT_SCOPE` on each repository.
- Domain exceptions (`common/exceptions.py`) are translated to HTTP responses in one place,
  `interfaces/api/helpers/errors.py`; endpoints never build error bodies.
- The flow runner publishes commands before persisting task state and enforces two safety limits
  (`FLOW_RUNNER_MAX_IRRIGATION_MINUTES`, `FLOW_RUNNER_MAX_READING_AGE_MINUTES`).

## Configuration

Environment variables (all read by `config/settings.py`; a `.env` at `apps/backend/.env` is optional):

1 - Database
```bash
 POSTGRES_HOST= YOUR DB HOST
 POSTGRES_DB= YOUR DB
 POSTGRES_USER= YOUR DB USER
 POSTGRES_PASSWORD= YOUR DB PASSWORD
 POSTGRES_PORT= 5432
 POSTGRES_URI= optional full SQLAlchemy URI (e.g. sqlite:///... for tests)
```

2- API
```bash
API_SECRET_KEY=            # >= 32 random chars; placeholders are refused at startup
API_ALGORITHM=HS256
API_ACCESS_TOKEN_EXPIRE=120
API_CORS_ORIGINS=["http://localhost:3000"]
API_LOGIN_RATE_LIMIT_PER_MINUTE=10
```

3 - Broker
```bash
 STREAMER_BROKER_HOSTS=["redpanda:29092"]
 STREAMER_SENSORS_TOPIC=tilthwave.sensors.dev
 STREAMER_WATER_CONTROL_TOPIC=tilthwave.water-control.dev
 STREAMER_GROUP_ID=tilthwave-backend-streamer
 LOG_LEVEL=INFO
```

4 - Flow runner
```bash
 FLOW_RUNNER_MINUTES=0.2
 FLOW_RUNNER_MAX_IRRIGATION_MINUTES=60
 FLOW_RUNNER_MAX_READING_AGE_MINUTES=30
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


