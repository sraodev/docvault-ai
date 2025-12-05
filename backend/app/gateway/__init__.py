"""
API Gateway Module

This module provides a centralized gateway layer for the API that handles:
- Request routing and versioning
- Middleware management
- Error handling
- Request/response transformation
- API documentation

The gateway acts as the single entry point for all API requests.
"""
from .gateway import APIGateway
from .versioning import APIVersion, VersionRouter
from .routing import RouteRegistry

__all__ = ["APIGateway", "APIVersion", "VersionRouter", "RouteRegistry"]

