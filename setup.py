from setuptools import setup, find_packages


setup(
    name = 'HakuNet',
    packages = find_packages(
        where = 'src'
    ),
    package_dir = {"": "src"},
    zip_safe = False,
    requires = [
        'asyncio',
    ],
    version = '0.1.0',
    description = 'A simple server framework',
    author = 'KohakuBlueleaf',
    author_email = 'apolloyeh0123@gmail.com',
    keywords = [
        'server',
        'socket',
        'framework',
        'asyncio',
    ],
)