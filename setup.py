from setuptools import setup, find_packages

setup(
    name="trackman",
    version="0.1.0",
    description="Python client for the Trackman Golf API",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28",
    ],
    extras_require={
        "pandas": ["pandas>=1.5"],
    },
)
