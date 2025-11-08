# LagTALK Microblogging Platform Backend

This repository contains the production-ready, modular FastAPI backend for the LagTALK platform.

## Features

-   **Authentication**: JWT-based with role access (`general`, `student`, `institution`, `admin`).
-   **Database**: Asynchronous PostgreSQL with SQLModel and Alembic for migrations.
-   **Architecture**: Modular routers, repository pattern, and dependency injection.
-   **Media Uploads**: Direct-to-S3 pre-signed URL flow.
-   **Real-time**: WebSocket endpoint for notifications.
-   **Observability**: Prometheus metrics and a pre-configured Grafana dashboard.
-   **Containerized**: Fully containerized with Docker and Docker Compose for easy setup.

## Getting Started

### Prerequisites

-   Docker and Docker Compose
-   Python 3.11+
-   An `.env` file (copy from `.env.example`)

### 1. Setup Environment

Copy the example environment file and update the variables as needed.

```bash
cp .env.example .env

Important: Generate a new SECRET_KEY using openssl rand -hex 32.

2. Build and Run with Docker Compose
This command will start the FastAPI backend, PostgreSQL database, MinIO (S3), Prometheus, and Grafana.

Bash

docker-compose up --build
API: http://localhost:8000/docs

MinIO Console: http://localhost:9001 (Use MINIO_ROOT_USER and MINIO_ROOT_PASSWORD from your .env)

Prometheus: http://localhost:9090

Grafana: http://localhost:3000 (Login with admin/grafana or your .env values)

3. Create the S3 Bucket
Navigate to the MinIO console at http://localhost:9001.

Login with your MinIO credentials.

Click on "Buckets" and create a new bucket named lagtalk-media (or whatever you set S3_BUCKET_NAME to).

4. Database Migrations with Alembic
To run database migrations, you need to execute the alembic command inside the running backend container.

Generate a new migration (after changing models.py):

Bash

docker-compose exec backend alembic revision --autogenerate -m "Your migration message"
Apply migrations:

Bash

docker-compose exec backend alembic upgrade head
Running Tests
To run the test suite:

Bash

docker-compose exec backend pytest
Grafana Setup
The included docker-compose.yml automatically provisions Grafana.

Navigate to http://localhost:3000.

Login with the credentials from your .env file (GF_SECURITY_ADMIN_USER/GF_SECURITY_ADMIN_PASSWORD).

The Prometheus data source and the "LagTALK API Performance" dashboard will be pre-configured and available.

The dashboard visualizes:

Requests per second by endpoint.

95th percentile request latency.

Distribution of HTTP status codes