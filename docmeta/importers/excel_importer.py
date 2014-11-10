import os
from collections import defaultdict
from openpyxl import load_workbook

import docmeta.models as dm


class MoreThanOneDocumentFoundError(Exception):
    pass


class NoDocumentFoundError(Exception):
    pass


class XLImporter(object):
    heading_row = 1  # Why :(

    # field_spec is a (<column_name>, <transform_method_suffix> . <method args>) for the field.
    column_specs = [
        (u'URL', 'm2m', {'field': 'url', 'model': dm.Url}),
        (u'URL-alt', 'm2m', {'field': 'url', 'model': dm.Url}),
        (u'Date Received by CCCS Team', 'date', {'field': 'date_received'}),
        (u'Received by CCCS Team Member', 'fk_receiver', {}),
        (u'Distribution', 'fk_distribution', {}),
        (u'CCCS folder - orig', None, {}),
        (u'sub-folder - orig', None, {}),
        (u'original file name', None, {}),
        (u'original file name -alt', 'o2m_filename', {}),
        (u'revised file name', 'o2m_filename', {}),
        (u'BIBTEX entry type', 'fk_bibtex_entry_type', {}),
        (u'CCCS entry type', 'fk_cccs_entry_type', {}),
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
            if getattr(self, transform_methodname)(document, column_name, row, **transform_kwargs):
                changed = True

        if changed:
            document.save()

    @staticmethod
    def transform_m2m(document, column_name, row, field, model):
        """
        Add m2m named element if it does not exist and add it to document field.
        The addition can be performed repeatedly without problem.
        :param document: docmeta document model object
        :param column_name: name of column in row relating to this transform
        :param row: entire row of raw data for this metadata update
        :param field: document field name relating to this transform
        :param model: model class for m2m target relation
        :return: Boolean - True if document object has changed
        """
        name = row[column_name]
        if name is None:
            return False
        related_object, created = model.objects.get_or_create(name=name)
        if created:
            related_object.save()
        getattr(document, field).add(related_object)
        return False  # m2m does not affect document

    @staticmethod
    def transform_copy(document, column_name, row, field):
        """
        Copy raw string value into the named field

        :param document: docmeta document model object
        :param column_name: name of column in row relating to this transform
        :param row: entire row of raw data for this metadata update
        :param field: document field name relating to this transform
        :return: Boolean - True if document object has changed
        """
        value = row[column_name]
        if value is None:
            return False

        if value != getattr(document, field):
            setattr(document, field, value)
            return True

        return False

    def transform_fk_receiver(self, document, column_name, row):
        pass

    def transform_fk_distribution(self, document, column_name, row):
        pass

    def transform_o2m_filename(self, document, column_name, row):
        pass

    def transform_fk_bibtex_entry_type(self, document, column_name, row):
        pass

    def transform_fk_cccs_entry_type(self, document, column_name, row):
        pass

    def transform_tag(self, document, column_name, row):
        pass

    def transform_copy_int(self, document, column_name, row, field):
        pass

    def transform_countries(self, document, column_name, row):
        pass

    def transform_publication_date(self, document, column_name, row):
        pass

    def transform_subcategories(self, document, column_name, row, root):
        pass

    def transform_date(self, document, column_name, row, field):
        pass