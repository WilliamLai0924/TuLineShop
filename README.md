# TuLineShop Monorepo

This repository contains the consolidated source code for the TuLineShop project, organized as a monorepo.

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1.  Clone the repository:

    ```bash
    git clone <repository-url>
    cd TuLineShop-Monorepo
    ```

2.  Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Running the Services

-   **LINE Bot API & Product API**:

    ```bash
    cd packages/line-bot-api
    python main.py
    ```

-   **Shop View**:

    ```bash
    cd packages/shop-view
    gunicorn app:app
    ```

## Packages

The individual projects are located in the `packages` directory:

-   **`packages/line-bot-api`**: The backend API for the LINE bot and product data, originally from the `line-bot-api` project.
-   **`packages/shop-view`**: The frontend web application for the shop, originally from the `shop-view` project.
