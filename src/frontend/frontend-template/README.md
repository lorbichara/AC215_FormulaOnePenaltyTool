# F1 Penalty Explainer - Frontend

This directory contains the source code for the F1 Penalty Explainer frontend application. It is a [Next.js](https://nextjs.org/) application that provides a user interface for interacting with the Formula 1 penalty analysis backend.

## Features

*   **Interactive Chat**: A chat interface to ask questions about F1 rules, penalties, and incidents in natural language.
*   **Penalty Document Analysis**: A page to upload and analyze official FIA penalty documents.
*   **Theming**: Includes both light and dark mode, and is responsive.
*   **Component-Based UI**: Built with reusable React components using [shadcn/ui](https://ui.shadcn.com/).

## Tech Stack

*   **Framework**: [Next.js](https://nextjs.org/)
*   **Language**: JavaScript (React)
*   **Styling**: [Tailwind CSS](https://tailwindcss.com/)
*   **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
*   **API Communication**: [Axios](https://axios-http.com/)
*   **Markdown Rendering**: [React Markdown](https://github.com/remarkjs/react-markdown)

## Getting Started

There are two primary ways to run the frontend for development.

### Method 1: Using Docker Compose (Recommended)

This method runs the entire application stack (frontend, backend, database) with a single command.

1.  **Prerequisites**: Docker and Docker Compose are installed.
2.  **Run the application**: From the project root directory (containing `docker-compose.yml`), run:
    ```bash
    docker-compose up --build
    ```
3.  **Access the application**: Open your browser and navigate to `http://localhost:3001`.

### Method 2: Manual Container Setup

This method runs only the frontend in a Docker container, assuming the backend services are running separately.

1.  **Navigate to this directory**:
    ```bash
    cd src/frontend/frontend-template
    ```
2.  **Build and start the container**: This script starts an interactive shell inside the container.
    ```bash
    sh docker-shell.sh
    ```
3.  **Install dependencies** (inside the container's shell):
    ```bash
    npm install
    ```
4.  **Run the development server** (inside the container's shell):
    ```bash
    npm run dev
    ```
5.  **Access the application**: Open your browser and navigate to `http://localhost:3001`.

## Evidence of Running Components

Below are screenshots showing the frontend application and its components in action.

### Home Page (Light Mode)

This screenshot shows the application's home page with the light theme enabled.

![Home Page - Light Mode](./assets/homepage.png)

### Home Page (Dark Mode)

This screenshot shows the application's home page with the dark theme enabled.

![Home Page - Dark Mode](./assets/homepage-dark.png)

### Chat Interface

This screenshot shows the main chat interface of the application.

![Application UI](./assets/ui-running.png)

### Docker Compose Services

This screenshot shows the `docker-compose` services running, including the frontend, backend (`rag`), and database (`chromadb`).

![Docker Compose Services](./assets/docker-compose.png)
