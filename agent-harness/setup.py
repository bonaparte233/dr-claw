from setuptools import setup, find_namespace_packages

setup(
    name='cli-anything-vibelab',
    version='0.1.0',
    packages=find_namespace_packages(include=['cli_anything.*']),
    install_requires=['click>=8.0', 'requests>=2.28', 'websockets>=11.0'],
    entry_points={
        'console_scripts': [
            'vibelab=cli_anything.vibelab.vibelab_cli:cli',
        ],
    },
    python_requires='>=3.8',
    author='VibeLab Agent Harness',
    description='CLI harness for the VibeLab AI research workspace',
)
