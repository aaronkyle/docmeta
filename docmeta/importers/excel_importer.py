import os
import datetime
import difflib
import dateutil.parser as dp

from collections import defaultdict
from openpyxl import load_workbook

from django.contrib.auth.models import User

import docmeta.models as dm


class MoreThanOneDocumentFoundError(Exception):
    pass


class NoDocumentFoundError(Exception):
    pass


class XLImporter(object):
    heading_row = 1  # Why :(

    # field_spec is a (<column_name>, <transform_method_suffix>, <method kwargs>) for the field.
    column_specs = [
        (u'URL', 'm2m', {'field': 'url', 'model': dm.Url}),
        (u'URL-alt', 'm2m', {'field': 'url', 'model': dm.Url}),
        (u'Date Received by CCCS Team', 'date', {'field': 'date_received'}),
        (u'Received by CCCS Team Member', 'fk_receiver', {}),
        (u'Distribution', 'fk_named', {'field': 'distribution', 'model': dm.Distribution}),
        (u'CCCS folder - orig', None, {}),
        (u'sub-folder - orig', None, {}),
        (u'original file name', None, {}),
        (u'original file name -alt', 'o2m_filename', {}),
        (u'revised file name', 'o2m_filename', {}),
        (u'BIBTEX entry type', 'fk_named', {'field': 'bibtex_entry_type', 'model': dm.BibTexEntryType}),
        (u'CCCS entry type', 'fk_named', {'field': 'cccs_entry_type', 'model': dm.CCCSEntryType}),
        (u'attribute tag', 'tag', {}),
        (u'Country / Countries', 'countries', {}),
        (u'Region(s)', 'copy', {'field': 'regions'}),
        (u'Year', 'copy_int', {'field': 'year'}),
        (u'Month', 'copy_int', {'field': 'month'}),
        (u'Day', 'copy_int', {'field': 'day'}),
        (u'Date Created / Published', 'publication_date', {}),
        (u'Author(s)', 'm2m', {'field': 'authors', 'model': dm.Author}),
        (u'Editor(s)', 'm2m', {'field': 'editors', 'model': dm.Editor}),
        (u'Book Title', 'copy', {'field': 'booktitle'}),
        (u'Book Chapter', 'copy', {'field': 'chapter'}),
        (u'Document / Article Title', 'copy', {'field': 'title'}),
        (u'Journal / Publication', 'copy', {'field': 'journal'}),
        (u'Vol', 'copy', {'field': 'volume'}),
        (u'Issue', 'copy', {'field': 'copy'}),
        (u'Pages', 'copy', {'field': 'pages'}),
        (u'Series', 'copy', {'field': 'series'}),
        (u'Language', 'copy', {'field': 'language'}),
        (u'Publishing Agency', 'copy', {'field': 'publishing_agency'}),
        (u'Publishing House', 'copy', {'field': 'publishing_house'}),
        (u"Publisher's City", 'copy', {'field': 'publisher_city'}),
        (u"Publisher's Address", 'copy', {'field': 'publisher_address'}),
        (u'Doc ID#', 'copy', {'field': 'document_id'}),
        (u'ISSN / ISBN', 'copy', {'field': 'document_id'}),
        (u'Abstract', 'copy', {'field': 'content'}),
        (u'Bibliographic Annotation', 'copy', {'field': 'annotation'}),
        (u'Reviewer Notes', 'copy', {'field': 'notes'}),
        (u'Significance to Client Document Development [short tags]',
         'subcategories', {'root': 'significance/short'}),
        (u'Significance to Client Document Development [descriptive]',
         'subcategories', {'root': 'significance/descriptive'}),
        (u'L1 Geographical Admin. Cat.', 'copy', {'field': 'l1'}),
        (u'L2 Geographical Admin. Cat.', 'copy', {'field': 'l2'}),
        (u'L3 Geographical Admin. Cat.', 'copy', {'field': 'l3'}),
        (u'L4 Geographical Admin. Cat.', 'copy', {'field': 'l4'}),
        (u'L5 Geographical Admin. Cat.', 'copy', {'field': 'l5'})]
    
    def __init__(self, source_file):
        super(XLImporter, self).__init__()
        self.workbook = load_workbook(source_file)
        self.inpex_docs_ws = self.workbook.get_sheet_by_name('INPEX docs')

        document_lookup = defaultdict(list)
        for document_filename in dm.DocumentFileName.objects.all():
            document_lookup[os.path.basename(document_filename.name)].append(document_filename.document)
        self.document_lookup = document_lookup

        user_lookup = dict()
        for user in User.objects.all():
            user_lookup[user.username.lower()] = user
            long_name = u'{0} {1}'.format(user.first_name, user.last_name).lower()
            user_lookup[long_name] = user
        self.user_lookup = user_lookup

        named_relations = dict()
        model_classes = [kwargs['model'] for _, suffix, kwargs in self.column_specs if suffix == 'fk_named']
        for model_class in model_classes:
            model_lookup = dict()
            named_relations[model_class] = model_lookup
            for obj in model_class.objects.all():
                model_lookup[obj.name.strip().lower()] = obj
        self.named_relations = named_relations

    def find_user(self, raw_name):
        key = raw_name.strip().lower()
        try:
            return self.user_lookup[key]
        except KeyError:
            close_enough = difflib.get_close_matches(key, self.user_lookup.keys(), 1)
            if close_enough:
                return self.user_lookup[close_enough[0]]
            else:
                raise

    def find_named_relation(self, model_class, raw_name):
        key = raw_name.strip().lower()
        try:
            return self.named_relations[model_class][key]
        except KeyError:
            close_enough = difflib.get_close_matches(key, self.named_relations[model_class].keys(), 1)
            if close_enough:
                return self.named_relations[model_class][close_enough[0]]
            else:
                new_relation = model_class(name=raw_name)
                new_relation.save()
                self.named_relations[model_class][key] = new_relation
                return new_relation

    @staticmethod
    def get_worksheet_dicts(ws, column_names, heading_row=0, starting_row=1):

        # create column_name, column_index pairings for the extraction
        column_headings = [c.value for c in ws.rows[heading_row]]
        for column_name in column_names:
            if column_name not in column_headings:
                raise Exception("{0} is not a column heading".format(column_name))
        column_info = [(column_name, column_headings.index(column_name)) for column_name in column_names]

        return [{column_name: row[column_index].value
                 for (column_name, column_index) in column_info}
                for row in ws.rows[starting_row:]]

    def find_column_headings(self):
        return [c.value for c in self.inpex_docs_ws.rows[self.heading_row] if c.value is not None]

    def load(self):
        column_names = [s[0] for s in self.column_specs]
        rows = self.get_worksheet_dicts(self.inpex_docs_ws, column_names, self.heading_row, self.heading_row+1)
        for row in rows:
            for document in self.document_lookup[row[u'original file name']]:
                self.load_document_metadata(document, row)

    def load_document_metadata(self, document, row):
        changed = False
        for spec in self.column_specs:
            column_name, transform_suffix, transform_kwargs = spec
            if transform_suffix is None:
                continue
            transform_methodname = 'transform_{0}'.format(transform_suffix)
            raw_datum = row[column_name]
            if raw_datum is None:
                continue
            if getattr(self, transform_methodname)(document, raw_datum, **transform_kwargs):
                changed = True

        if changed:
            document.save()

    @staticmethod
    def transform_m2m(document, raw_name, field, model):
        """
        Add m2m named element if it does not exist and add it to document field.
        The addition can be performed repeatedly without problem.
        :param document: docmeta document model object
        :param raw_name: supplied name
        :param field: document field name relating to this transform
        :param model: model class for m2m target relation
        :return: Boolean - True if document object has changed
        """
        related_object, created = model.objects.get_or_create(name=raw_name)
        if created:
            related_object.save()
        getattr(document, field).add(related_object)
        return False  # m2m does not affect document

    @staticmethod
    def transform_copy(document, raw_value, field):
        """
        Copy raw string value into the named field
        :param document: docmeta document model object
        :param raw_value: supplied value
        :param field: document field name relating to this transform
        :return: Boolean - True if document object has changed
        """
        if raw_value != getattr(document, field):
            setattr(document, field, raw_value)
            return True

        return False

    def transform_fk_receiver(self, document, raw_receiver):
        """
        Find matching user if possible using supplied text.
        Failed matches are ignored.
        :param document: docmeta document model object
        :param raw_receiver: supplied name string for receiver
        :return: Boolean - True if document object has changed
        """
        try:
            document.receiver = self.find_user(raw_receiver)
            return True
        except KeyError:  # no matching user found
            return False

    def transform_fk_named(self, document, raw_relation_name, field, model):
        """
        Find matching named object if possible using supplied text.
        named object is created if not found.
        :param document: docmeta document model object
        :param raw_relation_name: name of column in row relating to this transform
        :param field: field on document
        :param model: model class of relation
        :return: Boolean - True if document object has changed
        """
        relation = self.find_named_relation(model_class=model, raw_name=raw_relation_name)
        if getattr(document, field) != relation:
            setattr(document, field, relation)
            return True

        return False

    @staticmethod
    def transform_tag(document, raw_tag_string):
        """
        Add specified tags to document (tags are separated in raw_tag_string by semi colons)
        :param document: docmeta document model object
        :param raw_tag_string: semi colon delimited list of tags
        :return: Boolean - True if document object has changed
        """
        tags = raw_tag_string.split(';')
        document.tags.add(*tags)
        return False  # No change to document model

    @staticmethod
    def transform_copy_int(document, raw_int, field):
        """
        Copy raw integer value into the named field
        :param document: docmeta document model object
        :param raw_int: supplied value
        :param field: document field name relating to this transform
        :return: Boolean - True if document object has changed
        """
        try:
            use_int = int(raw_int)
        except ValueError:
            return False

        if use_int != getattr(document, field):
            setattr(document, field, use_int)
            return True

        return False

    def transform_countries(self, document, raw_countries):
        pass

    @staticmethod
    def transform_publication_date(document, raw_publication_date):
        """
        Break the publication date into the year/month/day fields
        :param document: docmeta document model object
        :param raw_publication_date: supplied value
        :return: Boolean - True if document object has changed
        """
        try:
            year = int(raw_publication_date)
            if year != document.year:
                document.year = year
                return True
            else:
                return False
        except (ValueError, TypeError):
            pass

        if isinstance(raw_publication_date, datetime.datetime):
            # openpyxl managed to parse it
            publication_date = raw_publication_date
        else:
            # parse using dateutil
            publication_date = dp.parse(raw_publication_date)
        changed = False

        for attname in ('year', 'month', 'day'):
            if getattr(publication_date, attname) != getattr(document, attname):
                setattr(document, attname, getattr(publication_date, attname))
                changed = True

        return changed

    @staticmethod
    def transform_subcategories(document, raw_subcategories, root):
        """
        Break the publication date into the year/month/day fields
        :param document: docmeta document model object
        :param raw_subcategories: string of subcategorynames separated by semicolons
        :return: Boolean - True if document object has changed
        """
        parent = dm.verify_categories(root.split('/'), create_if_absent=True)[-1]
        subcategory_names = [sc.strip() for sc in raw_subcategories.split(';')]

        for subcategory_name in subcategory_names:
            document.categories.add(dm.verify_categories([parent.name, subcategory_name], create_if_absent=True)[-1])

    @staticmethod
    def transform_date(document, raw_date, field):
        """
        Converte and assign the date
        :param document: docmeta document model object
        :param raw_date if document object has changed
        :param field: document field name relating to this transform
        :return: Boolean - True if document object has changed
        """
        if isinstance(raw_date, datetime.datetime):
            # openpyxl has managed to parse it
            actual_date = raw_date
        else:
            # parse using dateutil
            try:
                actual_date = dp.parse(raw_date)
            except TypeError:  # give up
                return False

        if actual_date != getattr(document, field):
            setattr(document, field, actual_date)
            return True
        return False

    def transform_o2m_filename(self, document, raw_filename):
        pass