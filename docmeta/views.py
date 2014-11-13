from collections import defaultdict
import os

from django.http.response import Http404, HttpResponse
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.shortcuts import get_object_or_404

from mezzanine.utils.views import paginate

import docmeta.models as dm


class RootCategoriesView(TemplateView):
    template_name = 'docmeta/category_roots.html'
    categories = dm.get_root_categories()

    def get_context_data(self, **kwargs):
        context = super(RootCategoriesView, self).get_context_data(**kwargs)
        context['categories'] = self.categories
        context['document_list'] = dm.get_orphan_documents()
        return context


class DocumentListView(ListView):
    model = dm.Document
    mezz_paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super(DocumentListView, self).get_context_data(**kwargs)
        context['document_list'] = paginate(
            context['document_list'],
            self.request.GET.get("page", 1),
            self.mezz_paginate_by,
            7)
        return context

    def get_queryset(self):
        queryset = super(DocumentListView, self).get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(status=dm.CONTENT_STATUS_PUBLISHED)
        return queryset


class DocumentDuplicatesView(ListView):
    model = dm.Document
    mezz_paginate_by = 10
    template_name = 'docmeta/document_duplicates.html'

    def get_context_data(self, **kwargs):
        context = super(DocumentDuplicatesView, self).get_context_data(**kwargs)
        context['sha_document_list'] = paginate(
            self.get_sha_document_list(context['document_list']),
            self.request.GET.get("page", 1),
            self.mezz_paginate_by,
            7)
        return context

    @staticmethod
    def get_sha_document_list(documents):
        sha_dict = defaultdict(list)
        for document in documents:
            if document.sha is None:
                document.update_sha()
                document.save()
            sha_dict[document.sha[:8]].append(document)

        # Remove all entries with just one document
        for sha, documents in list(sha_dict.items()):  # list avoids mutating dict while iterating it
            if not documents[1:]:
                del sha_dict[sha]

        return sha_dict.items()


class DocumentDeleteView(DeleteView):
    model = dm.Document

    def get_success_url(self):
        return self.request.GET['next']


class CategoryView(DocumentListView):
    template_name = 'docmeta/category.html'
    categories = []

    def get_queryset(self):
        qs = super(CategoryView, self).get_queryset()
        return qs.filter(categories=self.categories[-1])

    def get_context_data(self, **kwargs):
        context = super(CategoryView, self).get_context_data(**kwargs)
        context['category'] = self.categories[-1]
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            self.categories = dm.categories_from_slugs(kwargs['category_slugs'].split('/'))
        except dm.DocumentCategory.DoesNotExist:
            raise Http404

        return super(CategoryView, self).dispatch(request, *args, **kwargs)


class DocumentDetailView(DetailView):
    model = dm.Document

    def get_object(self, queryset=None):
        obj = super(DocumentDetailView, self).get_object(queryset)
        if not self.request.user.is_staff and obj.status != dm.CONTENT_STATUS_PUBLISHED:
            raise Http404
        return obj


def download(request, slug):
    """
    Download the file
    :param request:
    :param slug:
    :return: response
    """

    document = get_object_or_404(dm.Document, slug=slug)
    filename = os.path.basename(document.source_file.name)

    response = HttpResponse(document.source_file, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)

    return response