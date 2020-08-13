import os
from setuptools import find_packages, setup

setup(
    name="faust-avro",
    include_package_data=True,
    packages=find_packages(exclude=["tests"]),
)
