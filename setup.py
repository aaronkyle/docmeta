from setuptools import setup, find_packages

required_packages = [
    'mezzanine',
    'django-taggit',
    'boto',
    'django-categories',
    'django-storages',
    'pdfminer',
    'python-dateutil']

setup(
    name='docmeta',
    version= 0.1,
    description= "Document manager. Handles searching and listing documents using metadata model objects.",
    author='Paul Whipp',
    author_email='paul.whipp@gmail.com',
    url='https://github.com/cccs-web/docmeta',
    packages=find_packages(),
    install_requires=required_packages,
    license='BSD')