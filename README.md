# Docmeta

Metadata for searching and categorising downloadable documents.

## Installation

Add this to requirements
```
-e git://github.com/cccs-web/docmeta.git#egg=docmeta
```

### Installation for development
As this is a Django module, you need a 'main' project so you can test development changes as you go. You should already
be using a virtualenv for your main project.

In your main project, uninstall docmeta if it is already installed via the requirements in the project you want to work with the development
version in. Then clone a working copy and setup the project for development in your main project's virtualenv e.g:
```
(cccs)~/wk/cccs $ git clone https://github.com/cccs-web/docmeta
(cccs)~/wk/cccs $ cd docmeta
(cccs)~/wk/cccs $ python setup.py develop
```