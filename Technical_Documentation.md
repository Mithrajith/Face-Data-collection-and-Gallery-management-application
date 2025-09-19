# Technical Documentation: Face Recognition Gallery Manager

This document provides a technical overview of the Face Recognition Gallery Manager application, focusing on its architecture, core components, and key processes.

## 1. Application Architecture

The application is built using a modern Python stack, centered around the **FastAPI** web framework. It follows a modular, service-oriented architecture.

### 1.1. Core Principles

*   **Modularity**: The application is divided into distinct modules for handling API routes, database interactions, machine learning logic, and business services. This separation is evident in the `src` directory structure.
*   **Asynchronous Operations**: Leveraging FastAPI, the application is built to handle I/O-bound operations asynchronously, making it suitable for high-concurrency environments.
*   **Service-Oriented**: Business logic is encapsulated within service classes, promoting reusability and separating concerns from the API layer.
*   **Configuration-driven**: Key parameters like model paths, server settings, and directories are managed through a centralized configuration system, allowing for easy adjustments without code changes.

### 1.2. Application Entrypoint (`src/main.py`)

The application is launched via `src/main.py`, which serves as the main entry point.

*   It initializes the FastAPI application by calling `create_app()` from `src/api/routes.py`.
*   It sets up event handlers for application `startup` and `shutdown`:
    *   `@app.on_event("startup")`: Starts a background scheduler (`apscheduler`) for running periodic tasks defined in `src/periodic_tasks.py`.
    *   `@app.on_event("shutdown")`: Gracefully shuts down the scheduler.
*   When run directly, it uses `uvicorn` to serve the application, respecting host, port, and worker configurations from `src/config/settings.py`.

## 2. Source Code Structure (`src/`)

The `src` directory contains the core logic of the application, organized as follows:

| Directory/File          | Purpose                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| `main.py`               | The main entry point for the FastAPI application. Initializes the app and background scheduler.          |
| `api/`                  | Contains all API-related code, including route definitions and the main app factory.                    |
| `config/`               | Manages application settings and configurations, such as paths and server parameters.                   |
| `database/`             | Defines the database schema (SQLAlchemy models), session management, and CRUD operations.               |
| `ml/`                   | Encapsulates all machine learning logic, including model loading, inference, and feature extraction.    |
| `models/`               | Contains Pydantic models used for API request/response validation and data transfer objects (DTOs).     |
| `services/`             | Implements the core business logic, orchestrating calls between the database, ML models, and file system. |
| `utils/`                | Provides miscellaneous utility functions used across the application.                                   |
| `periodic_tasks.py`     | Defines background jobs that are run on a schedule, such as gallery synchronization or cleanup.         |
| `preprocess_images.py`  | Contains logic for processing and preparing images before they are used for gallery creation.           |
| `quality_checker.py`    | Implements a sophisticated pipeline to assess the quality of face images based on multiple metrics.     |
| `migrate_database.py`   | A script to initialize and migrate the database schema.                                                 |
| `gallery_manager.py`    | Handles the creation, loading, and management of face gallery files (`.pth`).                           |

## 3. Core Technical Components

### 3.1. API Layer (`src/api/`)

The API is defined using FastAPI's `APIRouter`. Each router corresponds to a specific feature domain (e.g., galleries, processing, recognition). The main `create_app` function in `src/api/routes.py` assembles these routers into the final FastAPI application and mounts the static files directory.

### 3.2. Machine Learning Engine (`src/ml/`)

This is the heart of the face recognition system.

*   **Face Detection**: Utilizes a **YOLO** model to detect faces in images and videos. The model is loaded and managed within this module to provide detection coordinates.
*   **Feature Extraction**: Employs a **LightCNN** model, a lightweight Convolutional Neural Network optimized for face recognition. It takes a cropped face image as input and outputs a high-dimensional feature vector (embedding) that uniquely represents the face.
*   **Similarity Matching**: Face recognition is performed by calculating the cosine similarity between the feature vector of a target face and all feature vectors in a gallery. A match is declared if the similarity score exceeds a predefined threshold.

### 3.3. Image Quality Assurance (`src/quality_checker.py`)

Before a face is added to a gallery, it undergoes a rigorous quality check to ensure recognition accuracy. This module implements a `QualityChecker` class that assesses images based on:

*   **Image Blurriness**: Uses a Laplacian variance method to detect and reject blurry images.
*   **Face Pose**: Estimates head pose (yaw, pitch, roll) to ensure the face is sufficiently frontal.
*   **Illumination**: Checks for under-lit or over-exposed images.
*   **Resolution**: Ensures the face crop meets a minimum size requirement.
*   **Occlusion**: Contains logic to detect if parts of the face are obstructed.

Only images that pass this multi-stage quality pipeline are used for gallery creation.

### 3.4. Database and Data Models (`src/database/` & `src/models/`)

*   **Database**: The application uses **SQLite** via **SQLAlchemy ORM**. The database connection and session management are handled in `src/database/session.py`.
*   **Schema (`src/database/models.py`)**: Defines the database tables for storing metadata, including `Batch`, `Department`, `Student`, `Gallery`, and `GalleryStudents`. These tables use relationships to link students to galleries and departments.
*   **Pydantic Models (`src/models/`)**: Pydantic models are used for strict type validation of API inputs and for serializing data in API responses. This ensures data integrity at the boundaries of the application.

### 3.5. Background Tasks (`src/periodic_tasks.py`)

The application uses `apscheduler` to run scheduled background jobs. A key task is the `sync_galleries_and_data` job, which periodically scans the file system and database to:
*   Ensure consistency between gallery files on disk and their metadata in the database.
*   Clean up orphaned data.
*   Update gallery statistics.

This ensures the long-term health and integrity of the application's data.
