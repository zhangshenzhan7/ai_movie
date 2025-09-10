#!/usr/bin/env python3
"""
Setup script for AI Movie Generator
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
else:
    requirements = []

# Read version
version_file = Path(__file__).parent / "src" / "ai_movie" / "__init__.py"
version = "0.1.0"
if version_file.exists():
    with open(version_file, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

setup(
    name="ai-movie-generator",
    version=version,
    author="AI Movie Team",
    author_email="contact@ai-movie.com",
    description="AI-powered video generation from text descriptions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-movie/ai-movie-generator",
    project_urls={
        "Bug Reports": "https://github.com/ai-movie/ai-movie-generator/issues",
        "Source": "https://github.com/ai-movie/ai-movie-generator",
        "Documentation": "https://ai-movie-generator.readthedocs.io/",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Content Creators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.19.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ai-movie=ai_movie.cli:main",
            "ai-movie-web=ai_movie.web.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "ai_movie.web": ["templates/*", "templates/**/*"],
    },
    zip_safe=False,
    keywords="ai, video, generation, machine learning, content creation",
)