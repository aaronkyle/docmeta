import os
import hashlib
import re
from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from mezzanine.core.models import Displayable, RichText, CONTENT_STATUS_DRAFT, CONTENT_STATUS_PUBLISHED
from taggit.managers import TaggableManager

from storages.backends.s3boto import S3BotoStorage

from categories.base import (MPTTModel,
                             TreeForeignKey,
                             CategoryManager,
                             TreeManager,
                             slugify,
                             SLUG_TRANSLITERATOR,  # Showing incorrect because of PyCharm bug
                             force_unicode)


def sha1(f):
    sha = hashlib.sha1()
    while True:
        chunk = f.read(4096)
        if not chunk:
            break
        sha.update(chunk)
    return sha.hexdigest()


class UniqueNamed(models.Model):
    name = models.CharField(max_length=512, unique=True)
    plural_name = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __unicode__(self):
        return u"{0}".format(self.name)

    @property
    def plural(self):
        if self.plural_name is None or len(self.plural_name) == 0:
            return u"{0}s".format(self.name)
        else:
            return self.plural_name


class DocumentCategory(MPTTModel):
    """
    Largely a copy of categories.models.CategoryBase because we needed bigger fields.
    Refactor with own django-categories/pull request if we have to do more with this :(
    """
    parent = TreeForeignKey('self',
                            blank=True,
                            null=True,
                            related_name='children',
                            verbose_name=_('parent'))
    name = models.CharField(max_length=512, verbose_name=_('name'))
    slug = models.SlugField(max_length=512, verbose_name=_('slug'))
    active = models.BooleanField(default=True, verbose_name=_('active'))

    objects = CategoryManager()
    tree = TreeManager()

    def save(self, *args, **kwargs):
        """
        While you can activate an item without activating its descendants,
        It doesn't make sense that you can deactivate an item and have its
        decendants remain active.
        """
        if not self.slug:
            self.slug = slugify(SLUG_TRANSLITERATOR(self.name))[:50]

        super(DocumentCategory, self).save(*args, **kwargs)

        if not self.active:
            for item in self.get_descendants():
                if item.active != self.active:
                    item.active = self.active
                    item.save()

    def __unicode__(self):
        ancestors = self.get_ancestors()
        return '/'.join([force_unicode(i.name) for i in ancestors] + [self.name, ])

    class Meta:
        unique_together = ('parent', 'name')
        ordering = ('tree_id', 'lft')
        verbose_name_plural = 'document categories'

    class MPTTMeta:
        order_insertion_by = 'name'

    def get_absolute_url(self):
        return reverse("document-category", args=('/'.join(self.category_slugs),))

    @property
    def category_slugs(self):
        category_slugs = [self.slug]
        parent = self.parent
        while parent:
            category_slugs.insert(0, parent.slug)
            parent = parent.parent
        return category_slugs


class BibTexEntryType(UniqueNamed):
    class Meta:
        verbose_name = 'BIBTEX Entry Type'
        verbose_name_plural = 'BIBTEX Entry Types'


class CCCSEntryType(UniqueNamed):
    class Meta:
        verbose_name = 'CCCS Entry Type'
        verbose_name_plural = 'CCCS Entry Types'


class Url(UniqueNamed):
    class Meta:
        verbose_name = "URL"
        verbose_name_plural = "URLs"

Url._meta.get_field('name').verbose_name = 'URL String'


class Author(UniqueNamed):
    class Meta:
        verbose_name = 'Author(s)'
        verbose_name_plural = 'Author(s)'


class Editor(UniqueNamed):
    class Meta:
        verbose_name = 'Editor(s)'
        verbose_name_plural = 'Editor(s)'


class Document(RichText, Displayable):
    name = models.CharField(max_length=512, unique=True, default='')  # default is just to feed South
    source_file = models.FileField(max_length=512, upload_to='documents/%Y/%m/%d', storage=S3BotoStorage())
    source_file_created = models.DateTimeField(null=True, blank=True)
    source_file_modified = models.DateTimeField(null=True, blank=True)
    sha = models.CharField(max_length=40, null=True, blank=True)
    authors = models.ManyToManyField(Author, related_name='documents')
    editors = models.ManyToManyField(Editor, related_name='documents')
    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    day = models.IntegerField(null=True, blank=True)
    chapter = models.CharField(max_length=256, null=True, blank=True)
    journal = models.CharField(max_length=256, null=True, blank=True)
    volume = models.CharField(max_length=256, null=True, blank=True)
    issue = models.CharField(max_length=256, null=True, blank=True)
    pages = models.CharField(max_length=256, null=True, blank=True)
    series = models.CharField(max_length=256, null=True, blank=True)
    language = models.CharField(max_length=256, null=True, blank=True)
    article_title = models.CharField(max_length=512, null=True, blank=True,
                                     help_text="BibTex Article Title")
    publishing_agency = models.CharField(max_length=256, null=True, blank=True)
    publishing_house = models.CharField(max_length=256, null=True, blank=True)
    publisher_city = models.CharField(max_length=256, null=True, blank=True)
    publisher_address = models.CharField(max_length=256, null=True, blank=True)
    cccs_source_path = models.CharField(max_length=512, null=True, blank=True)
    bibtex_entry_type = models.ForeignKey(BibTexEntryType, null=True, blank=True)
    cccs_entry_type = models.ForeignKey(CCCSEntryType, null=True, blank=True)
    countries = models.CharField(max_length=512, null=True, blank=True)
    tags = TaggableManager(blank=True)
    categories = models.ManyToManyField(DocumentCategory, related_name='documents')
    url = models.ManyToManyField(Url, related_name='documents')
    date_received = models.DateField(null=True, blank=True)
    receiving_team_member = models.CharField(max_length=128, null=True, blank=True)
    regions = models.CharField(verbose_name='Region(s)', max_length=128, null=True, blank=True)
    document_id = models.CharField(verbose_name='Doc ID#/ISSN/ISBN', max_length=128, null=True, blank=True)
    annotation = models.CharField(verbose_name='Bibliographic annotation', max_length=128, null=True, blank=True)
    notes = models.TextField(verbose_name='Reviewer Notes', null=True, blank=True)

    search_fields = ("content", "title", "tags__name")

    class Meta:
        ordering = ('title',)

    def get_absolute_url(self):
        return reverse("document-detail", args=(self.slug,))

    @property
    def tag_string(self):
        return ', '.join([tag.name for tag in self.tags.all()])

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)

    def update_sha(self):
        try:
            self.source_file.open()
            try:
                self.sha = sha1(self.source_file)
            finally:
                self.source_file.close()
        except IOError:
            self.sha = 'file missing'

    def unique_name(self):
        self.name = get_unique_name(self)

    def unique_title(self):
        self.title = get_unique_title(self.title)


Document._meta.get_field('content').verbose_name = 'Abstract/Description of content'


class DocumentFileName(models.Model):
    document = models.ForeignKey(Document)
    name = models.CharField(max_length=512)

    class Meta:
        unique_together = ('document', 'name')
        ordering = ('document', 'name')


def categories_from_slugs(slugs):
    parent = None
    result = list()
    for slug in slugs:
        category = DocumentCategory.objects.get(slug=slug, parent=parent)
        result.append(category)
        parent = category
    return result


def verify_categories(category_names, create_if_absent=False):
    """
    Create the category_names ancestral tree if it does not already exist
    :param category_names: list of category names with root at the top
    :return: list of the actual categories corresponding to the names.
    """
    parent = None
    result = list()
    for category_name in category_names:
        try:
            category = DocumentCategory.objects.get(
                name=category_name,
                parent=parent)
        except DocumentCategory.DoesNotExist:
            if create_if_absent:
                category = DocumentCategory(
                    name=category_name,
                    parent=parent)
                category.save()
            else:
                raise
        result.append(category)
        parent = category
    return result


def get_root_categories():
    return DocumentCategory.tree.root_nodes()


def get_orphan_documents():
    return Document.objects.filter(categories=None)


def get_unique_title(title):
    """
    Return unique version of title, altering it if necessary by adding (or incrementing) a suffixed integer in
    brackets. For example, if the matching title 'About' already exists, return 'About (1)' Altered titles will
    result in numbers being re-used. This is done as a function because it is also used in migration
    """
    return get_unique_field_value(title, Document.objects, 'title')


def get_unique_name(document):
    """
    Return unique version of name field for document.
    """
    if document.name:
        candidate = document.name
    else:
        try:
            filename = document.documentfilename_set.first().name
            candidate = os.path.splitext(os.path.basename(filename))[0]
        except DocumentFileName.DoesNotExist:
            candidate = document.title
    return get_unique_field_value(candidate, Document.objects, 'name')


def get_unique_field_value(candidate, object_manager, field_name):
    """
    Return unique version of field_name candidate, altering it if necessary by adding (or incrementing) a suffixed
    integer in brackets. For example, if the matching candidate 'About' already exists, return 'About (1)'.
    """
    pat = re.compile(r'(.*\()(\d+)(\))$')  # (prefix, existing_num, suffix) if successful

    def generate_new_candidate(candidate):
        match = re.match(pat, candidate)
        if match:  # already has a number so increment it
            num = int(match.groups()[1]) + 1
            new_candidate = match.groups()[0] + str(num) + match.groups()[2]
        else:  # Add the first incremental number
            new_candidate = "{0} (1)".format(candidate)
        return new_candidate

    if object_manager.filter(**{field_name: candidate})[1:]:  # more than one so not unique
        while object_manager.filter(**{field_name: candidate}):  # any matches
            candidate = generate_new_candidate(candidate)

    return candidate