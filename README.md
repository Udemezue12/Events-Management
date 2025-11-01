🎟️ FastAPI Event Ticketing System

🚀 Developed by UDEMEZUE UCHECHUKWU JUDE

🧭 Overview

The FastAPI Event Ticketing System is a scalable, asynchronous backend for event discovery, ticket management, and real-time processing — built with FastAPI, PostgreSQL (PostGIS), Celery, RabbitMQ, and Redis.

It leverages geospatial queries for nearby event discovery, asynchronous communication via message queues, and intelligent caching for high-performance production deployments. Designed with cloud deployment in mind, it supports Render, AWS, and Azure, using environment-based configuration.

⚙️ Core Features

🎫 Event Management – Create, list, and filter events by location (PostGIS spatial queries).

💳 Ticket Reservation & Payment Flow – Secure and async-driven.

👥 User Management – Registration, authentication-ready, and extendable.

📍 Geo-based Discovery – Uses ST_DWithin for proximity filtering.

⚙️ Asynchronous Execution – Thread + async I/O blend for scalability.

🚦 Caching & Throttling – Redis-backed caching and rate limiting.

📢 Event-driven Architecture – Publishes events via RabbitMQ (e.g., event.created, ticket.reserved).

🛡️ Resilience – Circuit breaker ensures safe retries and graceful failures.

🧪 Testing Suite – Async-first integration tests powered by pytest-asyncio.

🧩 Modular Architecture – Separation of routes, repositories, and services for clean maintainability.

🧱 Technology Stack
Layer	Technology
Framework	FastAPI (async-first web framework)
Database	PostgreSQL + PostGIS
ORM / Spatial	SQLAlchemy 2.0 + GeoAlchemy2
Migration	Alembic
Message Queue	RabbitMQ (via aio-pika)
Task Queue	Celery
Cache Layer	Redis
Rate Limiting	fastapi-limiter
Testing	pytest + pytest-asyncio
Deployment	Docker + Supervisor + Render/AWS/Azure
🧰 Installation & Setup

Clone the repository:

git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>


Install dependencies:

pip install -r requirements.txt


Set environment variables manually (via .env or Render/AWS/Azure settings):

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
RABBITMQ_URL=amqp://guest:guest@localhost//
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key

🚀 Running the Application

Run database migrations:

alembic upgrade head


Start the FastAPI development server:

uvicorn main:app --reload


Start Celery worker for background tasks:

celery -A main.celery worker --loglevel=info


(Optional) Run Celery Beat for scheduled or periodic tasks:

celery -A main.celery beat --loglevel=info


Access the interactive API documentation at:
👉 http://localhost:8000/docs

📂 Project Structure


🗺️ System Architecture
┌─────────────────────┐
│      FastAPI        │
│   (Async Gateway)   │
└─────────┬───────────┘
          │
          ▼
 ┌───────────────────────┐
 │  PostgreSQL + PostGIS  │
 │  (Events + Tickets)    │
 └──────────┬────────────┘
            │
            ▼
 ┌───────────────────────┐
 │     Redis Cache        │
 │ (Throttling & Storage) │
 └──────────┬────────────┘
            │
            ▼
 ┌────────────────────┐
 │     RabbitMQ       │
 │ (Event Publisher)  │
 └────────┬───────────┘
          │
          ▼
 ┌────────────────────┐
 │      Celery         │
 │ (Async Task Queue)  │
 └────────────────────┘

🧠 Design Philosophy

This system emphasizes:

Asynchronous efficiency — full async I/O for high throughput.

Separation of concerns — clear service-repo layering.

Scalability — RabbitMQ + Celery for distributed workloads.

Fault tolerance — built-in circuit breakers and caching.

Cloud-readiness — easily deployable on Render, AWS, or Azure.

👨‍💻 Author

👤 UDEMEZUE UCHECHUKWU JUDE
💼 Backend Engineer | API Architect | Distributed Systems Developer
🌐 Expert in Python, FastAPI, Django, Celery, Redis, RabbitMQ, PostgreSQL, and Docker.
📬 Passionate about designing high-performance backend systems that scale.