from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="diap-sdk",
    version="0.1.2",
    author="DIAP Team",
    author_email="dev@diap.ai",
    description="DIAP Python SDK - Decentralized Intelligent Agent Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/logos-42/DIAP_Python_SDK",
    packages=find_packages(exclude=["tests", "examples"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.9.0",
        "ipfshttpclient>=0.8.0a2",
        "cryptography>=41.0.0",
        "cachetools>=5.3.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "mypy>=1.5.0",
            "ruff>=0.1.0",
        ],
    },
)
