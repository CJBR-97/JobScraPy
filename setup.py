from setuptools import setup, find_packages

setup(
    name='Job Scraping Tools for Python',
    url='https://github.com/CJBR-97/JobScraPy',
    author='Christoff Reimer',
    packages=find_packages(),
    install_requires=['re', 'datetime', 'time', 'warnings', 'functools', 'traceback', 'pandas', 'bs4', 'selenium'],
    version='0.1',
    license='MIT',
    description='A Python package for materials science from pre-existing code',
    long_description=open('README.txt').read(),
)
