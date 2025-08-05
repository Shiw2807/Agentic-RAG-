"""Setup configuration for the Microservice Refactor Agent."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="microservice-refactor-agent",
    version="0.1.0",
    author="Refactor Agent Team",
    description="An intelligent agent for refactoring legacy microservices with automated Git workflows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/microservice-refactor-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "gitpython>=3.1.0",
        "pygit2>=1.12.0",
        "astroid>=2.15.0",
        "pylint>=2.17.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "click>=8.1.0",
        "pydantic>=2.0.0",
        "networkx>=3.0",
        "matplotlib>=3.7.0",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
        "typer>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "refactor-agent=refactor_agent.cli:main",
        ],
    },
)