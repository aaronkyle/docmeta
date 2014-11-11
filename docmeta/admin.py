from django.contrib import admin
from django.forms import TextInput
from django.db import models

from categories.admin import CategoryBaseAdmin

import docmeta.models as dm


class DocumentCategoryAdmin(CategoryBaseAdmin):
    pass

admin.site.register(dm.DocumentCategory, DocumentCategoryAdmin)


class DocumentFileNameInline(admin.TabularInline):
    model = dm.DocumentFileName
    extra = 1
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'style': 'width: 100em'})}
    }


class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'created', 'updated']
    list_filter = ['tags']
    fieldsets = ((None, {'fields': ('name',
                                    'tags',
                                    'categories',
                                    'title',
                                    'content',
                                    'source_file',
                                    'created',
                                    'updated',
                                    'source_file_created',
                                    'source_file_modified',
                                    'sha',
                                    'authors',
                                    'editors')}),
                 ('CCCS', {'classes': ('collapse-closed',),
                           'fields': ('date_received',
                                      'receiver',
                                      'notes',
                                      'distribution',
                                      'bibtex_entry_type',
                                      'cccs_entry_type',
                                      'regions',
                                      'countries',
                                      'l1',
                                      'l2',
                                      'l3',
                                      'l4',
                                      'l5')}),
                 ('Bibliographic Data', {'classes': ('collapse-closed',),
                                         'fields': ('booktitle',
                                                    'eprint',
                                                    'howpublished',
                                                    'annotation',
                                                    'year',
                                                    'month',
                                                    'day',
                                                    'chapter',
                                                    'journal',
                                                    'volume',
                                                    'issue',
                                                    'pages',
                                                    'series',
                                                    'language',
                                                    'publishing_agency',
                                                    'publishing_house',
                                                    'publisher_city',
                                                    'publisher_address',
                                                    'edition',
                                                    'institution',
                                                    'crossref',
                                                    'school',
                                                    'organization')}),
                 ('Metadata', {'classes': ('collapse-closed',),
                               'fields': ('_meta_title',
                                          'slug',
                                          'short_url',
                                          'description',
                                          'gen_description',
                                          'keywords',
                                          'publish_date',
                                          'expiry_date')}))
    filter_horizontal = ('categories', 'authors', 'editors')
    readonly_fields = ('created', 'updated', 'sha', 'source_file_created', 'source_file_modified')
    inlines = (DocumentFileNameInline,)

    def save_model(self, request, document, form, change):
        super(DocumentAdmin, self).save_model(request, document, form, change)
        filename, created = dm.DocumentFileName.objects.get_or_create(name=request.FILES['source_file'].name,
                                                                      document=document)
        if created:
            filename.save()
        document.filenames.add(filename)


class DocumentFileNameAdmin(admin.ModelAdmin):
    list_display = ('document', 'name')


admin.site.register(dm.DocumentFileName, DocumentFileNameAdmin)

admin.site.register(dm.Document, DocumentAdmin)
admin.site.register(dm.BibTexEntryType, admin.ModelAdmin)
admin.site.register(dm.CCCSEntryType, admin.ModelAdmin)
admin.site.register(dm.Distribution, admin.ModelAdmin)
admin.site.register(dm.Url, admin.ModelAdmin)
admin.site.register(dm.Author, admin.ModelAdmin)
admin.site.register(dm.Editor, admin.ModelAdmin)