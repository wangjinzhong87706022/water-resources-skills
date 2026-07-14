#!/usr/bin/env python3
"""Database configuration for evaluation scripts.

All scripts should import get_db_config() instead of hardcoding connection info.

Usage:
    from config import get_db_config

    db_config = get_db_config()
    conn = pymysql.connect(**db_config)
"""

import os


def get_db_config(database='sl323') -> dict:
    """Get database configuration from environment variables.

    Environment variables:
        SL323_DB_HOST: Database host (default: 192.168.100.103)
        SL323_DB_PORT: Database port (default: 3306)
        SL323_DB_USER: Database user (default: root)
        SL323_DB_PASSWORD: Database password (required)

    Args:
        database: Database name (default: sl323)

    Returns:
        dict: Database configuration for pymysql.connect()
    """
    return {
        'host': os.environ.get('SL323_DB_HOST', '192.168.100.103'),
        'port': int(os.environ.get('SL323_DB_PORT', '3306')),
        'user': os.environ.get('SL323_DB_USER', 'root'),
        'password': os.environ.get('SL323_DB_PASSWORD', ''),
        'database': database,
        'charset': 'utf8mb4',
        'connect_timeout': 10,
    }


def get_default_db_config() -> dict:
    """Get default sl323 database configuration."""
    return get_db_config('sl323')
