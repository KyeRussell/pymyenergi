#!/usr/bin/env python
from pathlib import Path

from setuptools import setup

version = (Path("pymyenergi") / "VERSION").read().strip()

setup(
    name="pymyenergi",
    version=version,
    author="Johan Isaksson",
    author_email="johan@generatorhallen.se",
    description="Python library and CLI for communicating with myenergi API.",
    long_description=Path("README.md").read(),
    long_description_content_type="text/markdown",
    package_data={"pymyenergi": ["VERSION"]},
    include_package_data=True,
    url="https://github.com/cjne/pymyenergi",
    license="MIT",
    packages=["pymyenergi"],
    python_requires=">=3.8",
    install_requires=["httpx", "pycognito"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
    ],
    setup_requires=("pytest-runner"),
    tests_require=(
        "asynctest",
        "pytest-cov",
        "pytest-asyncio",
        "pytest-trio",
        "pytest-tornasync",
    ),
)
