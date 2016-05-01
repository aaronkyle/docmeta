# DocMeta

`docmeta` is tool that manipulates metadata for organizing, search and (eventually) citing documents.

I started work on this tool via [CCCS](http://crossculturalconuslt.com).  [Paul Whipp](https://github.com/pwhipp) built the initial prototype.



## Assumptions / Plug-in Dependencies

The requirements in the `setup.py` or `requirements.txt` must be satisfied.

The built-in `docmeta` templates extend a `base.html` file, which is part of the Mezzanine CMS.

## Installation

Add this to requirements

```
-e git://github.com/aaronkyle/docmeta.git#egg=docmeta
```

### Installation for development

As this is a Django module, you need a 'main' project so you can test development changes as you go.

You should already be using a virtualenv for your main project.

In your main project, uninstall docmeta if it is already installed via the requirements in the project you want to work with the development
version in. Then clone a working copy and setup the project for development in your main project's virtualenv e.g:

```
(cccs)~/wk/cccs $ git clone https://github.com/cccs-web/docmeta
(cccs)~/wk/cccs $ cd docmeta
(cccs)~/wk/cccs $ python setup.py develop
```

## Configuration

Add taggit, storages, categories, categoies.editor and docmeta to your INSTALLED_APPS

Run the management command 'syncdb' or 'migrate' as appropriate.

South is recommended on Django versions earlier than 1.7.

Add docmeta.urls to your main project urls.py:

```
import docmeta.urls
...
urlpatterns += patterns(<
    '',
    ("^documents/", include(docmeta.urls)),
    ...
...
```

The current backend is S3 so the following settings must be set to appropriate values (keep them out of your repository using a secrets.py):
  
AWS_STORAGE_BUCKET_NAME
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

## Updating current production environments

When development is done, the production environments become out of date. Updating them is optional and can be done using the following pip command in the relevant environment:

```
(production)abadi:~/production $ pip install -e git://github.com/cccs-web/docmeta.git#egg=docmeta
```

If necessary, use pip freeze to write back the commit that has been installed this way.
