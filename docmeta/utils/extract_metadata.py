import os
import datetime
import re

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from dateutil.tz import tzutc, tzoffset


def transform_text(text):
    """
    Text may be arbitrarily in utf16 or asci format. Take whatever and return unicode.
    :return: unicode version of text
    """
    try:
        return u'{0}'.format(text)
    except UnicodeDecodeError:
        return u'{0}'.format(text.decode('utf16'))

pdf_date_pattern = re.compile(''.join([
    r"(D:)?",
    r"(?P<year>\d\d\d\d)",
    r"(?P<month>\d\d)",
    r"(?P<day>\d\d)",
    r"(?P<hour>\d\d)",
    r"(?P<minute>\d\d)",
    r"(?P<second>\d\d)",
    r"(?P<tz_offset>[+-zZ])?",
    r"(?P<tz_hour>\d\d)?",
    r"'?(?P<tz_minute>\d\d)?'?"]))


def transform_date(date_str):
    """
    Convert a pdf date such as "D:20120321183444+07'00'" into a usable datetime
    http://www.verypdf.com/pdfinfoeditor/pdf-date-format.htm
    (D:YYYYMMDDHHmmSSOHH'mm')
    :param date_str: pdf date string
    :return: datetime object
    """
    global pdf_date_pattern
    match = re.match(pdf_date_pattern, date_str)
    if match:
        date_info = match.groupdict()

        for k, v in date_info.iteritems():  # transform values
            if v is None:
                pass
            elif k == 'tz_offset':
                date_info[k] = v.lower()  # so we can treat Z as z
            else:
                date_info[k] = int(v)

        if date_info['tz_offset'] in ('z', None):  # UTC
            date_info['tzinfo'] = tzutc()
        else:
            multiplier = 1 if date_info['tz_offset'] == '+' else -1
            date_info['tzinfo'] = tzoffset(None, multiplier*(3600 * date_info['tz_hour'] + 60 * date_info['tz_minute']))

        for k in ('tz_offset', 'tz_hour', 'tz_minute'):  # no longer needed
            del date_info[k]

        return datetime.datetime(**date_info)

metadata_map = {
    'Author': ('author', transform_text),
    'ModDate': ('source_file_modified', transform_date),
    'CreationDate': ('source_file_created', transform_date),
    'Title': ('title', transform_text)}


def pdf_metadata(document):
    """
    Return dict of metadata in pdf file fp.
    :param document: docmeta Document model object
    :return: dict of metadata
    """
    global metadata_map
    try:
        document.source_file.open()
        parser = PDFParser(document.source_file)
        doc = PDFDocument(parser)
        result = dict()
        for k, v in doc.info[0].iteritems():
            if k in metadata_map:
                (metadata_field, transform) = metadata_map[k]
                result[metadata_field] = transform(v)
        return result
    finally:
        document.source_file.close()

extractors = {
    'pdf': pdf_metadata
}


def extract_metadata(document):
    global extractors
    basename = os.path.basename(document.source_file.name)
    (name, ext) = os.path.splitext(basename)
    ext = ext[1:]
    if ext in extractors:
        return extractors[ext](document)
    else:
        return {}