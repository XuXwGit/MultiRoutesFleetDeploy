from setuptools import setup, find_packages

setup(
    name="shipping_system",
    version="1.0",
    packages=find_packages(),
    package_dir={'': '.'},
    install_requires=[
        'gurobipy',
        'flask',
        'numpy',
        'pandas',
        'matplotlib'
    ],
    python_requires='>=3.8'
)