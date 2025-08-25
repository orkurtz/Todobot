"""
Setup script for WhatsApp Todo Bot
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="whatsapp-todo-bot",
    version="1.0.0",
    author="WhatsApp Todo Bot Team",
    description="An AI-powered personal assistant for task management via WhatsApp",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/whatsapp-todo-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "flask>=3.0.0",
        "requests>=2.32.3",
        "google-generativeai>=0.8.3",
        "gunicorn>=21.2.0",
        "psycopg2-binary>=2.9.9",
        "sqlalchemy>=2.0.23",
        "flask-sqlalchemy>=3.1.1",
        "flask-migrate>=4.0.5",
        "python-dateutil>=2.8.2",
        "pytz>=2023.3",
        "apscheduler>=3.10.4",
        "redis>=5.0.1",
        "rq>=1.15.1",
        "cryptography>=3.4.8",
        "ivrit>=0.0.4",
    ],
    entry_points={
        "console_scripts": [
            "whatsapp-todo-bot=app:app",
        ],
    },
)