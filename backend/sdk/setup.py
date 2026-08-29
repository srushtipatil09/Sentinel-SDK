from setuptools import setup, find_packages

setup(
    name="sentinelai-telemetry-sdk",
    version="1.0.0",
    description="Official Python SDK for Sentinel AI Autonomous Observability & Root Cause Analysis Platform.",
    long_description=open("README.md", encoding="utf-8").read() if open("README.md") else "",
    long_description_content_type="text/markdown",
    author="Sentinel AI Team",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
