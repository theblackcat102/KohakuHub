# Fallback API Module

## Overview

The `kohakuhub.api.fallback` module implements a sophisticated fallback system that allows a KohakuHub instance to proxy requests to external sources, such as Hugging Face or other KohakuHub instances. When a repository or file is not found locally, this module attempts to find it on one of the configured fallback sources.

## Key Features

- **Transparent Fallback**: End-users can access resources from external hubs as if they were hosted locally.
- **Multiple Source Support**: Configure multiple fallback sources with different priorities.
- **Source Type Awareness**: Handles URL mapping differences between Hugging Face and other KohakuHub instances.
- **Caching**: Caches repository-to-source mappings to reduce redundant API calls to external sources.
- **Asynchronous Operations**: All external requests are made asynchronously to avoid blocking.
- **Decorator-based Integration**: Easily add fallback functionality to existing endpoints using decorators.

## Module Structure

- **`cache.py`**: A TTL (Time-To-Live) cache for storing which external source hosts a given repository.
- **`client.py`**: An asynchronous HTTP client for making requests to external sources, with logic for URL mapping.
- **`config.py`**: Functions for retrieving and managing the list of enabled fallback sources from the database and configuration.
- **`decorators.py`**: Decorators (`@with_repo_fallback`, `@with_list_aggregation`, `@with_user_fallback`) that wrap existing API endpoints to add fallback logic.
- **`operations.py`**: The core logic for handling fallback operations, such as resolving files, fetching repository info, and aggregating lists.
- **`utils.py`**: Helper functions for the fallback system.

## How It Works

1.  **Request Interception**: A request to an endpoint decorated with a fallback decorator (e.g., `@with_repo_fallback`) is intercepted.
2.  **Local First**: The decorator first attempts to process the request locally by calling the original endpoint function.
3.  **404 Detection**: If the local processing results in a 404 Not Found error (either via an `HTTPException` or a `Response` with a 404 status code), the fallback mechanism is triggered.
4.  **Cache Check**: The system checks its cache to see if it already knows which external source hosts the requested repository.
5.  **Source Probing**: If not cached, the system iterates through the configured fallback sources in priority order, making lightweight `HEAD` or `GET` requests to see if the resource exists.
6.  **Redirection or Proxying**:
    - For file downloads (`resolve` operations), if a source has the file, the system returns an HTTP 302 redirect to the external URL.
    - For API requests (e.g., fetching repository info or file trees), the system fetches the data from the external source, injects a `_source` field to indicate its origin, and returns it to the client.
7.  **Caching**: Once a resource is found on a source, the mapping is cached for a configurable duration (TTL) to speed up future requests.

## Configuration

The fallback system is configured through a combination of environment variables and database entries.

- **`KOHAKU_HUB_FALLBACK_ENABLED`**: A boolean to enable or disable the fallback system globally.
- **`KOHAKU_HUB_FALLBACK_CACHE_TTL`**: The time-to-live for cache entries in seconds.
- **`KOHAKU_HUB_FALLBACK_TIMEOUT`**: The timeout for HTTP requests to external sources.
- **`KOHAKU_HUB_FALLBACK_MAX_CONCURRENT`**: The maximum number of concurrent requests to external sources.
- **`KOHAKU_HUB_FALLBACK_SOURCES`**: A JSON list of global fallback sources.

Additionally, fallback sources can be managed through the admin API, which stores them in the `fallbacksource` database table. This allows for more dynamic and granular control over the fallback configuration.
