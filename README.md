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

## Running the Service

To run the integrated application (LINE Bot API and Shop View):

```bash
gunicorn app:app
```

## Packages

The original individual projects are located in the `packages` directory:

-   **`packages/line-bot-api`**: Contains the LINE Bot API and product data logic.
-   **`packages/shop-view`**: Contains the frontend web application assets (static files and templates).