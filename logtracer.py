#!./system/bin/python
# Author: Larry Castro
# Version: 1.8
# Last modification: 02-12-20
# This program will take a physical log file for analysis
#
import argparse
import hashlib
import json
import os
import re
import textwrap
from collections import OrderedDict
from multiprocessing import Pool

from ahocorapy.keywordtree import KeywordTree
from sqlalchemy import and_

# from .home.larry.IdeaProjects.support import Table, Configs

# Global variables
log_file = None
flow_id = None
transaction_id = None
logfile_format = None
kwtree = None
database = None
party_found = False

# ================================== Support import ==================================


class Table:
    """
    This class create a table for a list; it's possible to add the borders
    """
    line_details = []

    def __init__(self, column_delimiter='|', row_delimiter='-', table_corners='+', table_name=None, table_style=None,
                 anchor_link=None, auto_number=False, table_class=None, no_headers=False, data=None, output_style=None):
        self.id_header = {}
        self.args_header = {}
        self.table_name = table_name
        self.table_anchor_link = None
        self.headers = OrderedDictX()
        self.cell_attributtes = {}
        self.rows = []
        self.row = []
        self.column_delimiter = column_delimiter
        self.row_delimiter = row_delimiter
        self.table_corners = table_corners
        self.title_header_array = []
        self.row_line_array = []
        self.header_title = ''
        self.line_delimiter = ''
        self.auto_number = auto_number
        self.table_class = table_class
        self.cell_match = {}
        self.cell_color_map = {}
        self.data = data
        self.filters = {}
        self.orderby = None
        self.web_style = True
        self.output_style = output_style

        # Check if we have setup a filter on this table
        #
        if Configs.get_config("TABLE_CONFIG", self.table_name, similar=True):
            # Check if we have a filter for this table/column
            if "FILTER_ON" in Configs.get_config("TABLE_CONFIG", self.table_name, similar=True):
                filters = Configs.get_config("TABLE_CONFIG", self.table_name, similar=True)["FILTER_ON"]
                for each_new_filter in filters:
                    if each_new_filter not in self.filters:
                        self.add_filter(each_new_filter)
                    # Add default filter 'all' for this column
                    self.add_filter(each_new_filter, 'all')

        # Check if we have setup ordering over this table...
        if Configs.get_config("TABLE_CONFIG", self.table_name, similar=True):
            # Adding a mark to each header that will allow sorting...
            table_sorting = Configs.get_config("TABLE_CONFIG", self.table_name, similar=True)
            if "ORDER_BY" in table_sorting:
                self.orderby = table_sorting["ORDER_BY"]

        # Internal setting (this is being set by the method)
        #
        # Need to keep this code to allow ASCII tables to be created looking forward to slack bot or teamcity bot
        if table_style:
            self.row_delimiter = ' '
            self.table_corners = ' '
            self.column_delimiter = '|'
            if table_style == 'simple':
                self.column_delimiter = '|'
                self.row_delimiter = '-'
                self.table_corners = '+'
            if table_style == 'full':
                self.column_delimiter = '|'
                self.row_delimiter = '-'
                self.table_corners = '+'
            if table_style == 'notable':
                self.row_delimiter = ' '
                self.table_corners = ''
                self.column_delimiter = ' '
        else:
            self.row_delimiter = ' '
            self.table_corners = ' '
            self.column_delimiter = '|'

        # Manual override (this is being set on config file)
        if Configs.get_config('TABLE_STYLE'):
            if Configs.get_config('TABLE_STYLE') == 'SIMPLE_TABLES':
                self.row_delimiter = ' '
                self.table_corners = ' '
                self.column_delimiter = '|'
            if Configs.get_config('TABLE_STYLE') == 'NO_TABLES':
                self.row_delimiter = ' '
                self.table_corners = ''
                self.column_delimiter = ' '
            if Configs.get_config('TABLE_STYLE') == 'FULL_TABLES':
                self.column_delimiter = '|'
                self.row_delimiter = '-'
                self.table_corners = '+'

        # Command line override (this is being set at the command line)
        if args.simple_tables:
            self.row_delimiter = ' '
            self.table_corners = ' '
            self.column_delimiter = '|'
        if args.no_tables:
            self.row_delimiter = ' '
            self.table_corners = ''
            self.column_delimiter = ' '
        if args.full_tables:
            self.column_delimiter = '|'
            self.row_delimiter = '-'
            self.table_corners = '+'
        #
        self.start_end_table_delimiter = None
        self.alt_table_corner = '+'
        self.alt_table_row_delimiter = '-'
        #
        #
        # Legacy table ASCII support

        #
        # setup any anchor link table may have to point into it.

        if anchor_link:
            self.table_anchor_link = Web.anchor_link(id=anchor_link, message=self.table_name)

    @staticmethod
    def add_table_line_details(line):
        """
        Will keep track which lines has detailed information
        :param line:
        :return: None
        """
        clear_line = re.sub('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});', '', line)
        line_hash = generate_hash(clear_line)
        if line_hash not in Table.line_details:
            Table.line_details.append(line_hash)

    @staticmethod
    def check_table_line_details(line):
        """
        Will check if given line has any details
        :param line: line to check
        :return: True if line has been marked with details, false otherwise
        """

        line_hash = generate_hash(line)
        if line_hash in Table.line_details:
            return True

        return False

    def add_filter(self, column_header, value=None):
        """

        :param column_header: column where filter is required
        :param value: all possible values that we can check on the filter
        :return: None
        """

        if column_header not in self.filters:
            if not self.filters:
                self.filters = {}

            self.filters[column_header] = []

        if value:
            if value not in self.filters[column_header]:
                self.filters[column_header].append(value)

    def has_filter(self, column_header=None):
        """
        Check if given header has filter applied
        :param column_header:
        :return: will return true if has filters false otherwise
        """

        if column_header:
            if isinstance(column_header, str) and "<br>" in column_header:
                column_header = column_header.replace("<br>", " ")

            if column_header in self.filters:
                return True
            else:
                return False

        if len(self.filters) > 0:
            return True
        else:
            return False

    def get_filter_options(self, column_header):
        """
        Will return list of options on given header
        :param column_header: header name to check
        :return: list of string representing all options allowed
        """

        if "<br>" in column_header:
            column_header = column_header.replace("<br>", " ")

        if column_header in self.filters:
            return self.filters[column_header]

        return None

    def able_to_orderby(self, column_header=None):
        """
        Check if given table or column has orderby set
        :param column_header:
        :return:
        """

        if not self.orderby:
            return False

        if column_header:
            if "<br>" in column_header:
                column_header = column_header.replace("<br>", " ")

            if column_header in self.orderby:
                return True
            else:
                return False

        else:
            if self.orderby:
                return True

        return False

    def create_title_header(self):
        """
        Generate headers and also division line
        :return:
        """

        wheader = Web(True)

        if self.table_name:
            if not self.table_anchor_link:
                # wheader.add_to_page('<tr><td colspan=%s><center><b>%s</b></center></td></tr>' %
                #                     (self.get_column_count(), self.table_name))
                wheader.add_to_page('<caption><h4>%s</h4></caption>' % self.table_name)
            else:
                # wheader.add_to_page('<tr><td colspan=%s><center><b>%s</b></center></td></tr>' %
                #                     (self.get_column_count(), self.table_anchor_link))
                wheader.add_to_page('<caption><h4>%s</h4></caption>' % self.table_anchor_link)

        return wheader.print_html()

    def create_title_header_ascii(self):
        """
        Generate headers and also division line
        :return:
        """
        balance = 0
        alt_row_line_array = []
        ignored_column = []
        alt_format_line_delimiter = None
        array_print = []
        for hd in self.headers.keys():
            # TODO: A way to detect when given table(TABLE_SETTINGS) name doesn't exist! [LOW-PRIORITY]
            #  problem is I'm not able to 'know' what tables are defined at system...
            #  so system will just ignore it for now... but will not print(any message)
            #  there're no way to detect if give table name exist or not to give a warning when user is asking
            #  for a table that doesn't exist...

            if Configs.get_config('TABLE_SETTINGS'):
                if self.table_name in Configs.get_config('TABLE_SETTINGS'):
                    for column in Configs.get_config('TABLE_SETTINGS')[self.table_name]:
                        if column in self.headers:
                            self.headers[column] = Configs.get_config('TABLE_SETTINGS')[self.table_name][column]
                        else:
                            if column not in ignored_column:
                                ignored_column.append(column)

            format_header_names = '{:%s%s}' % (self.get_header_justification(hd), self.get_header_length(None, hd))
            format_line_delimiter = '{:%s<%s}%s' % (self.row_delimiter, self.get_header_length(None, hd) - balance,
                                                    self.table_corners)
            if self.table_corners == ' ':
                alt_format_line_delimiter = '{:%s<%s}%s' % (self.alt_table_row_delimiter,
                                                            self.get_header_length(None, hd) - balance,
                                                            self.alt_table_corner)

            balance = 1
            self.title_header_array.append(format_header_names.format(hd))

            if self.table_corners == ' ' and alt_format_line_delimiter:
                alt_row_line_array.append(alt_format_line_delimiter.format(self.alt_table_row_delimiter))

            self.row_line_array.append(format_line_delimiter.format(self.row_delimiter))

            self.header_title = '%s%s%s' % (self.column_delimiter,
                                            self.column_delimiter.join(self.title_header_array),
                                            self.column_delimiter)

            self.line_delimiter = '%s%s' % (self.table_corners, self.row_delimiter.join(self.row_line_array))

        if ignored_column:
            printm('{{TABLE_SETTINGS}}: column {{%s}} does not exist on requested {{%s}} table, this setting'
                   ' will be ignored...', (','.join(ignored_column), self.table_name), msgtype.WARNING)

        if self.table_corners == ' ':
            self.start_end_table_delimiter = '%s%s' % (self.alt_table_corner,
                                                       self.alt_table_row_delimiter.join(alt_row_line_array))

        # if args.web_style:
        #     if Configs.get_config('WEB_SHEET_STYLE'):
        #         print(Configs.get_config('WEB_SHEET_STYLE'))
        #     print('<center>')
        #     if Configs.get_config('HTML_START_TABLE'):
        #         print(Configs.get_config('HTML_START_TABLE'))
        #     else:
        #         print('<table>')
        #
        #     if self.table_name:
        #         print('<tr><td colspan=%s><center><b>%s</b></center></td></tr>' % (
        #             self.get_column_count(), self.table_name))
        #         # print('<caption>%s</caption>' % self.table_name)
        #     return

        if self.table_name:  # and not args.web_style:
            title_format = '{:^%s}' % (len(self.line_delimiter),)
            title_line_format = '{:%s<%s}' % (self.alt_table_row_delimiter, len(self.line_delimiter) - 1)
            if self.start_end_table_delimiter or self.line_delimiter.strip():
                if self.output_style and self.output_style == "array":
                    array_print.append(title_line_format.format(self.alt_table_corner) + self.alt_table_corner)
                else:
                    print(title_line_format.format(self.alt_table_corner) + self.alt_table_corner)
            if self.output_style and self.output_style == "array":
                array_print.append('%s%s\b\b%s' % (self.column_delimiter,
                                                   title_format.format(self.table_name),
                                                   self.column_delimiter))
            else:
                print(
                    '%s%s\b\b%s' % (self.column_delimiter, title_format.format(self.table_name), self.column_delimiter))

        if not self.start_end_table_delimiter:
            if self.output_style and self.output_style == "array":
                array_print.append(self.line_delimiter)
                array_print.append(self.header_title)
                array_print.append(self.line_delimiter)
            else:
                print(self.line_delimiter)
                print(self.header_title)
                print(self.line_delimiter)
        else:
            if self.output_style and self.output_style == "array":
                array_print.append(self.start_end_table_delimiter)
                array_print.append(self.header_title)
                array_print.append(self.start_end_table_delimiter)
            else:
                print(self.start_end_table_delimiter)
                print(self.header_title)
                print(self.start_end_table_delimiter)

        if self.output_style and self.output_style == "array":
            return array_print

    def add_cell(self, cell):
        """
        Add a new cell into table, the rows are created automatically; when cell count reach lenght of header, a new
        row will be added.
        :param cell: cell content to add
        :return:
        """
        rw = 0

        if cell is None:
            cell = "**NO DATA**"
        if len(self.row) + 1 < len(self.headers.keys()):
            self.row.append(cell)
            rw = self.row.__len__()
        else:
            self.row.append(cell)
            self.rows.append(self.row)
            rw = self.row.__len__() + 1
            self.row = []

        if rw - 1 < len(self.get_headers()) and self.get_header(rw - 1) in self.id_header:
            ids = "%s-%s" % (rw - 1, cell)
            self.cell_attributtes[ids] = 'id="%s"' % (ids,)

        # Check if this table has more filters sets beside default one 'all'

        if self.auto_number:
            trw = rw - 1
        else:
            trw = rw
        header_name = self.get_header(trw, normalized=True)
        if isinstance(header_name, str):
            has_filter = self.has_filter(header_name)
            table_source = False
            if has_filter:
                table_filters = Configs.get_config("TABLE_CONFIG", sub_param=self.table_name, similar=True)["FILTER_ON"]
                if table_filters:
                    if "OPTIONS_SOURCE" in table_filters[header_name] and \
                            table_filters[header_name]["OPTIONS_SOURCE"] == "TABLE":
                        table_source = True
                # Add filter values...
                cellv = Table.get_cell_value(cell)
                if cellv and table_source:
                    self.add_filter(header_name, cellv)

    @staticmethod
    def get_cell_value(value):
        """
        Will return value content of cell, taking out any html tags on it...
        :param value: raw value to check
        :return: string with real value
        """
        match = None
        rgx = r'\>(.*)\<'

        if isinstance(value, str):
            match = re.search(rgx, value)

        if match:
            return match.group(1)

        return value

    def add_header(self, header_title, header_length, header_justification='^', column_justification='^',
                   id=None, args=None):
        """
        Add a header title
        :param header_title: Header title
        :param header_length: Maximum length, for the content on  this column, if content length > max length then
        content will be wrapped
        :param header_justification: Header justification use '<'(left),'^'(center),'>'(right)
        :param column_justification: Column justification use '<'(left),'^'(center),'>'(right)
        :return:
        """
        if id:
            self.id_header[header_title] = id
        if args:
            self.args_header[header_title] = args
        self.headers[header_title] = [header_length, header_justification, column_justification]

    def auto_numbering(self):
        self.headers.prepend(Configs.get_config('TABLE_AUTO_NUMBERING_CONFIG'))

    def get_headers(self):
        return self.headers

    def get_header(self, idx, normalized=False):
        # if self.auto_number:
        #     idx -= 1
        if idx > len(self.headers.keys()) - 1 or idx < 0:
            return 0
        else:
            lheaders = list(self.headers.keys())
            if not self.auto_number:
                idx = idx - 1

            if normalized:
                lheaders[idx] = lheaders[idx].replace("<br>", " ")

            return lheaders[idx]

    def get_header_(self, idx):
        if not self.auto_number:
            if idx != 0:
                idx = idx - 1

        lheaders = list(self.headers.keys())
        return lheaders[idx]

    def get_header_length(self, column_idx=None, header_title=None):
        length = None
        if column_idx is not None:
            if column_idx < len(self.headers.keys()):
                lheaders = list(self.headers.keys())
                length = self.headers[lheaders[column_idx]][0]

        if header_title in self.headers:
            length = self.headers[header_title][0]

        if self.web_style:
            length = length * Configs.get_config('PIXEL_RATIO')

        return length

    def get_header_index(self, header_title):
        if header_title in self.get_headers():
            lheader = list(self.get_headers().keys())
            return lheader.index(header_title)

    def get_header_justification(self, header_title):
        if header_title in self.headers:
            return self.headers[header_title][1]
        else:
            return None

    def get_column_justification(self, column_idx, header=None):

        if not self.auto_number:
            offset = -1
        else:
            offset = 0

        if header is None:
            if column_idx + offset < len(self.headers.keys()):
                lheaders = list(self.headers.keys())
                return self.headers[lheaders[column_idx + offset]][2]
            else:
                return None
        else:
            if header not in self.headers:
                return None
            else:
                return self.headers[header][2]

    def get_column_count(self):
        """
        Will return number of columns on this table
        :return:
        """

        return len(self.headers)

    @staticmethod
    def sort_key(key):

        ikey = int(key)

        return ikey

    @staticmethod
    def recycle_color(table_name, id):
        """
        Recycle the given color for a new one
        :param id: actual id that is requiring a new color (recycled)
        :return: a new color
        """
        global database
        use_session()

        # look for the actual ID
        dbtask = database.query(Task).filter(Task.task_id == id).first()
        color = dbtask.task_color_code

        if dbtask:

            # now check if color hasn't been used by other value...
            #
            color_scheme = 0
            # color = Table.random_colorx()
            if table_name and table_name in Configs.get_config("TABLE_CONFIG"):
                table_config = Configs.get_config("TABLE_CONFIG", table_name)
                if "COLOR_SCHEME" in table_config["LINE_DETAILS"]:
                    if table_config["LINE_DETAILS"]["COLOR_SCHEME"] == 1:
                        # color = Table.random_color()
                        color_scheme = 1
                    else:
                        # color = Table.random_colorx()
                        color_scheme = 0
            else:
                color_scheme = 0
                # color = Table.random_colorx()

            # Search an individual color for this code
            # print("Starting color: %s" % color)
            while True:
                check_task = database.query(Task).filter(Task.task_color_code == color).first()

                # if color is not found at the color match table; then choose this one and break the loop
                # otherwise, generate another color and check again.

                if not check_task:
                    # print("Approved color: %s" % color)
                    # This color is not being used.
                    break

                # Look for a new color...
                # print("DEBUG: Color clash... Color already used by %s, generating a new one" % (check_task.task_id,))
                if color_scheme == 1:
                    color = Table.random_color()
                else:
                    color = Table.random_colorx()

                # print("Prev: %s --> new %s" % (check_task.task_color_code, color))
            #
            # Store new color for this match

            dbtask.task_color_code = color
            dbcommit()

        return color

    def print_table(self, highlight=None, sort_by=None, auto_numbering=False, auto_numbering_start=None,
                    output_style=None, clusterize=False):
        """
        This method will print created table
        :param auto_numbering_start:
        :param output_style: specify which format you want the table output
        :param highlight: A dictionary, containing highlighting strings and severity setting
        :param sort_by: If you need to sort the table, you can choose column number or the header name to sort by
        :param auto_numbering: if it's true, will add an additional column with the row number
        :return:
        """

        wtable = Web(True)

        clusterize_row = []  # Each row
        clusterize_rows = []  # All rows

        if auto_numbering:
            self.auto_numbering()

        if self.table_name in Configs.get_config("TABLE_CONFIG"):
            if "OPTIONS" in Configs.get_config("TABLE_CONFIG")[self.table_name]:
                if "USE_CLUSTERIZE" in Configs.get_config("TABLE_CONFIG")[self.table_name]["OPTIONS"]:
                    clusterize = True

        reverse = False
        content_type = None
        # for table_conf in Configs.get_config("TABLE_CONFIG"):
        #     sort_by = None
        #     if self.table_name and table_conf in self.table_name:
        #         if "SORTING" in Configs.get_config("TABLE_CONFIG")[table_conf]:
        #             if "BY_COLUMN" in Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"]:
        #                 sort_by = Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"]["BY_COLUMN"]
        #
        #             if "DIRECTION" in Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"] and \
        #                     Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"]["DIRECTION"] == "reverse":
        #                 reverse = True
        #
        #             if "CONTENT_TYPE" in Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"]:
        #                 content_type = Configs.get_config("TABLE_CONFIG")[table_conf]["SORTING"]["CONTENT_TYPE"]
        #             else:
        #                 content_type = None
        #
        #         # if "LINE_DETAILS" in Configs.get_config("TABLE_CONFIG")[table_conf]:
        #         #     if "SHOW" in Configs.get_config("TABLE_CONFIG")[table_conf]["LINE_DETAILS"] and \
        #         #             Configs.get_config("TABLE_CONFIG")[table_conf]["LINE_DETAILS"]["SHOW"]:
        #         #
        #         #         # prepare initial colors
        #         #         #self.cell_color_map = setup_color_table(self.table_name)
        #
        #         break

        table = []
        row_format = []
        maxlines_per_row = []

        # if sort_by:
        #
        #     if type(sort_by) == int:
        #         if content_type and content_type == "int":
        #             self.rows = sorted(self.rows, key=operator.itemgetter(sort_by - 1), reverse=reverse)
        #         else:
        #             self.rows = sorted(self.rows, key=operator.itemgetter(sort_by - 1), reverse=reverse)
        #
        #     elif type(sort_by) == str:
        #         if sort_by in self.get_headers():
        #             if content_type and content_type == "int":
        #                 self.rows = sorted(self.rows,
        #                                    key=operator.itemgetter(self.get_header_index(sort_by) - 1),
        #                                    reverse=reverse)
        #             else:
        #                 self.rows = sorted(self.rows, key=operator.itemgetter(self.get_header_index(sort_by) - 1),
        #                                    reverse=reverse)

        # if output_style and output_style == 'web' or args.web_style:
        # Start table
        wtable.add_to_page("<center>")
        wtable.add_to_page(self.create_title_header())
        # Setup headers
        # Check for any TABLE optimisation
        #
        # if clusterize:
        #     wtable.add_to_page("<div class='clusterize'>")

        if Configs.get_config('HTML_START_TABLE'):
            custom_table_applied = False
            for each_table_name in Configs.get_config("HTML_START_TABLE"):
                if each_table_name in self.table_name:
                    wtable.add_to_page(Configs.get_config("HTML_START_TABLE")[each_table_name])
                    custom_table_applied = True

            if not custom_table_applied:
                if "GLOBAL_SETTING" in Configs.get_config('HTML_START_TABLE'):
                    wtable.add_to_page(Configs.get_config('HTML_START_TABLE')["GLOBAL_SETTING"])
                else:
                    wtable.add_to_page("<table>")
        else:
            wtable.add_to_page("<table>")

        # wtable.add_to_page("<thead id='%s'>" % self.table_name)
        class_table_name = self.table_name.replace(":", "").replace(" ", "-")
        wtable.add_to_page('<thead class="th-%s">' % class_table_name)
        # Setup size per column using CCS
        #
        wtable.add_to_page("<style>")
        for each_column_name in self.get_headers().keys():
            wtable.add_to_page(".%s {" % each_column_name.replace(" ", "-").replace("<br>", "-"), )
            wtable.add_to_page("   width: %s%s;" % (self.get_header_length(header_title=each_column_name), "px"))
            # if self.able_to_orderby(each_column_name):
            #     wtable.add_to_page("   cursor: pointer")
            wtable.add_to_page("}\n")
        wtable.add_to_page("</style>\n")

        extra_attributes_tr = ''
        if Configs.get_config("TABLE_CONFIG", self.table_name, similar=True):
            tbl_config = Configs.get_config("TABLE_CONFIG", self.table_name, similar=True)
            if "TABLE_RENDER_ENGINE" in tbl_config:
                # Force a specific class name to a header, this is to setup a size for header independently of
                # the rows; this specially useful on scrollable tables like "Log Viewer"
                #
                if "FORCE_HEADER_PREFIX" in tbl_config["TABLE_RENDER_ENGINE"]:
                    extra_attributes_tr = ' class="tr-%s"' % self.table_name.replace(" ", "-").replace("<br>", "-")

        wtable.add_to_page('<tr%s>' % extra_attributes_tr)

        for each_column_header in self.get_headers().keys():
            cell_hattribute = ' class="%s"' % \
                              each_column_header.replace(" ", "-").replace("<br>", "-")
            if Configs.get_config("TABLE_CONFIG", self.table_name, similar=True):
                tbl_config = Configs.get_config("TABLE_CONFIG", self.table_name, similar=True)
                if "TABLE_RENDER_ENGINE" in tbl_config:
                    # Force a specific class name to a header, this is to setup a size for header independently of
                    # the rows; this specially useful on scrollable tables like "Log Viewer"
                    #
                    if "FORCE_HEADER_PREFIX" in tbl_config["TABLE_RENDER_ENGINE"]:
                        if each_column_header \
                                in tbl_config["TABLE_RENDER_ENGINE"]["FORCE_HEADER_PREFIX"]:
                            cell_hattribute = ' class="%s-%s"' % \
                                              (tbl_config["TABLE_RENDER_ENGINE"]["FORCE_HEADER_PREFIX"][
                                                   each_column_header],
                                               each_column_header.replace(" ", "-").replace("<br>", "-"))

            # Check for filters:
            dropdown = ""
            if self.has_filter(each_column_header):
                # Create dropdown list tool on this header!
                options = self.get_filter_options(each_column_header)
                if options:
                    # Create dropdown tool
                    header_idx = self.get_header_index(each_column_header)
                    id_header = each_column_header.replace('<br>', ' ')
                    id_header = "%s:%s" % (header_idx, id_header.replace(' ', '-'))
                    dropdown = "<br><span class='th-filter-on'>%s<span><br>" % \
                               Web.drop_down_list(id_header,
                                                  options,
                                                  selection="all",
                                                  onchange="filter_table(this)")

            # Check this header to see if will allow sorting
            if self.able_to_orderby(each_column_header):
                cell_hattribute += ' name="th-order-on"'
                idc = each_column_header.replace(" ", "-").replace("<br>", "-")
                if each_column_header in self.args_header:
                    wtable.add_to_page("<th %s>"
                                       "<span class='th-order-on' id='order-on:%s'>%s</span>"
                                       "%s%s</th>" % (cell_hattribute, idc, each_column_header,
                                                      self.args_header[each_column_header],
                                                      dropdown))
                else:
                    wtable.add_to_page("<th %s>"
                                       "<span class='th-order-on' id='order-on:%s'>%s</span>"
                                       "%s</th>" % (cell_hattribute, idc, each_column_header, dropdown))
            else:
                if each_column_header in self.args_header:
                    wtable.add_to_page("<th %s>%s%s%s</th>" % (cell_hattribute, each_column_header,
                                                               self.args_header[each_column_header],
                                                               dropdown))
                else:
                    wtable.add_to_page("<th %s>%s%s</th>" % (cell_hattribute, each_column_header, dropdown))

        wtable.add_to_page('</tr>')

        wtable.add_to_page('</thead>')
        # if clusterize:
        #     wtable.add_to_page("</table>")

        # Add table body
        # tbody = '<tbody id="%s">' % self.table_name <------- Previously used with clusterize...
        # didn't work as I wanted
        if self.has_filter() or self.able_to_orderby():
            tbody = '<tbody id="tbody-content" class="tb-%s">' % self.table_name.replace(" ", "-")
        else:
            tbody = '<tbody class="tb-%s">' % self.table_name.replace(" ", "-")

        # Attach scroll support if table requires it (Log Viewer for example)
        #
        if self.table_name in Configs.get_config("TABLE_CONFIG"):
            table_cfg = Configs.get_config("TABLE_CONFIG", self.table_name)
            if "TABLE_RENDER_ENGINE" in table_cfg:
                function_name = self.table_name.replace(" ", "_")
                class_name = "tb-" + self.table_name.replace(" ", "-")
                top_limit = table_cfg["TABLE_RENDER_ENGINE"]["REQUEST_ON_TOP"]
                bottom_limit = table_cfg["TABLE_RENDER_ENGINE"]["REQUEST_ON_BOTTOM"]
                batch_row_request = table_cfg["TABLE_RENDER_ENGINE"]["BATCH_ROW_REQUEST"]
                tbody = '<tbody class="%s" onscroll="%s(this)">' % (class_name, function_name)

                Configs.set_config("FUNCTION_NAME", function_name)
                Configs.set_config("CLASS_NAME", class_name)
                Configs.set_config("BATCH_ROW_REQUEST", "%s" % batch_row_request)
                Configs.set_config("REQUEST_ON_TOP", "%s" % top_limit)
                Configs.set_config("REQUEST_ON_BOTTOM", "%s" % bottom_limit)

                tbody = Web.inject_js("table_rendering.js") + tbody + "\n"

        # Add support for table sorting
        ordering_method = None
        if self.able_to_orderby():
            if Configs.get_config("TABLE_CONFIG", self.table_name):
                if "ORDERING_METHOD" in Configs.get_config("TABLE_CONFIG", self.table_name):
                    ordering_method = Configs.get_config("TABLE_CONFIG", self.table_name)["ORDERING_METHOD"]
            else:
                ordering_method = "DATABASE"

            if ordering_method:
                tbody = Web.inject_js("table_ordering.js",
                                      variable_replace='TABLE_ORDERING="%s"' % ordering_method) + tbody
            else:
                print("[MAIN] please define ordering method on config (TABLE or DATABASE) using \"ORDERING_METHOD\" "
                      "keyword under '%s' table definition..." %
                      (self.table_name,))

        # Add support for table filtering
        if self.has_filter():
            tbody = Web.inject_js("table_filtering.js") + tbody

        if auto_numbering_start:
            rl = auto_numbering_start
        else:
            rl = 1

        wtable.add_to_page(tbody)
        for each_row in self.rows:
            if not clusterize:
                wtable.add_to_page('<tr>')

            if auto_numbering:
                wtable.add_to_page('<td >%s</td>' % rl)
                if not clusterize:
                    clusterize_rows.append('%s' % rl)
                rl += 1
            cc = 1

            for each_column in each_row:
                if self.table_name in Configs.get_config("TABLE_CONFIG"):
                    cell_attribute = ''
                    tbl_config = Configs.get_config("TABLE_CONFIG", self.table_name)
                    if "TABLE_RENDER_ENGINE" in tbl_config:
                        if "IGNORE_COLUMN_SIZE" in tbl_config["TABLE_RENDER_ENGINE"]:
                            if self.get_header(cc) not in tbl_config["TABLE_RENDER_ENGINE"]["IGNORE_COLUMN_SIZE"]:
                                cell_attribute = ' class="%s"' % self.get_header(cc)
                else:
                    cell_attribute = ''
                if len('%s' % each_column) < 20:
                    ids = "%s-%s" % (cc, each_column)
                    if ids in self.cell_attributtes:
                        for each_att in self.cell_attributtes:
                            cell_attribute += " %s" % (self.cell_attributtes[each_att],)

                if self.get_column_justification(cc) == '^':
                    cell_attribute += " style='text-align:center'"
                if self.get_column_justification(cc) == '<':
                    cell_attribute += " style='text-align:left'"
                if self.get_column_justification(cc) == '>':
                    cell_attribute += " style='text-align:right'"

                for each_table_name in Configs.get_config("TABLE_CONFIG"):
                    if each_table_name in self.table_name:
                        table_config = Configs.get_config("TABLE_CONFIG")[each_table_name]
                        if "HIGHLIGHT" in table_config:
                            for heach_column in table_config["HIGHLIGHT"]:
                                if heach_column == self.get_header(cc):
                                    for each_h in table_config["HIGHLIGHT"][heach_column]:
                                        if "\\b" not in each_h:
                                            if type(each_column) == int:
                                                each_column = str(each_column)
                                            # Catch errors with the RE trying to interpret '*'
                                            if '*' in each_h:
                                                each_h = each_h.replace("*", r"\*")

                                            # If length of search pattern is less than 3, then search for exact match
                                            # within the string given, otherwise search for the full pattern,
                                            # this will avoid situations where the table was highlighting wrong stuff.
                                            # for example if the pattern to highlight is "I" then anything with n "I" will
                                            # be highlighted, like "I" and "INFO"; in such case it will strictly look for a
                                            # "I" and will not match anythingelse...

                                            if "HIGHLIGHT_CONDITION" in table_config and heach_column in \
                                                    table_config["HIGHLIGHT_CONDITION"]:
                                                if table_config["HIGHLIGHT_CONDITION"][heach_column] == 'Strict':
                                                    chk_col = re.search(r'\b%s\b' % each_h, each_column)
                                                else:
                                                    chk_col = re.search(r'%s' % each_h, each_column)
                                            else:
                                                chk_col = re.search(r'%s' % each_h, each_column)

                                            if chk_col:  # and chk_col in each_column:
                                                # print "(%s -- %s)<BR>" %
                                                # (each_column,table_config["HIGHLIGHT"][heach_column].keys())
                                                fcolor = None
                                                hcolor = table_config["HIGHLIGHT"][heach_column][each_h]
                                                # Check if color scheme include font color, denoted by '/' at the color
                                                # definition
                                                if "/" in hcolor:
                                                    colors = hcolor.split("/")
                                                    hcolor = colors[0]
                                                    fcolor = colors[1]
                                                cell_attribute += " bgcolor=%s" % hcolor
                                                if fcolor:
                                                    each_column = "<font color='%s'>%s</font>" % (fcolor, each_column)
                                        else:
                                            each_h = each_h.replace("\\b", "")
                                            if each_h == each_column:
                                                # print "(%s -- %s)<BR>" %
                                                # (each_column,table_config["HIGHLIGHT"][heach_column].keys())
                                                fcolor = None
                                                hcolor = table_config["HIGHLIGHT"][heach_column][each_h]
                                                # Check if color scheme include font color, denoted by '/' at the color
                                                # definition
                                                if "/" in hcolor:
                                                    colors = hcolor.split("/")
                                                    hcolor = colors[0]
                                                    fcolor = colors[1]
                                                cell_attribute += " bgcolor=%s" % hcolor
                                                if fcolor:
                                                    each_column = "<font color='%s'>%s</font>" % (fcolor, each_column)

                                else:
                                    continue
                # Check if we need to hide info
                table_config_details = Configs.get_config("TABLE_CONFIG", self.table_name, similar=True)
                if table_config_details:
                    if "LINE_DETAILS" in table_config_details:
                        if "HIDE_DATA" in table_config_details["LINE_DETAILS"]:
                            table_config_hide = table_config_details["LINE_DETAILS"]["HIDE_DATA"]
                            for each_data in table_config_hide:
                                match_hide = re.search(table_config_hide[each_data], each_column)

                                if match_hide:
                                    each_column = each_column.replace(match_hide.group(1), each_data)

                        # Check if column require specific detailed information
                        #
                        if "CHECK" in table_config_details["LINE_DETAILS"]:
                            if "COLUMN_DETAILS" in table_config_details["LINE_DETAILS"]:
                                if self.get_header_(cc) in table_config_details["LINE_DETAILS"]["COLUMN_DETAILS"]:
                                    check_line_details, max_len = self.show_line_details(each_column)
                                    if check_line_details:
                                        Table.add_table_line_details(each_column)
                                        tmp1 = "<table class='line-analysis'><tr>" \
                                               "<td class='line-analysis-left'>%s</td>" \
                                               "<td class='line-analysis-right'>%s</td></tr></table>" % (
                                                   each_column,
                                                   check_line_details)
                                        each_column = tmp1
                            else:
                                check_line_details, max_len = self.show_line_details(each_column)
                                if check_line_details:
                                    tmp1 = "<table class='line-analysis'><tr>" \
                                           "<td class='line-analysis-left'>%s</td>" \
                                           "<td class='line-analysis-right'>%s</td></tr></table>" % (
                                               each_column,
                                               check_line_details)
                                    each_column = tmp1

                wtable.add_to_page("<td%s>%s</td>" % (cell_attribute, each_column,))

                if clusterize:
                    if type(each_column) == str:
                        # clusterize_row.append("<td%s>%s</td>" % (cell_attribute, each_column.rstrip(),))
                        clusterize_row.append((cell_attribute, each_column.rstrip()))
                    else:
                        # clusterize_row.append("<td%s>%s</td>" % (cell_attribute, each_column,))
                        clusterize_row.append((cell_attribute, each_column))
                cc += 1

            wtable.add_to_page('</tr>')
            if clusterize:
                # clusterize_rows.append("<tr>%s</tr>" % "".join(clusterize_row))
                clusterize_rows.append(clusterize_row)
                clusterize_row = []

        wtable.add_to_page('</tbody>')
        wtable.add_to_page('</table>')
        wtable.add_to_page('</center>')
        # Check for any TABLE optimisation
        #
        if self.table_name in Configs.get_config("TABLE_CONFIG"):
            if "OPTIONS" in Configs.get_config("TABLE_CONFIG")[self.table_name]:
                if "USE_CLUSTERIZE" in Configs.get_config("TABLE_CONFIG")[self.table_name]["OPTIONS"]:
                    wtable.add_to_page("</div>")  # tbody
                    wtable.add_to_page("</div>")  # Whole table
        # wtable.add_to_page(self.fix_columns_sizes())
        wtable.add_to_page('<BR>')
        Configs.count = 0
        if clusterize:
            return wtable.print_html(), clusterize_rows
        else:
            return wtable.print_html()

    def print_table_ascii(self, highlight=None, sort_by=None, auto_numbering=False, output_style=None):
        """
        This method will print(created table)
        :param output_style: specify which format you want the table output
        :param highlight: A dictionary, containing highlighting strings and severity setting
        :param sort_by: If you need to sort the table, you can choose column number or the header name to sort by
        :param auto_numbering: if it's true, will add an additional column with the row number
        :return:
        """

        import textwrap
        array_print = []
        if auto_numbering:
            self.auto_numbering()
        self.web_style = False
        if output_style and output_style == "array":
            array_print = self.create_title_header_ascii()
        else:
            self.create_title_header_ascii()

        table = []
        row_format = []
        maxlines_per_row = []

        if sort_by:
            if type(sort_by) == int:
                self.rows = sorted(self.rows, key=operator.itemgetter(sort_by - 1))
            elif type(sort_by) == str:
                if sort_by in self.get_headers():
                    self.rows = sorted(self.rows, key=operator.itemgetter(self.get_header_index(sort_by) - 1))

        # if output_style and output_style == 'web':# or args and args.web_style:
        #     # Setup headers
        #     print('<tr>')
        #     for each_column_header in self.get_headers().keys():
        #         print('<th>%s</th>' % each_column_header)
        #     # Setup size per column
        #     for each_column_name in self.get_headers().keys():
        #         print('<col width="%s">' % self.get_header_length(header_title=each_column_name))
        #     print('</tr>')
        #     rl = 1
        #     for each_row in self.rows:
        #         print('<tr>')
        #         if auto_numbering:
        #             print('<td>%s</td>' % rl)
        #             rl += 1
        #         for each_column in each_row:
        #             print('<td>%s</td>' % each_column)
        #         print('</tr>')
        #     print('</center>')
        #     print('</table>')
        #     print('<BR>')
        #     return

        # Prepare line format:

        for hn in self.headers:
            row_format.append('{:%s%s}' % (self.get_column_justification(None, hn), self.get_header_length(None, hn)))

        row_line = 0
        for cl in self.rows:
            row_line += 1
            cn = 0
            arow = []
            nmaxlines = 1
            if auto_numbering:
                cl.insert(0, u'%s' % row_line)
            for cel in cl:
                if cel is not None:
                    hdr_len = self.get_header_length(column_idx=cn)
                    if not isinstance(cel, str):
                        cel = '%s' % cel

                    if len(cel) > hdr_len:
                        nrow = textwrap.fill(cel, hdr_len)
                        arow.append(nrow.split('\n'))
                        if len(nrow.split('\n')) > nmaxlines:
                            nmaxlines = len(nrow.split('\n'))
                    else:
                        arow.append([cel])
                cn += 1
            # Store maximum lines found on this row
            maxlines_per_row.append(nmaxlines)
            table.append(arow)

        for row_number, row in enumerate(table):
            for nr in range(0, maxlines_per_row[row_number]):
                sfrow = []
                for idx, rcel in enumerate(row):
                    if nr < len(rcel):
                        sfrow.append(row_format[idx].format(rcel[nr]))
                    else:
                        sfrow.append(row_format[idx].format(' '))

                if highlight is None:
                    if output_style and output_style == "array":
                        array_print.append('%s%s%s' % (self.column_delimiter,
                                                       self.column_delimiter.join(sfrow),
                                                       self.column_delimiter))
                    else:
                        print('%s%s%s' % (self.column_delimiter,
                                          self.column_delimiter.join(sfrow),
                                          self.column_delimiter))
                else:
                    tsfrow = []
                    for word in sfrow:
                        sword = word
                        for w2h in highlight:
                            if w2h in word:
                                tword = word.replace(w2h, '{{%s}}' % w2h)
                                sword = printm.highlight(tword, highlight[w2h])
                        tsfrow.append(sword)

                    if output_style and output_style == "array":
                        array_print.append('%s%s%s' % (self.column_delimiter,
                                                       self.column_delimiter.join(sfrow),
                                                       self.column_delimiter))
                    else:
                        print('%s%s%s' % (
                            self.column_delimiter, self.column_delimiter.join(tsfrow), self.column_delimiter))

            if len(self.line_delimiter.strip()) != 0:
                if output_style and output_style == "array":
                    array_print.append('%s%s%s' % (self.column_delimiter,
                                                   self.column_delimiter.join(sfrow),
                                                   self.column_delimiter))
                else:
                    print(self.line_delimiter)

        if self.start_end_table_delimiter is not None:
            if output_style and output_style == "array":
                array_print.append(self.start_end_table_delimiter)
            else:
                print(self.start_end_table_delimiter)

        if output_style and output_style == "array":
            return array_print

    def show_line_details(self, line):
        """
        Check if given line has any important details to highlight
        :param line: line to check
        :return:
        """
        line_detail = []
        max_len = 0

        table_config = Configs.get_config("TABLE_CONFIG")

        if table_config:
            if self.table_name in Configs.get_config("TABLE_CONFIG"):
                if "LINE_DETAILS" in table_config[self.table_name]:

                    if "SHOW" not in table_config[self.table_name]["LINE_DETAILS"]:
                        return None, None

                    if not table_config[self.table_name]["LINE_DETAILS"]["SHOW"]:
                        return None, None

                    details = table_config[self.table_name]["LINE_DETAILS"]
                    if "CHECK" in details:
                        each_details = self.valid_details(line, details)
                        if "CHECK_OPTIONS" in details:
                            check_options = details["CHECK_OPTIONS"]
                        else:
                            check_options = None
                        if each_details:
                            match_used = []
                            # Table.add_table_line_details(line)
                            for each_detail in each_details:
                                # # Check for any option given for the actual detail
                                # if each_detail in check_options:
                                #     each_detail_option = check_options[each_detail]
                                # else:
                                #     each_detail_option = None

                                each_detail_value = each_details[each_detail]
                                # for each_regex in details["CHECK"][each_detail]:
                                try:
                                    # match = re.findall(each_regex, line)
                                    # if match:
                                    # Check if first result of this match has multiple matches
                                    # Also it will ignore commas if it was given as an option
                                    #
                                    if ',' in each_detail_value and check_options and \
                                            "IGNORE_COMMA" in check_options and \
                                            each_detail not in check_options["IGNORE_COMMA"]:
                                        each_detail_value = each_detail_value.split(',')
                                    else:
                                        each_detail_value = [each_detail_value]
                                    for each_match in each_detail_value:
                                        if isinstance(each_match, str):
                                            each_match = each_match.strip()
                                            if 'null' in each_match:
                                                continue

                                        if each_match in match_used:
                                            continue

                                        # Add information about detail type
                                        self.data["task_type"] = each_detail
                                        skip_color_match = False
                                        if check_options:
                                            if "SHOW_ONLY" in check_options and \
                                                    each_detail in check_options["SHOW_ONLY"]:
                                                skip_color_match = True
                                        color = ''
                                        if not skip_color_match:
                                            color = self.set_color(each_match)

                                        line_detail.append("<tr>")
                                        line_detail.append("<td class='details-property'>%s</td>"
                                                           "<td bgcolor='%s' class='details-value'>%s%s</td> " %
                                                           (each_detail, color, each_match,
                                                            Web.span(
                                                                Web.image(
                                                                    Configs.get_config("APP_URL"),
                                                                    "recycle.png",
                                                                    xclass="recycle-color:%s" % (each_match,),
                                                                    style="width:32px;height: 32px;"),
                                                                xclass="recycle-color", style="float: right;",
                                                                title="Recycle color (change it)")))
                                        line_detail.append("</tr>")
                                        match_used.append(each_match)
                                        if len(each_detail_value) > max_len:
                                            max_len = len(each_detail_value)
                                    # break
                                except Exception as ve:
                                    return '<table><tr><td>%s</td></tr></table>' % \
                                           ("ERROR: %s Trying to apply line details for %s" % (ve, each_detail)), 40
                        else:
                            return None, None

        if line_detail:
            return "<table class='line-detail'>%s</table>" % "".join(line_detail), 25  # max_len - 15
            # return '<table class="line-detail">%s</table>' % "\n".join(line_detail), 25  # max_len - 15
        else:
            return None, None

    @staticmethod
    def valid_details(line, details, quick=False):
        """
        Quickly search for a valid detail on given line
        :param line: line to scan
        :param details: regex list to look for
        :return: property string that had a match, None otherwise
        """

        # put all regex on a single string to check if worthy to explore this line
        property_found = None
        all_regex = []
        list_rgx = [item for item in details["CHECK"].values()]
        Configs.count += 1
        # print("DEBUG====>[%s] [%s] Buscando detalles" % (Configs.count,
        #                                                  datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),))
        for rgx in list_rgx:
            if isinstance(rgx, str):
                all_regex.append(rgx)
            else:
                for each_rgx in rgx:
                    all_regex.append(each_rgx)

        full_rgx = "|".join(all_regex)

        # First validate line has a good match
        match = re.search(full_rgx, line)

        if match:
            # Check which property is a match and return that one.
            #
            if quick:
                # print("DEBUG====>Precheck!")
                return True

            property_found = {}
            regex_list = details["CHECK"]
            for each_property in regex_list:
                all_rgx_values = "|".join(regex_list[each_property])

                property_match = Configs.regex_expression(all_rgx_values).search(line)
                # property_match = re.search(all_rgx_values, line)

                if property_match:
                    try:
                        value = [x for x in property_match.groups() if x is not None][0]
                        property_found[each_property] = value
                    except BaseException as be:
                        print("[SUPPORT-LINE-DETAILS] %s: it has a regex definition that is lacking of"
                              " capture group please check it out" % (each_property,))
                    # property_found.append(each_property)

        return property_found

    # def setup_color_table(self, table_name):
    #     """
    #     Create matches on line_details pairing colors for coincidence
    #     :param table_name:
    #     :return:
    #     """
    #     from random import seed
    #     from random import randint
    #
    #     initial_color = {}
    #     used_colors = []
    #     seed(1)
    #     if Configs.config["TABLE_CONFIG"][table_name]["LINE_DETAILS"] and \
    #             "CHECK" in Configs.config["TABLE_CONFIG"][table_name]["LINE_DETAILS"] and \
    #             "SHOW" in Configs.config["TABLE_CONFIG"][table_name]["LINE_DETAILS"] and \
    #             Configs.config["TABLE_CONFIG"][table_name]["LINE_DETAILS"]["SHOW"]:
    #         line_details = Configs.config["TABLE_CONFIG"][table_name]["LINE_DETAILS"]
    #
    #         for each_detail in line_details:
    #             if each_detail not in initial_color:
    #                 color_match = randint(0, 360)
    #
    #                 while color_match in used_colors:
    #                     color_match = randint(0, 360)
    #
    #                 used_colors.append(color_match)
    #                 initial_color[each_detail] = initial_color
    #
    #     return initial_color

    @staticmethod
    def random_colorx():

        hue = randint(0, 360)
        pr1 = randint(0, 100)
        pr2 = randint(0, 100)
        color = "hsl(%s,%s%%,%s%%)" % (hue, pr1, pr2)

        return color

    @staticmethod
    def random_color():
        code = "0123456789ABCDEF"
        color = "#"

        for i in range(0, 5):
            color += code[randint(0, 15)]

        return color

    def similar_color(self, color, tolerance=10):
        """
        This method will return true if given color is similar to any other color already stored,
        if it fall within tolerance given...
        :param color: Color to compare
        :param tolerance: tolerance (similarity, default is 10)
        :return: boolean, true if color is close (visually) or false otherwise
        """

        use_session()
        extract_color_values = r"hsl\((\d+),(\d+)%,(\d+)%\)"
        base_color = re.search(extract_color_values, color)
        if self.data and "logfile_hash_key" in self.data:
            colors = database.query(Task).filter(Task.logfile_hash_key == self.data["logfile_hash_key"]).all()

            for each_color in colors:
                extract_values = re.search(extract_color_values, each_color.task_color_code)
                if abs(int(extract_values.group(1)) - int(base_color.group(1))) < tolerance:
                    return True

                if abs(int(base_color.group(3)) - int(extract_values.group(3))) < tolerance:
                    return True
                else:
                    return False

        return False

    def set_color(self, value):
        """
        Set or return a specific color for the given value; this will guarantee same match will have a uniform color
        through all the table, this will also create a record of given value into Database, program is able to determine
        Kind of value that is being passed using definition under [TABLE_CONFIG][TABLE_NAME][LINE_DETAILS].

        :param value: value to look for match
        :param recycle: will instruct to recycle current color if 'value' has already one
        :return: match color selected for it
        """

        # Check if given table contain self data field.

        if self.data and "logfile_hash_key" in self.data:
            use_session()
            # tasktype_key = "%s@%s" % (self.data["logfile_hash_key"], value)
            tasktype_key = "%s" % (value,)
            tasktype_hashkey = generate_hash(tasktype_key)

            check_task = database.query(Task).filter(Task.task_hash_key == tasktype_hashkey).first()

            if check_task:
                return check_task.task_color_code
        else:
            if value in self.cell_match:
                return self.cell_match[value]

        # now check if color hasn't been used by other value...
        #
        color_scheme = 0
        color = self.random_colorx()
        if self.table_name and self.table_name in Configs.get_config("TABLE_CONFIG"):
            table_config = Configs.get_config("TABLE_CONFIG", self.table_name)
            if "COLOR_SCHEME" in table_config["LINE_DETAILS"]:
                if table_config["LINE_DETAILS"]["COLOR_SCHEME"] == 1:
                    color = self.random_color()
                else:
                    color = self.random_colorx()
        else:
            color_scheme = 0
            color = self.random_colorx()

        if self.data:
            # Search an individual color for this code
            while True:
                if "logfile_hash_key" in self.data:
                    check_task = database.query(Task).filter(Task.task_color_code == color).first()

                    # if color is not found at the color match table; then choose this one and break the loop
                    # otherwise, generate another color and check again.

                    if not check_task:
                        # Check if selected color is "similar" to other color already selected, then keep looking
                        break

                    # Look for a new color...
                    if color_scheme == 1:
                        color = self.random_color()
                    else:
                        color = self.random_colorx()
            #
            # Store new color for this match
            # task_key = "%s@%s" % (self.data["logfile_hash_key"], value)
            task_key = "%s" % (value,)
            task_hashkey = generate_hash(task_key)
            # logfile_hash_key
            # task_type_hash_key
            # color_code
            # task_id
            # task_type
            task = Task(
                logfile_hash_key=self.data["logfile_hash_key"],
                task_hash_key=task_hashkey,
                task_color_code=color,
                task_id=value,
                task_type=self.data["task_type"]
            )
            database.add(task)
            dbcommit()
        else:
            while color in self.cell_match.values():
                color = self.random_colorx()

            self.cell_match[value] = color

        return color

    def fix_columns_sizes(self):
        """
        Apply Javascript code to fix header sizes
        :return:
        """
        javascript = """
<!--script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script> --!> 
<script>
// Change the selector if needed

 var $table = $('table.dashboard'),
    $bodyCells = $table.find('tbody tr:first').children(),
    colWidth;

// Get the tbody columns width array
colWidth = $bodyCells.map(function() {
    return $(this).width();
}).get();

// Set the width of thead columns
$table.find('thead tr').children().each(function(i, v) {
    $(v).width(colWidth[i]);
}); 
</script>

"""
        return javascript

    def get_max_columns(self):
        """
        Check if this table has defined any limits on numbers of characters per line
        :return:
        """

        if Configs.get_config("TABLE_CONFIG"):
            for each_table in Configs.get_config("TABLE_CONFIG"):
                if each_table in self.table_name:
                    table_setup = Configs.get_config("TABLE_CONFIG")
                    if "TEXT_AREA_SETUP" in table_setup[each_table]:
                        text_area = table_setup[each_table]["TEXT_AREA_SETUP"]
                        if "ACTIVATE_OVER_MAX_CHAR" in text_area:
                            return text_area["ACTIVATE_OVER_MAX_CHAR"]
                        else:
                            return None
                    else:
                        return None

    def get_text_rows(self):
        """
        Get configured rows for the text area for this table cells
        :return:
        """

        if Configs.get_config("TABLE_CONFIG"):
            for each_table in Configs.get_config("TABLE_CONFIG"):
                if each_table in self.table_name:
                    table_setup = Configs.get_config("TABLE_CONFIG")

                    if "TEXT_AREA_SETUP" in table_setup[each_table]:
                        text_area = table_setup[each_table]["TEXT_AREA_SETUP"]
                        if "ROWS" in text_area:
                            return text_area["ROWS"]
                        else:
                            return None
                    else:
                        return None

    def get_text_cols(self):
        """
        Get configured columns for the text area for this table cells
        :return:
        """
        if Configs.get_config("TABLE_CONFIG"):
            for each_table in Configs.get_config("TABLE_CONFIG"):
                if each_table in self.table_name:
                    table_setup = Configs.get_config("TABLE_CONFIG")
                    if "TEXT_AREA_SETUP" in table_setup[each_table]:
                        text_area = table_setup[each_table]["TEXT_AREA_SETUP"]
                        if "COLUMNS" in text_area:
                            return text_area["COLUMNS"]
                        else:
                            return None
                    else:
                        return None

    def setup_field(self, message, xclass=None):
        """
        This method will verify given message length is within proper limits, if so will return same message given
        otherwise will return a text area control with message inside it
        :param message:
        :return:
        """

        if self.get_max_columns():

            if len("%s" % message) > self.get_max_columns():
                rows = self.get_text_rows()
                # columns = self.get_text_cols()
                # line_details, max_len = self.show_line_details(message)
                # if line_details:
                #     if max_len:
                #         columns -= max_len
                #
                #
                # if xclass:
                #     return Web.text_area(text=message, readonly=True, rows=rows, xclass=xclass)
                # if rows and columns:
                #     return Web.text_area(text=message, readonly=True, rows=rows, cols=columns)

                return Web.text_area(text=message, readonly=True, rows=rows, xclass=xclass)
            else:
                if isinstance(message, int):
                    message = "%s" % message
                # message = "<code> %s </code>" % html.escape(message)
                message = "<code> %s </code>" % message
                return message
        else:
            return message


class Configs:
    config = {}
    count = 0
    compiled_regex = {}

    config_variables = {
        "VERSION": {
            "default": "2.00-RC27",
            "description": "Version of program"
        },
        "PIXEL_RATIO": {
            "default": 10,
            "description": "This will be used to make a multiplication at the column headers of each table"
                           " basically to adjust better new table web representation"
        },
        "APP_URL": {
            "default": "http://omega-x:8080/support",
            "description": "Web server URL to connect to"
        },
        "UPLOAD_PATH": {
            "default": "/home/r3support/www/uploads/customers",
            "description": "This represent actual physical directory where all logs will reside"
        },
        "RULES_FILE": {
            "default": "/home/r3support/www/cgi-bin/support/conf/logwatcher_rules.json",
            "description": "Specify path and filename used for match rules"
        },
        "HTML_START_TABLE": {
            "default": {
                "GLOBAL_SETTING": "<table border=1 cellpadding=10 cellspacing=0>",
                "File information": "<table width=\"90%\" border=1 cellpadding=2 cellspacing=0>",
                "Details for": "<table class=\"details\" width=\"90%\" border=1 cellpadding=10 cellspacing=0>",
                "Actual alerts": "<table class=\"screenboard\" border=1 cellpadding=10 cellspacing=0>",
                "Log Viewer": "<table class=\"logviewer\" width=\"85%\" border=1 cellpadding=10 cellspacing=0>",
                "Log Summary for": "<table class=\"logsummary\" id=\"logsummary\" width=\"85%\" border=1 cellpadding=10 cellspacing=0>"
            },
            "description": "This variable is used to apply modifications to tables, GLOBAL_SETTING affect all tables,"
                           " setting up table name, and settings will only apply to that table, "
                           "overriding GLOBAL_SETTINGS, this will force program to start table with specified settings"
        },
        "DASHBOARD": {
            "default": {
                "SHOW": [
                    "Production", "unknown", None
                ]
            },
            "description": "This variable will instruct program to show at the dashboard view errors with"
                           " that specified location"
        },
        "QUEUE_WORKERS": {
            "default": {
                "WORKER_COOPERATION_ALLOWED": True,
                "WORKER_COOPERATIVE_THREADS": 4,
                "WORKER_THRESHOLD_COOPERATION": 1000000,
                "WORKER_RESPONSE_TIMEOUT": 600,
                "WORKER_CHECK": 5,
                "WORKER_RGX_OPTIMIZATION_TEST": True,
                "WORKER_PROCESSING_ORDER": [
                    "SIMPLE(ASC)",
                    "COOPERATIVE(ASC)"
                ],
                "MAX_ADMIN_WORKERS": 4,
                "MAX_ANALYSIS_PROCESSES": 24,
                "MAX_WORKERS_PER_CUSTOMER": 4,
                "SHOW_WORKER_STATUS": False,
                "ANALYSIS_WORKER_CONSTRAINT": "customer"
            },
            "description": "Here you can modify behavior of workers for analysis, "
                           "WORKER_COOPERATION_ALLOWED: This will instruct program to use more workers to analyse. "
                           "WORKER_COOPERATIVE_THREADS: Maximum number of workers on the same analysis. "
                           "WORKER_THRESHOLD_COOPERATION: Number of lines that logfile must exceed to launch "
                           "cooperative workers. "
                           "WORKER_RESPONSE_TIMEOUT: Number of seconds Queue Manager program will wait to mark a worker"
                           "as 'STALLED' and kill it... or spanw a new one if is required. "
                           "WORKER_CHECK: This represents number of seconds that a worker will wait to report back. "
                           "WORKER_RGX_OPTIMIZATION_TEST: new analysis engine. "
                           "WORKER_PROCESSING_ORDER: [not implemented yet] will govern how analysis will be done,"
                           "starting with SIMPLE logfiles in ascendant mode(smaller first), then continue with"
                           "COOPERATIVE logs(bigger ones) also starting on ascendant mode. "
                           "MAX_ADMIN_WORKERS: number of ADMIN workers allowed, these workers will do admin task like"
                           " delete old logs. "
                           "MAX_ANALYSIS_PROCESSES: The maximum number of workers all the time, "
                           "including ADMIN workers. "
                           "MAX_WORKERS_PER_CUSTOMER: number of maximum workers that can work in a single "
                           "customer logs. "
                           "SHOW_WORKER_STATUS: This will show a small table a the top of page with worker statuses. "
                           "ANALYSIS_WORKER_CONSTRAINT: [not implemented] this will indicate what is the constraint "
                           "that will be used to limit number of workers on a specific customer"

        },
        "DATABASE": {
            "default": {
                "BATCH_COMMIT_EVERY": 1000,
                "BATCH_DELETE_ROWS": 10000,
                "LOGFILE_STORAGE_EXPIRE": 1,
                "STORE_FILES_ON_DB": True,
                "SEARCH_THRESHOLD": 500
            }
        },
        "ALERT_FILE": "/home/larry/workspace/metrix/alerts.json",
        "JIRA_ALERT_FILE": "/home/larry/IdeaProjects/metrix/jira_alerts.json",
        "FILE_FORMATS": {
            "gzip compressed data": "UNPACK",
            "tar": "UNPACK",
            "Zip archive data": "UNPACK",
            "7-zip archive data": "UNPACK",
            "ASCII text": "ANALYSE",
            "UTF-8 Unicode": "ANALYSE"
        },
        "HIDE_FROM_INFO_DETAILS": [
            "errors",
            "summary",
            "error_filename",
            "FILTERS"
        ],
        "ALERT_TYPE_LIST": [
            "info",
            "warning",
            "error",
            "ignore"
        ],
        "SHOW_ERROR_MAX_LINES": 50,
        "MAX_PAGES_TABS": 20,
        "TABLE_AUTO_NUMBERING_CONFIG": {
            "No": [
                5,
                "^",
                "^"
            ]
        },
        "TABLE_CONFIG": {
            "File information": {
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 200,
                    "COLUMNS": 175,
                    "ROWS": 10
                }
            },
            "Log Viewer": {
                "HIGHLIGHT": {
                    "Line": {
                        "--": "#ffa500"
                    },
                    "Severity": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 154,
                    "ROWS": 6
                },
                "LINE_DETAILS": {
                    "SHOW": True,
                    "COLOR_SCHEME": 1,
                    "COLUMN_DETAILS": [
                        "Message"
                    ],
                    "CHECK_OPTIONS": {
                        "Number of suspends": "SHOW_ONLY"
                    },
                    "CHECK": {
                        "Number of suspends": [
                            "numberOfSuspends=(\\d+)"
                        ],
                        "Session id": [
                            "session_id=([a-zA-Z0-9-]+)",
                            "sessionId=([a-zA-Z0-9-]+)"
                        ],
                        "Flow id": [
                            "flow-id=([a-zA-Z0-9-]+)",
                            "[Ff]low \\[([a-zA-Z0-9-]+)\\]",
                            "PersistCheckpoint\\(id=\\[([a-zA-Z0-9-]+)\\]",
                            "Flow with id ([a-zA-Z0-9-]+) has been waiting ",
                            "flowId=\\[([a-zA-Z0-9-]+)",
                            "flowId=([a-zA-Z0-9-]+)",
                            "Affected flow ids: ([a-zA-Z0-9- ,]+)"
                        ],
                        "TX id": [
                            "tx_id=([a-zA-Z0-9-]+)",
                            "NotaryException: Unable to notarise transaction ([a-zA-Z0-9-]+) :",
                            "hashOfTransactionId=([a-zA-Z0-9-]+)",
                            "([0-9A-Z]+)\\([0-9]+\\)\\s+->\\sStateConsumptionDetails\\(hashOfTransactionId=[0-9A-Z]+",
                            "The duplicate key value is\\s*\\(([A-Z0-9]+)\\)",
                            "hashOfTransactionId=([A-Z0-9]+)",
                            "ref=([a-zA-Z0-9-]+)",
                            "Tx \\[([a-zA-Z0-9-]+)\\]",
                            "Transaction \\[([a-zA-Z0-9-]+)\\]"
                        ],
                        "Owner id": [
                            "actor_owning_identity=CN=([0-9A-Za-z- .]+),",
                            "actor_owningIdentity=O=([0-9A-Za-z- .]+),"
                        ],
                        "Thread id": [
                            "thread-id=(\\d+)"
                        ],
                        "Party-Anonymous": [
                            "party=Anonymous\\(([a-zA-Z-0-9]+)\\)"
                        ],
                        "Message id": [
                            "id=[A-Z-]{4}([0-9-]{39})[0-9-]{2,};"
                        ]
                    },
                    "HIDE_DATAX": {
                        "HIDING_PASSWORD": "[Pp]assword\\s*=\\s*\\\"?([a-z0-9A-Z-@%+_\\?\\|\\/\\(\\)\\[\\]]*)\\\"?"
                    }
                },
                "TABLE_RENDER_ENGINE": {
                    "REQUEST_ON_TOP": 25,
                    "REQUEST_ON_BOTTOM": 80,
                    "BATCH_ROW_REQUEST": 100,
                    "IGNORE_COLUMN_SIZE": ["Message"],
                    "FORCE_HEADER_PREFIX": {
                        "Line": "header",
                        "Timestamp": "header",
                        "Severity": "header",
                        "Message": "header"
                    }
                }
            },
            "Temporal-LogViewer": {
                "COMMENTS": "This table is created to support Log Viewer scrolling",
                "HIGHLIGHT": {
                    "Line": {
                        "--": "#ffa500"
                    },
                    "Severity": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 154,
                    "ROWS": 6
                },
                "LINE_DETAILS": {
                    "SHOW": True,
                    "COLOR_SCHEME": 1,
                    "COLUMN_DETAILS": [
                        "Message"
                    ],
                    "CHECK_OPTIONS": {
                        "Number of suspends": "SHOW_ONLY"
                    },
                    "CHECK": {
                        "Number of suspends": [
                            "numberOfSuspends=(\\d+)"
                        ],
                        "Session id": [
                            "session_id=([a-zA-Z0-9-]+)",
                            "sessionId=([a-zA-Z0-9-]+)"
                        ],
                        "Flow id": [
                            "flow-id=([a-zA-Z0-9-]+)",
                            "[Ff]low \\[([a-zA-Z0-9-]+)\\]",
                            "PersistCheckpoint\\(id=\\[([a-zA-Z0-9-]+)\\]",
                            "Flow with id ([a-zA-Z0-9-]+) has been waiting ",
                            "flowId=\\[([a-zA-Z0-9-]+)",
                            "flowId=([a-zA-Z0-9-]+)",
                            "Affected flow ids: ([a-zA-Z0-9- ,]+)"
                        ],
                        "TX id": [
                            "tx_id=([a-zA-Z0-9-]+)",
                            "NotaryException: Unable to notarise transaction ([a-zA-Z0-9-]+) :",
                            "hashOfTransactionId=([a-zA-Z0-9-]+)",
                            "([0-9A-Z]+)\\([0-9]+\\)\\s+->\\sStateConsumptionDetails\\(hashOfTransactionId=[0-9A-Z]+",
                            "The duplicate key value is\\s*\\(([A-Z0-9]+)\\)",
                            "ref=([a-zA-Z0-9-]+)",
                            "Tx \\[([a-zA-Z0-9-]+)\\]",
                            "Transaction \\[([a-zA-Z0-9-]+)\\]"
                        ],
                        "Owner id": [
                            "actor_owning_identity=CN=([0-9A-Za-z- .]+),",
                            "actor_owningIdentity=O=([0-9A-Za-z- .]+),"
                        ],
                        "Thread id": [
                            "thread-id=(\\d+)"
                        ],
                        "Party-Anonymous": [
                            "party=Anonymous\\(([a-zA-Z-0-9]+)\\)"
                        ],
                        "Message id": [
                            "id=[A-Z-]{4}([0-9-]{39})[0-9-]{2,};"
                        ]
                    },
                    "HIDE_DATAX": {
                        "HIDING_PASSWORD": "[Pp]assword\\s*=\\s*\\\"?([a-z0-9A-Z-_\\?\\|\\/\\(\\)\\[\\]]*)\\\"?"
                    }
                }
            },
            "Jira Alerts": {
                "HIGHLIGHT": {
                    "Severity": {
                        "SEV1": "#ff0000/#ffffff",
                        "SEV2": "#ffa500"
                    }
                },
                "OPTIONS": {
                    "CLASS": "screenboard"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                }
            },
            "Customer logs": {
                "ORDER_ON": [
                    "Name",
                    "Number logs Loaded"
                ]
            },
            "Details for": {
                "HIGHLIGHT": {
                    "Error message Level": {
                        "INFO": "#3cb371",
                        "WARN": "#ffa500",
                        "ERROR": "#ff0000/#ffffff"
                    },
                    "Alert Level DataDog": {
                        "info": "#3cb371",
                        "warning": "#ffa500",
                        "error": "#ff0000/#ffffff"
                    },
                    "Alert Level (DataDog)_DropDown": {
                        "selected>info": "#3cb371",
                        "selected>warning": "#ffa500",
                        "selected>error": "#ff0000"
                    }
                },
                "ORDER_ON": [
                    "No",
                    "Line",
                    "Error type",
                    "Error message Level"
                ],
                "FILTER_ON": {
                    "Error message Level": {
                        "OPTIONS_SOURCE": "TABLE"
                    }
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 500,
                    "COLUMNS": 150,
                    "ROWS": 10
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Log Summary": {
                "HIGHLIGHT": {
                    "File Analysis status": {
                        "Complete": "#669900",
                        "Processing": "#cc9900",
                        "Pending": "#0066ff",
                        "Error": "#ff6666",
                        "*Not Started*": "#cc6699",
                        "On-Hold": "#9900cc/#ffffff",
                        "Cancelled": "#acac86",
                        "Preparing": "#99ceff",
                        "Delete": "#cc3300",
                        "Deleting": "#cc3300",
                        "Setting up": "#6699ff",
                        "Failed": "#acac86"
                    }
                },
                "FILTER_ON": {
                    "Jira Ticket": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "ticket_number"
                    },
                    "Corda Version": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "corda_version"
                    },
                    "File Analysis status": {
                        "OPTIONS_SOURCE": "DATABASE",
                        "TABLE_FIELD_NAME": "status"
                    }
                },
                "ORDER_ON": [
                    "Log",
                    "Uploaded on",
                    "Jira Ticket",
                    "Starting Date",
                    "Ending Date",
                    "File Name",
                    "Corda Version",
                    "Line count",
                    "Errors found",
                    "File Analysis status"
                ],
                "PAGINATION": {
                    "MAX_ITEMS_PER_PAGE": 50,
                    "MAX_TABS_PER_PAGE": 10
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 500,
                    "COLUMNS": 150,
                    "ROWS": 10
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Actual alerts": {
                "HIGHLIGHT": {
                    "Alert Level": {
                        "info": "#3cb371",
                        "warning": "#ffa500",
                        "error": "#ff0000/#ffffff"
                    }
                },
                "SORTING": {
                    "BY_COLUMN": "Time",
                    "DIRECTION": "reverse"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            },
            "Actual alerts_dropDown": {
                "HIGHLIGHT": {
                    "Alert Level": {
                        "selected>info": "#3cb371",
                        "selected>warning": "#ffa500",
                        "selected>error": "#ff0000"
                    }
                },
                "SORTING": {
                    "BY_COLUMN": "Time",
                    "DIRECTION": "reverse"
                },
                "TEXT_AREA_SETUP": {
                    "ACTIVATE_OVER_MAX_CHAR": 550,
                    "COLUMNS": 155,
                    "ROWS": 4
                },
                "HIGHLIGHT_ALL_LINE": False,
                "ACTIVATE_HIGHLIGHT": True
            }
        }
    }

    @staticmethod
    def load_config(file=None):
        """

        :return:
        """
        global app_path_support
        if not file:
            file = "%s/conf/support.json" % (app_path_support,)

        try:
            with open(file, "r") as fconfig:
                # Configs.config = json.load(fconfig)["CONFIG"]
                Configs.config = json.load(fconfig)
            print("Configuration loaded!")
            Rules.load()
        except IOError as io:
            print("ERROR loading config file: %s" % io)

            exit(1)
        except ValueError as ve:
            print("ERROR corrupted config file: %s" % ve)

            exit(1)

    @staticmethod
    def regex_expression(regex):
        """
        Expect a regex expresion, and will return compiled version if is stored,
        compile, store new compiled regex, and return compiled version
        :param regex: human readable regex string
        :return: compiled regex expression
        """

        regex_code = generate_hash(regex)

        if regex_code in Configs.compiled_regex:
            return Configs.compiled_regex[regex_code]

        compile_regex = re.compile(regex)

        Configs.compiled_regex[regex_code] = compile_regex

        return compile_regex

    @staticmethod
    def __init__(config_loaded, section="CONFIG"):

        Configs.config[section] = config_loaded

    @classmethod
    def get_config(cls, param=None, sub_param=None, section="CONFIG", similar=False):
        """
        Return requested parameter from config files.
        :param param: represents section at config file to look at
        :param sub_param: Represents a sub-section at the config file
        :param similar: it will indicate to do a similar search; as given sub_param is not exactly same as config, it
        is probably a sub-string of real subparameter.
        :return:
        """
        if not Configs.config:
            Configs.load_config()

        if not param and section in Configs.config:
            return Configs.config[section]

        if param not in Configs.config[section]:
            return None

        # If a similar search is being requested then do a reverse search, compare all sub_params from param
        # with the given sub_parameter
        #
        if similar:
            for each_subparam in Configs.config[section][param]:
                found_match = re.search(each_subparam, sub_param)
                if found_match:
                    return Configs.config[section][param][each_subparam]

            return None

        if not sub_param and param in Configs.config[section]:
            return Configs.config[section][param]

        if param and sub_param:
            if param in Configs.config[section] and sub_param in Configs.config[section][param]:
                return Configs.config[section][param][sub_param]
            else:
                return None

        # if param and sub_param:
        #     if param in Configs.config and sub_param in Configs.config[param]:
        #         return Configs.config[param][sub_param]
        #     else:
        #         # print("[CONFIGURATION] %s parameter do not exist under %s section" % (sub_param, param))
        #         return None

        if param in Configs.config[section]:
            return Configs.config[section][param]
        else:
            print("[CONFIGURATION] %s parameter do not exist under %s section" % (sub_param, param))
            return None

    @classmethod
    def set_config(cls, config_attributte=None, config_value=None, section="CONFIG"):
        """
        Set a value temporarly into config settings in memory, anything that is being set here will not be persistent on
        restarts
        :param config_attributte: attribute name to setup, if no attributte name is given, then method will expect a
        tree of values (a dictionary) to be attached to given section directly
        :param config_value: attribute value
        :param section: root section name for this attribute, all by default will be set under "CONFIG" branch section
        :return:
        """

        if config_attributte and config_value:
            Configs.config[section][config_attributte] = config_value

        if not config_attributte and config_value:
            Configs.config[section] = config_value

    @staticmethod
    def get_config_from(path_value):
        """

        :param path_value:
        :return:
        """
        configs = Configs.config
        variables = path_value.split(":")

        for each_variable in variables:
            if each_variable in configs:
                configs = configs[each_variable]
            else:
                return None

        return configs


class Rules:
    rule_list = {}

    def __init__(self):
        self.attributes = {}

    def add(self, attribute, value):
        self.attributes[attribute] = value

    def get(self, attribute):
        if attribute not in self.attributes:
            return None

        return self.attributes[attribute]

    def get_section(self, section, attribute):
        if section in self.attributes and attribute in self.attributes[section]:
            return self.attributes[section][attribute]

    def add_results(self, error_id, result, location):
        if "results" not in self.attributes:
            self.attributes["results"] = {}
        if location not in self.attributes["results"]:
            self.attributes["results"][location] = {}

        self.attributes["results"][location][error_id] = result

    def get_results(self, location=None):
        """
        Will return a list of results from this accordingly with the trigger conditions
        :param location: if location is being specified and exist, will return all results
        for such location, if no location is being specified will return all current stored results
        :return:
        """
        if "results" in self.attributes:
            if not location:
                return self.attributes["results"]
            else:
                if location in self.attributes["results"]:
                    return self.attributes["results"][location]

        return None

    def get_triggers(self, condition=None):
        """
        Will return a dictionary of current triggering actions for this rule, or the
        trigger statement for given condition
        :return:
        """
        triggers = {}

        if 'trigger' in self.attributes:
            if not condition:
                for each_trigger in self.attributes["trigger"]:
                    triggers[each_trigger] = self.attributes["trigger"][each_trigger]
            else:
                if condition in self.attributes['trigger']:
                    return self.attributes['trigger'][condition]
                else:
                    return None
        else:
            return None

        return triggers

    def get_parsed_trigger(self, condition=None):
        """
        Will return a dictionary of current triggering actions for this rule, or the
        trigger statement for given condition
        :return:
        """
        triggers = {}

        if 'parsed_trigger' in self.attributes:
            if not condition:
                for each_trigger in self.attributes["parsed_trigger"]:
                    triggers[each_trigger] = self.attributes["parsed_trigger"][each_trigger]
            else:
                if condition in self.attributes['parsed_trigger']:
                    return self.attributes['parsed_trigger'][condition]
                else:
                    return None
        else:
            return None

        return triggers

    def validate(self, error):
        error_id = error.get("error_id")

        if not error_id:
            return None

        results = None
        if not self.get_parsed_trigger():
            return None

        for each_condition in self.get_parsed_trigger():
            rule_actions = self.get_parsed_trigger(each_condition)

            if not rule_actions:
                return None

            if "location" in rule_actions:
                if rule_actions["location"] == "at same":
                    results = self.get_results(error.get("location"))
                if rule_actions["location"] == "at different":
                    results = self.get_results()

            if results and "occurrence" in rule_actions:
                if len(results) >= int(rule_actions["occurrence"]):
                    return results
                else:
                    # Given error do not pass the condition; then return a empty list
                    return {error.get("error_type"): {}}
            else:
                # Given error do not have
                return None

    def register(self):
        """
        Register a new rule
        :return:
        """
        self.parse_triggers()
        Rules.rule_list[self.get("name")] = self

    def parse_triggers(self):
        """
        Method to convert english text into parsed actions for current rule
        :return: a dictionary with parsed rules
        """
        action = {}
        rule_rgx = {
            "alert_on_occurrence": r"(\d+) time. (within) (\d+)[mhs] (at same|at different) (\w+)"
        }

        if self.get_triggers():
            for each_trigger in self.get_triggers():
                for rtrigger in self.get_triggers():
                    rtrigger_rgx = re.search(rule_rgx[each_trigger],
                                             self.get_triggers(rtrigger))
                    if rtrigger_rgx:
                        action[rtrigger] = {
                            "occurrence": rtrigger_rgx.group(1),
                            "within": int(rtrigger_rgx.group(3)),
                            "location": rtrigger_rgx.group(4),
                            "variable": rtrigger_rgx.group(5)
                        }
                        self.add("parsed_trigger", action)
        pass

    def get_attributes(self):
        return list(self.attributes)

    @staticmethod
    def get_rule(rule_name):
        if rule_name in Rules.rule_list:
            return Rules.rule_list[rule_name]

    @staticmethod
    def load():
        """
        Load all defined rules
        :return:
        """
        app_path = os.path.dirname(os.path.abspath(__file__))
        with open('%s/conf/logwatcher_rules.json' % (app_path,), 'r') as fregex_strings:
            rule_file = json.load(fregex_strings)

        for each_process in rule_file["WATCH_FOR"]:

            for each_rule in rule_file["WATCH_FOR"][each_process]:
                rule = Rules()
                rule.add("process", each_process)
                rule.add("name", each_rule)
                for each_attribute in rule_file["WATCH_FOR"][each_process][each_rule]:
                    rule.add(each_attribute, rule_file["WATCH_FOR"][each_process][each_rule][each_attribute])

                rule.register()

        load_corda_object_definition()


def generate_hash(stringData):
    hashstring = ""
    try:
        hashstring = hashlib.sha1(stringData.encode('utf8')).hexdigest()
    except UnicodeDecodeError as be:
        print("Error: %s" % be)
    return hashstring


def load_rules():
    app_path = os.path.dirname(os.path.abspath(__file__))
    with open('%s/conf/logwatcher_rules.json' % (app_path,), 'r') as fregex_strings:
        rule_file = json.load(fregex_strings)

    Configs.set_config(config_value=rule_file["VERSION"]["IDENTITY_FORMAT"], section="VERSION")
    Configs.set_config(config_value=rule_file["WATCH_FOR"], section="WATCH_FOR")


def draw_results(title, script_txt, file):
    import subprocess

    base_dir = os.path.dirname(file)
    #if not file:
    save_path = f"{app_path}/plugins/plantuml_cmd/data"
    if file:
        tmp_file = os.path.basename(file)
        if '.' in tmp_file:
            tmp = tmp_file.split('.')
            save_path = f"{app_path}/plugins/plantuml_cmd/data/{tmp[0]}"

    #else:
    #    filename = os.path.basename(file)
    #    save_path = f"{app_path}/{base_dir}/uml-{filename}"

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    if script_txt:
        with open(f"{save_path}/{title}.txt", "w") as uml:
            for each_line in script_txt:
                uml.write("%s\n" % (each_line,))

        if args.generate_uml:
            subprocess.call(['java', '-jar',
                             f'{app_path}/plugins/plantuml_cmd/plantuml.jar',
                             '-tsvg',
                             '-v',
                             f'{save_path}/{title}.txt'])

# ================================== Support import ==================================


class RegexLib:
    """
    Keep a cache of compiled regex, to be able to re-use them.
    """

    compiled_regex_cache = {}

    @staticmethod
    def use(rx_expression):
        """
        Will try to keep a cached compiled version of which regex are most used so it will not need to re-compile them
        again.
        :param rx_expression: regex expression to search for
        :return: compiled version of given regex
        """

        signature = generate_hash(rx_expression)

        if signature not in RegexLib.compiled_regex_cache:
            RegexLib.compiled_regex_cache[signature] = re.compile(rx_expression)
            return RegexLib.compiled_regex_cache[signature]

        return RegexLib.compiled_regex_cache[signature]

    class Search:
        # def __init__(self, pattern, string, flags=re.MULTILINE):
        #     """
        #     An emulation to what re.search commands does, but I will add more support for it as I need the command to
        #     search on the whole string and extract all matches with the format of what "re.search" does.
        #
        #     :param pattern: pattern to match
        #     :param string: string to search pattern
        #     :param flags: on re
        #     :return: re.search class
        #     """
        #     # Extract all values for this match
        #     self.match_found = re.findall(pattern, string, flags)
        #     # A plain list to track duplicated values
        #     tpaux = []
        #     # Extract all labels/group names for this specific regex pattern
        #     #
        #     group_name = re.findall(r"\?P\<([a-z-_]+)\>", pattern)
        #
        #     # Group assignation must be done in appearance order
        #     value_position = 0
        #     if self.match_found:
        #         self.tp = []
        #         for each_match in self.match_found:
        #             # Ignore first match as it represent whole original line to scan
        #             #
        #             if type(each_match) == tuple:
        #                 for each_item in each_match:
        #                     if value_position > 0:
        #                         if each_item not in tpaux:
        #                             self.tp.append({group_name[value_position-1]: each_item})
        #                             tpaux.append(each_item)
        #                     value_position += 1
        #             else:
        #                 self.tp.append({group_name[value_position]: each_match})
        #                 tpaux.append(each_match)

        def __init__(self, pattern, string, flags=re.MULTILINE):
            matches = re.finditer(pattern, string, flags)
            self.tp = ()
            for matchNum, match in enumerate(matches, start=1):
                #
                # print("Match {matchNum} was found at {start}-{end}:
                # {match}".format(matchNum=matchNum, start=match.start(),
                # end=match.end(), match=match.group()))

                for groupName in match.groupdict():
                    # print("Group {groupName}: {group}".format(groupName=groupName,
                    #                                           group=match.group(groupName)))
                    self.tp += ({groupName: match.group(groupName)},)

        def groupdict(self):
            """
            Will return a list of dictionaries containing, grouped key
            :return: a list of dictionaries
            """
            return self.tp

        def groupdictkeys(self):
            """
            Return all keys contained on list of dictionaries
            :return: a list of keys
            """
            keys = []
            for each_dict in self.tp:
                for each_key in each_dict:
                    keys.append(each_key)

            return keys

        def groups(self):
            """
            Will respond with a tuple list containing all values found
            :return: tuple
            """
            values = ()
            for each_dict in self.tp:
                for each_key in each_dict:
                    values += (each_dict[each_key],)

            return values

        def group(self, group=None):
            """
            Will return desired group, will return all groups if no-one is specified will return all groups
            :param group: requested group
            :return: required group or all group if none is specified
            """
            ltr = []
            if not group:
                return [tpx for tpx in self.tp if tpx.values()]

            if type(group) == str:

                for each_dict in self.tp:
                    for each_item in each_dict:
                        if each_item == group:
                            ltr.append(each_dict)

            return ltr


class CordaObject:
    """
    This class object will hold all transaction results and many other useful objects
    """
    id_ref = []
    list = {}
    relations = {}

    # Default UML references
    # This represents entities endpoints (for source and destination)
    default_uml_endpoints = {}
    # To store all uml setup
    uml = {}
    # Setup uml participants and initial fields
    uml_init = []
    uml_active_participants = []
    # An auxiliary field to allow me find out what are additional fields that need to be added to final summary table
    additional_table_fields = []
    # List of all participants; and roles
    uml_participants = {}
    # Reference registration: this will register each reference that "visit" a "UML_DEFAULT" object if proper flag is
    # enabled
    entity_register = {}
    # Define current object as Log Owner
    log_owner = None
    # References
    corda_object_regex = []
    corda_object_types = []

    # Clear group names cache
    #
    clear_group_list = {}

    def __init__(self):
        self.data = {}
        self.references = OrderedDictX()
        self.type = None

    @staticmethod
    def get_clear_group_list(raw_list):
        """
        This method will check if given list is already on memory; otherwise, will process the list, and add it into
        memory for further usage.

        :param raw_list: list that need to be checked
        :return:
        """

        signature = generate_hash("$$".join(raw_list))

        if signature in CordaObject.clear_group_list:
            return CordaObject.clear_group_list[signature]

        return CordaObject.add_clear_group_list(raw_list)

    @staticmethod
    def add_clear_group_list(raw_list):
        """
        Add a new list with all groups cleared
        :param raw_list: list with required groups to be cleared
        :return: initial group given; with no groups names.
        """

        signature = generate_hash("$$".join(raw_list))
        no_group_list = []
        for each_item in raw_list:
            # Expand all macro variables from their pseudo form
            expand_macro = build_regex(each_item, nogroup_name=True)
            # Check how many "group names" are within the given string
            #
            clear_groups = expand_macro
            for each_group in range(expand_macro.count('?P<')):
                start = clear_groups.find('?P<')
                end = clear_groups.find('>')+1
                clear_groups = clear_groups.replace(clear_groups[start:end], "")

            no_group_list.append(clear_groups)

        CordaObject.clear_group_list[signature] = no_group_list

        return no_group_list

    @staticmethod
    def get_cordaobject_regex_definition():
        """

        :return:
        """
        return CordaObject.corda_object_regex

    @staticmethod
    def get_cordaobject_types_definition():
        """

        :return:
        """
        return CordaObject.corda_object_types

    @staticmethod
    def set_cordaobject_regex_definition(corda_regex_definition):
        """

        :return:
        """
        CordaObject.corda_object_regex = corda_regex_definition

    @staticmethod
    def set_cordaobject_types_definition(corda_type_definition):
        """

        :return:
        """
        CordaObject.corda_object_types = corda_type_definition

    @staticmethod
    def reset():
        """
        Clears up actual object and deletes all info
        :return:
        """
        CordaObject.list = {}
        CordaObject.uml_init = []
        CordaObject.log_owner = None
        CordaObject.uml_participants = {}
        CordaObject.uml_active_participants = []
        CordaObject.additional_table_fields = []
        CordaObject.id_ref = []
        CordaObject.relations = {}

    def get_reference_id(self):
        return self.data['ref_id']

    def add_data(self, cproperty, value):
        """

        :param cproperty:
        :param value:
        :return:
        """
        if not self:
            pass
        self.data[cproperty] = value

        # Extract extra data
        if "=" in value:
            if ";" in value:
                for each_data in value.split(";"):
                    if not each_data:
                        continue
                    values = each_data.split("=")
                    if len(values) > 1:
                        self.data[values[0].strip()] = values[1].strip().replace("}", "")

            for each_data in value.split(","):
                if not each_data:
                    continue
                values = each_data.split("=")
                if values:
                    if len(values) > 1:
                        self.data[values[0].strip()] = values[1].strip().replace("}", "")

    def set_type(self, each_object):
        """
        Set object type
        :param each_object:
        :return:
        """

        self.type = each_object

    def set_reference_id(self, reference_id):
        """
        Will set object reference id
        :param reference_id: reference id to be assigned
        :return: void
        """
        self.data['id_ref'] = reference_id

    def get_data(self, data_property):
        """
        Return value
        :param data_property:
        :return:
        """

        if data_property in self.data:
            return self.data[data_property]
        else:
            return None

    def get_relationship(self):
        """
        Will check what fields will be key to make relationships between transactions/flows
        :return:
        """

        relation = Configs.get_config("IDENTIFICATION", self.type, "OBJECT")

        if not relation:
            print("No relationship defined for %s" % self.type)
            return None

        return relation

    def add_object(self):
        """
        Add given object into internal class list of objects
        :return:
        """

        if self.type not in CordaObject.list:
            CordaObject.list[self.type] = OrderedDictX()

        if self.data["id_ref"] not in CordaObject.id_ref:
            # Add a new reference found into the list
            CordaObject.id_ref.append(self.data["id_ref"])

        if self.data["id_ref"] not in CordaObject.list[self.type]:
            CordaObject.list[self.type][self.data["id_ref"]] = self

    def add_relation(self):
        """

        :return:
        """

        if self.type not in CordaObject.relations:
            CordaObject[self.type] = {}

        relations = self.get_relationship()

    # def load_from_database(self):
    #     """
    #
    #     :return:
    #     """
    #     global database
    #     # TODO: Aqui estoy tratando de cargar las referencias por "demanda" esto ayudara a cargar las cosas
    #     #  cuando sean necesarias lo cual servira cuando hay miles de referencias... este metodo carga
    #     #  la referencia que es requerida, ahora bien creo que tengo que revisar la re-asignacion porque el
    #     #  objeto va a sobre escribir la seccion `data` que contiene mucha informacion... de verda es requerido???
    #     #
    #     #
    #
    #     query = database.query(support.TracerReferences).filter(and_(
    #         support.TracerReferences.logfile_hash_key == self.get_data('logfile_hash_key'),
    #         support.TracerReferences.logfile_hash_key == self.get_data('id_ref')).order_by(
    #         support.TracerReferences.line_no)
    #     ).all()
    #
    #     for each_reference in query:
    #         self.add_reference(each_reference.line_no, json.loads(each_reference.details))
    #         self.data = json.loads(each_reference.data)

    def get_references(self, line_no=None, field=None):
        """
        Will return all objects where this reference was found.

        :param line_no: this is the line number to get from references
        :param field: If field is valid from reference storage this will be returned.
        :return: depends on parameters given (list, dictionary, or string)
        """

        cobject = self

        # Check if object has references

        if not cobject.references:
            return None

        if cobject.references and not line_no and not field:
            return cobject.references

        if cobject.references and line_no and not field:
            if line_no in cobject.references:
                return cobject.references[line_no]
            else:
                return None

        # if there's no line_no reference, I can't return proper reference, or I got the line_no, but that line is not
        # in the references, then return None

        if not line_no or line_no and line_no not in cobject.references:
            return None

        if field:
            if field in cobject.references[line_no]:
                return cobject.references[line_no][field]

        return None

    @staticmethod
    def add_register(control, reference, reference_type, state, line_no, cause=None):
        """
        Will add given reference into control section, this will highlight and count number of references on each
        control entity (like flow hospital)
        :param cause: reason why need to be registered
        :param reference_type: of reference ID
        :param state: This state is coming from actual config file; Entity setup
        :param line_no: actual line number
        :param reference: reference ID
        :param control: name of control entity (like flowhospital)
        :return:
        """

        if control not in CordaObject.entity_register:
            CordaObject.entity_register[control] = {
                "state": state
            }

        if reference_type not in CordaObject.entity_register[control]:
            CordaObject.entity_register[control][reference_type] = {}

        if reference not in CordaObject.entity_register[control][reference_type]:
            CordaObject.entity_register[control][reference_type][reference] = {
                "lines": {line_no: cause}
            }
        else:
            if line_no not in CordaObject.entity_register[control][reference_type][reference]["lines"]:
                CordaObject.entity_register[control][reference_type][reference]["lines"][line_no] = cause

    @staticmethod
    def set_participant_role(participant, role, attach_usages=False):
        """
        Method that will setup properly endpoint and attach endpoint references if is possible
        This will help for example to set the log Owner, this will help with messages that do not explicitly give
        source or destination of message
        :param participant: a string (essentially a Party / uml_object)
        :param role: role that need to be setup for this uml_object
        :param attach_usages: Will indicate if default values will be attached to the default_uml_endpoints

        :return: void
        """
        party = Party.get_party(participant)

        if role == "log_owner":
            CordaObject.log_owner = participant

        if attach_usages:
            if Configs.get_config(section="UML_ENTITY", param="OBJECTS", sub_param="log_owner"):
                default_endpoint = Configs.get_config(section="UML_ENTITY", param="OBJECTS", sub_param=role)
                if "USAGES" in default_endpoint:
                    # CordaObject.default_uml_endpoints[CordaObject.log_owner] = default_endpoint["USAGES"]
                    # CordaObject.default_uml_endpoints[CordaObject.log_owner]["ROLE"] = role
                    CordaObject.default_uml_endpoints[participant] = default_endpoint["USAGES"]
                    CordaObject.default_uml_endpoints[participant]["ROLE"] = role
                else:
                    print("Unable to attach default usages for '%s': %s" % (role, participant))
                    print("Configuration file is not having this config section!")
            else:
                print("There's no config section for '%s' unable to define default properly" % (role,))
                print("Default destination/source will be shown as 'None' at UML")

        # Check if this participant has extra endpoints to attach (A notary for example)
        #
        if party.get_corda_role():
            additional_endpoints = Configs.get_config(section="UML_ENTITY", param="OBJECTS",
                                                      sub_param=party.get_corda_role().lower())
            if party.get_corda_role().lower() in additional_endpoints:
                additional_endpoints = additional_endpoints[party.get_corda_role().lower()]
            else:
                additional_endpoints = None

            if additional_endpoints and 'USAGES' in additional_endpoints:
                for each_endpoint in additional_endpoints['USAGES']:
                    additional_usages = additional_endpoints['USAGES'][each_endpoint]['EXPECT']
                    CordaObject.default_uml_endpoints[participant][each_endpoint]['EXPECT'].extend(additional_usages)


    @staticmethod
    def get_log_owner():
        """
        Will return who is the owner of current log (if it is know)
        :return: String representing a Party / uml_object
        """

        return CordaObject.log_owner

    @staticmethod
    def analyse(original_line):
        """
        Analyse line and covert it into UML
        :return:
        """

        uml_definition = Configs.get_config(section="UML_DEFINITIONS")
        uml_rtn = {}
        uml_step = {}
        # Loop over all UML definitions
        for each_uml_definition in uml_definition:
            # now for each uml definition, try to see if we have a match
            #
            # Stage 1: Find out which UML command should be applied to given line, as all UML_DEFINITIONS are
            # created as "meta-definitions" I need below line to extract actual regex that need to be used...
            # In this section, i will loop over all defined UML commands, and find out if this line match any of them
            #

            expect_to_use = regex_to_use(uml_definition[each_uml_definition]["EXPECT"], original_line)

            if expect_to_use is None:
                # If we do not have any valid regex for this line, try next list
                continue

            regex_expect = uml_definition[each_uml_definition]["EXPECT"][expect_to_use]
            each_expect = build_regex(regex_expect)
            # each_expect = RegexLib.use(each_expect)
            match = RegexLib.Search(build_regex(each_expect), original_line)
            # match = each_expect.search(original_line)
            if match:
                # rx = RegexLib.Search(build_regex(each_expect), original_line)
                grp = 1
                if match.groupdict():

                    for each_dict in match.groupdict():
                        for each_field in each_dict:
                            ignore = False

                            if 'IGNORE' in uml_definition[each_uml_definition]:
                                for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                                    if each_ignore_word in original_line:
                                        ignore = True
                            # Check if this specific statement has some specific words that should prevent this
                            # assignation to take place
                            #
                            if not ignore:
                                # CordaObject.add_uml(match.group(grp), each_field)
                                # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                                # if match.group(each_field):
                                # grp_value = match.group(each_field).strip().strip(".")
                                grp_value = each_dict[each_field]

                                if "OPTIONS" in uml_definition[each_uml_definition] and \
                                        "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                    already_defined = False
                                    for each_definition in CordaObject.uml_init:
                                        if grp_value in each_definition:
                                            already_defined = True
                                    if already_defined:
                                        continue
                                    else:
                                        uml_def = CordaObject.get_corda_object_definition_for(each_uml_definition)
                                        # grp_value = define_field_limits(grp_value, uml_def)
                                        if uml_def:
                                            CordaObject.add_uml_object(grp_value, uml_def)
                                            # CordaObject.uml_init.append('%s "%s"' % (uml_def, grp_value))
                                        else:
                                            CordaObject.add_uml_object(grp_value, each_uml_definition)
                                            # CordaObject.uml_init.append('%s "%s"' % (each_uml_definition,
                                            #                                          grp_value))
                                else:
                                    uml_set = False
                                    # Search each field on given line to see if it exists and extract its value
                                    #
                                    for each_field_def in uml_definition[each_uml_definition]["FIELDS"]:
                                        if ":" in each_field_def:
                                            extract_field = each_field_def.split(":")[1]
                                        else:
                                            extract_field = each_field_def
                                            print("Warning: This definition is missing proper labels on regex\n"
                                                  "%s" % each_expect)

                                        # if value for this field already exist on the EXPECTED (default one) then
                                        # get it otherwise, get proper expect to extract it from current log line

                                        if each_field == extract_field:
                                            uml_set = True
                                            uml_rtn[grp_value] = each_field_def
                                            uml_step[each_uml_definition] = uml_rtn

                                    if not uml_set:
                                        print("Warning unable to set proper values for group %s, not UML group"
                                              " set on '%s' definition" % (each_field, each_uml_definition))
                                        print("Offending line: \n%s" % original_line)

                else:
                    #
                    # TODO: no estoy seguro para que hice esta seccion, por lo que se ve en la logica ^^
                    #  nunca se llegara a alcanzar esta parte porque match.groupdict() "SIEMPRE" devolvera
                    #  un grupo amenos que no tenga la definicion de grupo en el "EXPECT" lo cual seria un error
                    for each_field in uml_definition[each_uml_definition]["FIELDS"]:
                        if grp > len(match.groups()):
                            print("Warning: There's no group to cover %s definition on '%s' setting...!" %
                                  (each_field, each_uml_definition))
                            print("Scanned line:\n %s" % (original_line,))
                        else:
                            ignore = False
                            if 'IGNORE' in uml_definition[each_uml_definition]:
                                for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                                    if each_ignore_word in original_line:
                                        ignore = True
                            # Check if this specific statement has some specific words that should prevent this
                            # assignation to take place
                            #
                            if not ignore:
                                # CordaObject.add_uml(match.group(grp), each_field)
                                # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                                if match.group(grp):
                                    grp_value = match.group(grp).strip().strip(".")
                                    # grp_value = define_field_limits(grp_value, each_uml_definition)

                                    if "OPTIONS" in uml_definition[each_uml_definition] and \
                                            "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                        if '%s "%s"' % (each_uml_definition, grp_value) not in CordaObject.uml_init:
                                            CordaObject.add_uml_object(grp_value, each_uml_definition)
                                            # CordaObject.uml_init.append('%s "%s"' % (each_uml_definition,
                                            #                                          grp_value))
                                        else:
                                            continue
                                    else:

                                        uml_rtn[grp_value] = each_field
                                        uml_step[each_uml_definition] = uml_rtn

                        grp += 1

                    # A match message was found (uml action definition), it doesn't make sense to go through the
                    # rest This will avoid to do a regex of each 'EXPECT' over action UML_DEFINITION
                    #break

            if uml_step and each_uml_definition in uml_step:
                # Will loop over the required fields for this uml action, and try to pull the info on the log line
                # also will skip any field that was already populated
                for each_required_field in uml_definition[each_uml_definition]["FIELDS"]:
                    # first check if we had value already...

                    if each_required_field in uml_step[each_uml_definition].values():
                        # We got this field covered, let's see next one...
                        continue

                    # First, obtain way how to extract desired field
                    # This definition should be under "CORDA_OBJECT_DEFINITIONS/OBJECTS"
                    if ':' in each_required_field:
                        uml_field, field_role = each_required_field.split(":")
                    else:
                        uml_field, field_role = each_required_field
                    # Get actual Corda Object Definition branch for this particular object
                    codefinition = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                      param="OBJECTS",
                                                      sub_param=field_role)

                    ignore_this_clause = False
                    if codefinition and "IGNORE" in codefinition:
                        # Check if we need to ignore this message...

                        for each_ignore_line in codefinition["IGNORE"]:
                            ignore_this = re.search(each_ignore_line, original_line)
                            if ignore_this:
                                # We don't need to search destination on this section as it could potentially clash
                                # with source
                                ignore_this_clause = True
                                break

                    if ignore_this_clause:
                        continue

                    expect_list = CordaObject.get_corda_object_definition_for(field_role, expect=True)

                    if expect_list is None:
                        # This mean there's no definition how to get this field out from source log line, which is an
                        # error
                        print("ERROR: I can't find proper definition of 'EXPECT' for %s please check this"
                              " as this will impact my ability to get proper UML definitions for current log" %
                              each_required_field)
                        continue
                    # Now go over each expect definition, and try to get field info...
                    #
                    for each_expect in expect_list:
                        # Make sure all regex substitution are done
                        fill_regex = build_regex(each_expect)
                        # now with proper regex, check message to see if we can gather field data
                        field_match = re.search(fill_regex, original_line)

                        # Check if we have a match
                        if field_match and field_match.groupdict():
                            if uml_field in field_match.groupdict():
                                grp_value = field_match.group(uml_field)
                                if grp_value in uml_rtn:
                                    # Do no overwrite previous values...
                                    continue
                                uml_rtn[grp_value] = each_required_field
                                uml_step[each_uml_definition] = uml_rtn
                                break
                            else:
                                for each_field_found in field_match.groupdict():
                                    if each_field_found in each_required_field:
                                        grp_value = field_match.group(each_field_found)
                                        uml_rtn[grp_value] = each_required_field
                                        uml_step[each_uml_definition] = uml_rtn
                                        break

        return uml_step

    @staticmethod
    def get_corda_object_definition_for(cobject, expect=False):
        """
        Will check against "CORDA_OBJECT_DEFINITIONS" section at configuration file to define what kind of object
        for UML should be related to
        :param cobject: name of the object to check out
        :return: actual UML Object name
        """

        # Basic Corda object definition
        corda_uml_definition = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS")
        # Check if given cobject has more detailed way to identify it. This need to be done because in the case of
        # Transaction the simple __tx_id__ definition is too ambiguous and can be confused with something else that is
        # not a proper transaction...

        # Detailed corda object description -- This definition *MUST-BE* Atomic only one macro-variable must appear,
        # on each line.
        corda_object_description = Configs.get_config(section="CORDA_OBJECTS")
        variable_to_search = "__%s__" % (cobject,)
        for each_corda_object in corda_object_description:
            for each_expect in corda_object_description[each_corda_object]['EXPECT']:
                if variable_to_search in each_expect:
                    return corda_object_description[each_corda_object]['EXPECT']

        # In the case no detailed description exist for this object, continue with the basic definition...

        if expect and cobject in corda_uml_definition.keys():
            if 'EXPECT' in corda_uml_definition[cobject]:
                return corda_uml_definition[cobject]['EXPECT']
            else:
                return None

        for each_definition in corda_uml_definition:
            if "APPLY_TO" in corda_uml_definition[each_definition] \
                    and cobject in corda_uml_definition[each_definition]["APPLY_TO"] and not expect:
                return each_definition

        return None

    @staticmethod
    def check_default_uml_references(line):
        """
        Check for default references to collect; when no source or destination are found on log message this will
        help to tell to program what can be used to infer source or destination references when they are missing
        for example, when a message is being sent back from a remote source will be the node that owns the actual log
        that will be the destination...
        Warning: This process only works when program is able to find automatically log_owner or notary; otherwise
        these entities when are setup manually will not have proper default endpoints defined!
        :param line: line to check
        :return:
        """

        uml_defaults = Configs.get_config(section="UML_ENTITY", param="OBJECTS")

        if not uml_defaults:
            return

        for each_default in uml_defaults:
            # if EXPECT option is found, this mean value should be extracted from the log itself
            # This EXPECTS will try to identify automatically an entity based on the regex contains on that expect, for
            # example identify automatically the log_owner, or a notary... and then add actual regex that will
            # recognise them as default endpoints. THIS WILL NOT WORK WHEN these are set manually (by the user)
            if "EXPECT" in uml_defaults[each_default]:
                usage_expect_counter = 0
                for each_usage_expect in uml_defaults[each_default]["EXPECT"]:
                    nregex = build_regex(each_usage_expect)
                    match = re.search(nregex, line)
                    if match and each_default not in CordaObject.default_uml_endpoints:
                        if each_default in match.groupdict():
                            # CordaObject.default_uml_endpoints[each_default] = match.group(each_default)
                            if match.group(each_default) not in CordaObject.default_uml_endpoints:
                                CordaObject.default_uml_endpoints[match.group(each_default)] = {}
                            for each_usage in uml_defaults[each_default]['USAGES']:
                                CordaObject.default_uml_endpoints[match.group(each_default)][each_usage] = \
                                    uml_defaults[each_default]['USAGES'][each_usage]

                            check_role = Configs.get_config(section="UML_ENTITY",
                                                            param="OBJECTS",
                                                            sub_param=each_default)
                            activate_role = False
                            if "ACTIVATE_ROLE" in check_role:
                                if check_role["ACTIVATE_ROLE"]:
                                    activate_role = check_role["ACTIVATE_ROLE"]
                            # if each_default == "log_owner":
                            if activate_role:
                                CordaObject.default_uml_endpoints[
                                    match.group(each_default)
                                ]["ROLE"] = each_default

                        else:
                            # I need to check if there's a default definition name that is not "standard" if so,
                            # then need to check "RETURN_OBJECT" then return that one instead of the name of
                            # this section; this will help to correct issue at the UML end definition, an example of
                            # this is the "log_owner" object that has no UML definition, this object in fact will be
                            # returned as "uml_object" to make it compatible with UML definition, but program will know
                            # that in this specific example, this uml_object is the Owner of current log, this is done
                            # to setup the default source/destination for some messages that are lacking of it
                            # a good example is saving into the Vault... the destination is the vault, but the source
                            # in this case will be the "log_owner"...
                            #
                            return_object = None
                            entity_list = dict(Configs.get_config(section="UML_ENTITY",
                                                                  param="OBJECTS",
                                                                  sub_param=each_default)['USAGES'])
                            # for each_endpoint in uml_defaults[each_default]["USAGES"]:
                            # print("Fuera del loop...")
                            for each_endpoint in entity_list:
                                if "RETURN_OBJECT" in uml_defaults[each_default]["USAGES"][each_endpoint]:
                                    return_object = uml_defaults[each_default]["USAGES"][each_endpoint]["RETURN_OBJECT"]
                                    for each_return_object in return_object:
                                        if each_return_object in match.groupdict():

                                            # for each_usage in uml_defaults[each_default]['USAGES']:
                                            for each_usage in entity_list:
                                                # print("Segundo loop test dict:", entity_list.keys())
                                                # print("Segundo loop org dict:",
                                                # uml_defaults[each_default]['USAGES'].keys())
                                                if match.group(each_return_object) not in \
                                                        CordaObject.default_uml_endpoints:
                                                    CordaObject.default_uml_endpoints[
                                                        match.group(each_return_object)
                                                    ] = {}
                                                CordaObject.default_uml_endpoints[
                                                    match.group(each_return_object)
                                                ][each_usage] = uml_defaults[each_default]['USAGES'][each_usage]
                                                check_role = Configs.get_config(section="UML_ENTITY",
                                                                                param="OBJECTS",
                                                                                sub_param=each_default)
                                                activate_role = False
                                                if "ACTIVATE_ROLE" in check_role:
                                                    if check_role["ACTIVATE_ROLE"]:
                                                        activate_role = check_role["ACTIVATE_ROLE"]
                                                # if each_default == "log_owner":
                                                if activate_role:
                                                    CordaObject.default_uml_endpoints[
                                                        match.group(each_return_object)
                                                    ]["ROLE"] = each_default
                                                    if not CordaObject.get_log_owner():
                                                        CordaObject.set_participant_role(
                                                            match.group(each_return_object),
                                                            role=each_default)

                                                # Finish the loop if I got the right definition do not
                                            # need more interactions
                                            break

                            if not return_object:
                                CordaObject.default_uml_endpoints[each_default] = each_default

                    # else:
                    #     # TODO: El problema que hay aqui es que la referencia a default esta iendo a "log_owner" o
                    #     #  por ejemplo "notary" debo hallar una manera de cambiar los roles a sus respectivos contra
                    #     #  partes es decir en el caso del log_owner deberia aparecer el x500 name en su lugar.
                    #     #  en la base de datos aparentemente aparece la informacion de el rol tal vez pueda usar eso
                    #
                    #     if "USAGES" in uml_defaults[each_default]:
                    #         for each_usage in uml_defaults[each_default]["USAGES"]:
                    #             usage_expect_counter = 0
                    #             for each_usage_expect in uml_defaults[each_default]["USAGES"][each_usage]["EXPECT"]:
                    #                 match_usage = re.search(each_usage_expect, line)
                    #                 if match_usage:
                    #                     if len(match_usage.groups()) == 0:
                    #                         if each_default not in CordaObject.default_uml_endpoints:
                    #                             CordaObject.default_uml_endpoints[each_default] = {}
                    #                         CordaObject.default_uml_endpoints[each_default][each_usage] = \
                    #                             uml_defaults[each_default]["USAGES"][each_usage]
                    #                     else:
                    #                         if each_default not in CordaObject.default_uml_endpoints:
                    #                             CordaObject.default_uml_endpoints[each_default] = {}
                    #
                    #                         default_object = uml_defaults[each_default]["USAGES"]\
                    #                             [each_usage]["RETURN_OBJECT"][usage_expect_counter]
                    #                         CordaObject.default_uml_endpoints[each_default] = default_object
                    #
                    #                 usage_expect_counter += 1
            else:
                if "USAGES" in uml_defaults[each_default]:
                    for each_usage in uml_defaults[each_default]["USAGES"]:
                        usage_expect_counter = 0
                        for each_usage_expect in uml_defaults[each_default]["USAGES"][each_usage]["EXPECT"]:
                            match_usage = re.search(each_usage_expect, line)
                            if match_usage:
                                if len(match_usage.groups()) == 0:
                                    if each_default not in CordaObject.default_uml_endpoints:
                                        CordaObject.default_uml_endpoints[each_default] = {}
                                    CordaObject.default_uml_endpoints[each_default][each_usage] = \
                                        uml_defaults[each_default]["USAGES"][each_usage]
                                else:
                                    if each_default not in CordaObject.default_uml_endpoints:
                                        CordaObject.default_uml_endpoints[each_default] = {}

                                    default_object = uml_defaults[each_default]["USAGES"] \
                                        [each_usage]["RETURN_OBJECT"][usage_expect_counter]
                                    CordaObject.default_uml_endpoints[each_default] = default_object

                            usage_expect_counter += 1

    @staticmethod
    def get_type(id_ref):
        """
        Search which type belongs to given reference
        :return: A string representing type of reference object, if is not found will return None
        """

        for each_type in CordaObject.list:
            if id_ref in CordaObject.list[each_type]:
                return each_type

        return None

    def add_reference(self, line, creference):
        """
        Add a new reference line to this object, this will be used to make the tracing of this object
        this action will also:
         - analyse and try to create a UML statements
         - analyse and extract actual status for the message
        :param line: line where this reference was found
        :param creference: a Dictionary that contains data to be referenced
        :return: None
        """

        # if the object has already "field_stage" means that it was already analised, and is coming from database...
        if "field_name" not in creference:
            object_type = CordaObject.get_type(self.data["id_ref"])
            if not object_type:
                print("Object without any type defined: %s" % self.data["id_ref"])
                print("Found in this line %s: %s" % (line, creference))
                return

            # Analyse UML -- Create UML step
            uml = self.analyse(creference["message"])

            if uml:
                if "uml" not in creference:
                    creference["uml"] = []
                # Add only one uml reference, do not make duplicates.
                if uml not in creference["uml"]:
                    creference["uml"].append(uml)

            # Extract stage
            # Get description setup for this reference:
            corda_object_reference = Configs.get_config(self.type, "ANALYSIS", section="CORDA_OBJECTS")
            if corda_object_reference and "EXPECT" in corda_object_reference:
                for each_regex_analysis in corda_object_reference["EXPECT"]:
                    # Apply regex to message line to extract a meaningful message
                    # analysis_group = re.search(each_regex_analysis, creference["message"])
                    reach_regex_analysis = RegexLib.use(each_regex_analysis)
                    analysis_group = reach_regex_analysis.search(creference["message"])

                    if analysis_group:
                        if len(analysis_group.groups()) > len(corda_object_reference["EXPECT"][each_regex_analysis]):
                            print("Unable to extract status properly; analysis has more group than defined fields")
                            print("Analysis group regex: '%s'" % each_regex_analysis)
                            print("expected groups: %s vs %s group found" %
                                  (len(corda_object_reference["EXPECT"][each_regex_analysis]),
                                   analysis_group.groups()))
                            continue
                        group_count = 1
                        for each_group in analysis_group.groups():
                            field = corda_object_reference["EXPECT"][each_regex_analysis][group_count-1]
                            creference[field] = each_group
                            if "field_name" not in creference:
                                # Add field name reference for later use (Print table with this field)
                                creference["field_name"] = []

                            creference["field_name"].append(field)
                            # Store this field to be able to create final summary table
                            if field not in CordaObject.additional_table_fields:
                                CordaObject.additional_table_fields.append(field)

        self.references[line] = creference
        # CordaObject.list[object_type][id_ref].references[line] = creference

    @staticmethod
    def get_object(ref_id):
        """
        Will return a corda object identified by ref_id
        :param ref_found:
        :return:
        """

        otype = CordaObject.get_type(ref_id)

        if not otype:
            return None

        return CordaObject.list[otype][ref_id]

    @staticmethod
    def add_uml_object(incoming_uml_object, uml_role):
        """
        Add new objects
        Also, it will try to identify if given object has a role

        :param incoming_uml_object: Normally party name
        :param uml_role: role assigned to this party (participant, control node, etc)

        :return:
        """
        # Add participants with proper UML role
        # standard_party = check_party(uml_object)

        # Verify if this UML object definition has a rule to accomplish
        rules = Configs.get_config(uml_role, "RULES", "UML_DEFINITIONS")
        if rules:
            uml_list = CordaObject.uml_apply_rules(incoming_uml_object, rules)
        else:
            uml_list = [incoming_uml_object]

        for umlobject in uml_list:
            uml_object = '%s "%s"' % (uml_role, umlobject)
            party = Party()
            party.name = umlobject
            party.role = uml_role
            # if I'm not able to add this new party name, means it is already in.
            if not party.add():
                continue

            CordaObject.uml_init.append(uml_object)

            CordaObject.uml_participants[uml_object] = ""
            # Check object Role...

    @staticmethod
    def uml_apply_rules(uml_object, rules):
        """
        Apply given rule to this object
        :return:
        """
        global participant_build
        participant_build_counter = 0
        x500_key_count = {}
        x500_build = ""
        rules_details = {}
        force_x500_split = False
        # This will read rules, and expand them to more detailed object
        for each_rule in rules:
            rl = re.search(r"(\d+):([=>]):([OM])", rules[each_rule])
            if not rl:
                print("Warning malformed rule for %s key found at configuration file" % each_rule)
                continue

            rules_details[each_rule] = {
                "occurrences": int(rl.group(1)),
                "operator": rl.group(2),
                "type": rl.group(3)
            }

        #
        # Split the x500 name in sections, using ","
        # then apply rule to each section.
        #

        allowed_keys = "".join(sorted(sorted(set("".join(rules.keys())))))
        allowed_keys_list = list(rules.keys())
        # search for proper formed x500 keys on given string...
        # following line will extract all keys from given string
        x500_keys = re.findall(r"([%s]{1,2}=[^\n\!\@\#\$\%\^\*\(\)~\?\>\<\&\/\\\,\.\",]*)" % allowed_keys, uml_object)
        number_of_keys = len(x500_keys)
        x500_key_counter = 0
        for each_x500_key in x500_keys:
            x500_key_counter += 1
            # Extract proper key, and it's value; will use re.search to manage re groups
            #
            x500_key_check = re.search(r"([%s]{1,2}=[^\n\!\@\#\$\%\^\*\(\)~\?\>\<\&\/\\\,\.\",]*)" % allowed_keys, each_x500_key)

            # count how many times given key appears

            if x500_key_check.group(1) not in x500_key_count:
                x500_key_count[x500_key_check.group(1)] = 1
            else:
                x500_key_count[x500_key_check.group(1)] += 1

            # Check if given key it is found at the rules.
            #
            if x500_key_check.group(1) not in rules:
                print("Warning, %s x500 keyword not fully supported on corda's x500 names" % x500_key_check.group(0))
                print("There's no proper rule to manage it, will be added anyway and ignored...")
                x500_key_check += x500_key_check.group(0) + ","
                participant_build[participant_build_counter] += x500_key_check.group(0) + ","
            else:
                # Check if x500 name is complete:
                mandatory_key = False
                force_x500_split = False
                for each_key in allowed_keys_list:
                    if ":M" in rules[each_key]:
                        mandatory_key = True
                        # if I found at least 1 mandatory rule, break
                        break
                # Check if actual key break actual amount of keys allowed on a single x500 name

                if rules_details[x500_key_check.group(1)]["operator"] == "=":
                    if x500_key_count[x500_key_check.group(1)] > rules_details[x500_key_check.group(1)]["occurrences"]:
                        # print("Warning Found a merged x500 name:\n %s\nattempting to split it" % uml_object)
                        force_x500_split = True
                    else:
                        force_x500_split = False

                # if:
                # There no more keys on allowed_keys_ist  - or -
                # Given key is not mandatory (it may be do not appear on expected keys) - or -
                # we are checking last key from x500 name - or -
                # any field key is seeing more times that allowed by the rule
                # if x500_key_count[x500_key_check.group(1)] > rules
                #

                if force_x500_split:
                    # Remove last "," from this participant build:
                    x500_build = x500_build.strip(", ")
                    # Store this name
                    if x500_build not in participant_build:
                        print(f"  X500 name: {x500_build} [Re-Build from split]")
                        participant_build.append(x500_build)
                    x500_build = "%s, " % x500_key_check.group(0)
                    # Reset rule key count for all to start from this x500 name (previous name was already stored)
                    for each_rd in x500_key_count:
                        x500_key_count[each_rd] = 0

                    # Update to 1 only actual processed key
                    x500_key_count[x500_key_check.group(1)] = 1
                    # Reset required fields again for the next name
                    allowed_keys_list = list(rules.keys())
                    # Remove recently added field at x500_build from allowed_keys_list
                    allowed_keys_list.remove(x500_key_check.group(1))

                if len(x500_keys) - x500_key_counter == 0:
                    # X500 name seems to be complete; store it
                    x500_build += "%s, " % x500_key_check.group(0)
                    # Remove last "," from this participant build:
                    x500_build = x500_build.strip(", ")
                    # Store this name
                    if x500_build not in participant_build:
                        print(f" * X500 name: {x500_build}")
                        participant_build.append(x500_build)

                    # Remove current keyword from expected list
                    if x500_key_check.group(1) in allowed_keys_list:
                        allowed_keys_list.remove(x500_key_check.group(1))
                    # if actual keyword is "S" or "ST remove it
                    if x500_key_check.group(1) == "ST":
                        allowed_keys_list.remove("S")
                    if x500_key_check.group(1) == "S":
                        allowed_keys_list.remove("ST")
                    break

                if not allowed_keys_list or not mandatory_key and not force_x500_split:
                    # X500 name seems to be complete; store it
                    # Remove last "," from this participant build:
                    x500_build = x500_build.strip(", ")
                    # Reset required fields again for the next name
                    allowed_keys_list = list(rules.keys())
                    # Store this name
                    if x500_build not in participant_build:
                        print(f"  X500 name: {x500_build}")
                        participant_build.append(x500_build)
                    # Clear build variable for next name
                    x500_build = ""
                else:
                    try:

                        if x500_key_check.group(0) not in x500_build:
                            # If x500 key is not in the actual x500 name add it...
                            x500_build += "%s, " % x500_key_check.group(0)
                            # x500_key_check += x500_key_check.group(0) + ","
                            # participant_build[participant_build_counter] += "%s, " % x500_key_check.group(0)

                            # Remove current keyword from expected list
                            if x500_key_check.group(1) in allowed_keys_list:
                                allowed_keys_list.remove(x500_key_check.group(1))
                            # if actual keyword is "S" or "ST remove it
                            if x500_key_check.group(1) == "ST":
                                allowed_keys_list.remove("S")
                            if x500_key_check.group(1) == "S":
                                allowed_keys_list.remove("ST")

                    except BaseException as be:
                        print(be)

        # Check if any mandatory field is missing
        if allowed_keys_list:
            for each_rule_key in allowed_keys_list:
                # check if this field is mandatory:
                if ":M" in rules[each_rule_key]:
                    print("WARNING: this participant name '%s' is missing a mandatory key: %s" % (uml_object,
                                                                                                  each_rule_key))

        return participant_build

    @staticmethod
    def get_corda_object_definition(macro_variable):
        """
        This method will return a list of ways to identify a macro_variable
        :param macro_variable: macro variable required
        :return: it will return a list of "EXPECT" which will teach how to identify given macro_variable in line context
        if not macro_variable is found at the expect list, will return None.
        """

        base_check = Configs.get_config(section="CORDA_OBJECTS")
        variable_to_search = "__%s__" % (macro_variable,)
        for each_corda_object in base_check:
            for each_expect in base_check[each_corda_object]['EXPECT']:
                if variable_to_search in base_check[each_corda_object][each_expect]:
                    return base_check[each_corda_object]['EXPECT']

        return None

    @staticmethod
    def get_all_objects(export=True):
        """
        Returns all objects stored
        :return: a dictionary
        """
        data = {}
        if not export:
            return CordaObject.list

        for each_type in CordaObject.list:
            for each_item in CordaObject.list[each_type]:
                if each_type not in data:
                    data[each_type] = {}

                data[each_type][each_item] = CordaObject.list[each_type][each_item].data

        return data

class FileManagement:
    """
    A class to help to read big files...
    """
    def __init__(self):
        self.filename = None
        self.block_size = None


    def divide_file(self):
        """
        Divide file in defined block_sizes
        :return:
        """
        with open(self.filename, "r") as fh_file:
            while True:
                start_pos = fh_file.tell()
                lines = fh_file.readlines(self.filename)
                if not lines:
                    break
                yield start_pos, fh_file.tell() - start_pos

    def process_block(args):
        filename, start, size = args
        results = []
        with open(filename, "r") as file:
            file.seek(start)
            lines = file.read(size).splitlines()
            for line in lines:
                result = CordaObject.analyse(line)  # Tu lógica aquí
                if result:
                    results.append(result)
        return results

    def parallel_processing(self,filename, block_size):
        tasks = [(filename, start, size) for start, size in self.divide_file(filename, block_size)]
        with Pool() as pool:
            results = pool.map(self.process_block, tasks)
        return results


class UMLObject:
    """
    Container for all uml objects
    """

    def __init__(self):
        """

        """
        self.type = ""
        self.name = ""
        self.definition = None


class Party:
    """
    A class to represent parties on a log
    """
    party_list = []

    def __init__(self):
        self.name = None
        self.role = ''
        self.corda_role = ''
        self.default_endpoint = None

    def set_name(self, name):
        """
        Set party name
        :param name: x500 party name
        :return: void
        """
        self.name = name

    def set_role(self, role):
        """
        Set party role
        :param role: role
        :return: void
        """

        self.role = role

    def set_corda_role(self, corda_role):
        """
        Set party corda role
        :param corda_role: set actual corda role like participant, Notary, etc
        :return: void
        """

        self.corda_role = corda_role

    def get_corda_role(self):
        """
        Return actual corda role assigned to this party
        :return: String
        """

        return self.corda_role

    def add_endpoint(self, endpoints, endpoint_type="source"):
        """
        Add endpoints for default destination / source
        :param endpoint_type: Destination / source
        :return:
        """

        if not self.default_endpoint:
            self.default_endpoint = {}

        self.default_endpoint[endpoint_type] = endpoints

    def remove_endpoint(self, endpoint, endpoint_type):
        """
        Remove an endpoint from this object

        :param endpoint: end point to remove
        :param endpoint_type: endpoint type, destination or source
        :return:
        """

        if endpoint_type in self.default_endpoint:
            dict.pop(self.default_endpoint[endpoint_type][endpoint], None)

    def add(self):
        """
        Add a new party
        :return: False if Party was already added, True if it is first time
        """
        self.name = self.name.replace('"','')
        # If party name was already registered do not add it.

        # # Verify if this UML object definition has a rule to accomplish
        # rules = Configs.get_config(uml_role, "RULES", "UML_DEFINITIONS")
        # if rules:
        #     uml_list = CordaObject.uml_apply_rules(incoming_uml_object, rules)
        # else:
        #     uml_list = [incoming_uml_object]

        for pty in Party.party_list:
            if self.name == pty.name:
                return False

        Party.party_list.append(self)
        return True

    @staticmethod
    def get_party(party_name):
        """
        Return Party object that match x500 name
        :param party_name: x500 name of party to look for
        :return: a party object
        """
        for each_party in Party.party_list:
            if each_party.name == party_name:
                return each_party

        return None


class OrderedDictX(OrderedDict):
    def prepend(self, other):
        ins = []
        if hasattr(other, 'viewitems'):
            other = other.viewitems()
        for key, val in other.items():
            if key in self:
                self[key] = val
            else:
                ins.append((key, val))
        if ins:
            items = OrderedDict(self.items())
            self.clear()
            self.update(ins)
            self.update(items)

def generate_internal_access(variable_dict, variable_to_get):
    """
    This method will try to generate internal access to given variable
    :type variable_dict: Actual dictionary object to access
    :param variable_to_get: dot representation to reach such variable
    :return: access representation to get into that variable,value of variable asked for
    """

    if '.' in variable_to_get:
        variables = variable_to_get.split('.')
        fvariable = ""
        for each_var in variables:
            fvariable = fvariable + f"['{each_var}']"

        try:
            fvariable_value = eval(f"variable_dict{fvariable}")
            # final_output = final_output + f"{variables[len(variables)-1]}: {final_variable} "
            return fvariable, fvariable_value
        except KeyError as be:

            # print(f"Unable to access variable_dict{fvariable} from this line: {variable_dict}")
            return None, None

def join_all_regex(section, list_to_collect=None):
    """
    A method to join all regex to search for...
    :param section: This is section at the JSON you want to collect regex from
    :param corda_objects:
    :param list_to_collect:
    :return:
    """
    all_regex = []
    all_regex_type = []


    objects_to_check = Configs.get_config(section=section)

    if not objects_to_check:
        return None, None

    for each_type in objects_to_check.keys():
        if list_to_collect and each_type not in list_to_collect:
            continue
        if "EXPECT" in objects_to_check[each_type]:
            regex_list = objects_to_check[each_type]["EXPECT"]
            for each_rgx in regex_list:
                all_regex.append(build_regex(each_rgx, nogroup_name=True))
                all_regex_type.append(each_type)

    return all_regex, all_regex_type

def regex_to_use(regex_list, message_line):
    """
    Given a regex_list, which will contain all regex; and the line to find out which regex can be applied into it
    :param regex_list: a regex list with all possible regex to try
    :param message_line: the actual message that need to be parsed
    :return: regex index to be used or None if there're no possible regex matches.
    """
    #
    # In order to join all regex into one, I need to remove any group names as it can make conflicts
    no_group_names = clear_groupnames(regex_list)
    #
    # I need to get actual group references for the concatenated regex. this will help to
    # identify correct regex to use
    concatenated_idx_groups = set_concatenated_index_groups(no_group_names)
    # Join all regex into one

    # all_expects = ''
    # for each_item in no_group_names:
    #     all_expects += '|' + each_item
    #
    # tall_expects = all_expects[1:]
    # all_expects = tall_expects

    all_expects = '|'.join(no_group_names)

    group_idx_match = None

    try:
        # Check if given line has a valid regex to be applied
        expression = RegexLib.use(all_expects)
        check_match = expression.findall(message_line)
        # check_match = re.findall(all_expects, message_line)
        #
        # Using result from findall; search which group was valid
        #
        if not check_match:
            return None
        match_expression_index = next(a for a, b in enumerate(check_match[0]) if b)
        # I've found a good group save it for reference
        group_idx_match = match_expression_index
    except BaseException as be:
        # No regex has a match with given line
        return None

    # If we don't match any regex for this line, then doesn't make sense to continue with it... return None
    if group_idx_match is None:
        return None

    expect_to_use = concatenated_idx_groups[group_idx_match]

    # A matching regex was found, return actual index that will work:

    return expect_to_use


def set_concatenated_index_groups(regex_list):
    """
    This method will create an array with list of regex indexes, this will help to locate the proper regex,
    when they are concatenated

    :param regex_list: List of regex expressions to scan
    :return: list of reference indexes for groups
    """
    group_pos = 0
    index_grp = []
    # group_data = {}

    for index, each_string in enumerate(regex_list, start=0):
        try:
            rexp = re.compile(each_string)
            no_groups = rexp.groups

        except re.error as ree:
            print(f"ERROR: Detected malformed pattern: {each_string} ")
            print("from processing list: %s" % regex_list)

        # group_data[index] = {
        #     "groups": [grp+group_pos for grp in range(1, no_groups + 1)]
        # }

        for grp_no in range(group_pos, group_pos + no_groups):
            index_grp.append(index)

        group_pos += no_groups

    return index_grp


def clear_groupnames(regex_list):
    """
    Clear given list of regex of any group name, returning same regex expression without any groupname
    This is useful to combine all the regex into a single expression to match a line, and check if within expression
    we have a possible candidate for analysis
    :param regex_list: of regex expression with group names
    :return: a list of regex expressions without any group name
    """

    return CordaObject.get_clear_group_list(regex_list)


def load_corda_object_definition(config_file="./conf/logwatcher_rules.json"):
    """
    Load TraceId definition definition
    :return:
    """
    with open(config_file) as fflowstatus:
        config_all = json.load(fflowstatus)
        config = config_all["UML_SETUP"]

        Configs.set_config(config_value=config["CORDA_OBJECTS"], section="CORDA_OBJECTS")
        Configs.set_config(config_value=config["CORDA_OBJECT_DEFINITIONS"], section="CORDA_OBJECT_DEFINITIONS")
        Configs.set_config(config_value=config["UML_DEFINITIONS"], section="UML_DEFINITIONS")
        Configs.set_config(config_value=config["UML_ENTITY"], section="UML_ENTITY")
        Configs.set_config(config_value=config["UML_CONFIG"], section="UML_CONFIG")

        print("Object definition loaded")


def clear_participant_str(source):
    """
    Will remove undesired strings from party name
    :param source: line that need to be cleaned
    :return: a clean party name
    """

    if source:
        if 'participant' in source:
            source = source.replace('participant', '').replace('"', '').strip()

    return source


def build_uml_script(corda_object=None):
    """
    Will build a UML script
    :param corda_object: corda Object
    :return:
    """

    start = []
    body = []
    end = []
    full_script = []
    start.append("@startuml")
    start.append("hide unlinked")

    if not corda_object:
        print("Warning no viable references were collected...")
        return None

    if Configs.get_config(section="UML_CONFIG", param="title"):
        start.extend(Configs.get_config(section="UML_CONFIG", param="title",sub_param="CONTENT"))
        title = '"Tracer for %s: %s"' % (corda_object.type, corda_object.data["id_ref"])
        start.append("title %s" % (title,))

    if corda_object:
        for reference in corda_object.references:
            if "uml" not in corda_object.references[reference]:
                continue
            for each_uml_step in corda_object.references[reference]["uml"]:
                action = list(each_uml_step.keys())[0]
                if action == "note over":
                    pass
                if action == "->" or action == "<-":
                    # First get each end...
                    # Getting source...
                    # Check first, if we can define a default source -- ie, source *MUST* be log_owner; for example
                    # if line refer to saving into vault; vault will belong to log_owner in this case...
                    #
                    if not setup_default_endpoint(corda_object.references[reference]["message"], "default_source"):
                        # get_uml_values(each_uml_step[action], "uml_object:source"):
                        source = define_field_limits(get_uml_values(each_uml_step[action], "uml_object:source"),
                                                     "uml_object")
                        if not source:
                            source = define_field_limits(get_uml_values(each_uml_step[action], "participant:source"),
                                                         "uml_object")
                        # source = get_uml_values(each_uml_step[action], "uml_object:source")
                    else:
                        source = define_field_limits(
                            setup_default_endpoint(corda_object.references[reference]["message"], "default_source"),
                            "uml_object"
                        )
                        # source = setup_default_endpoint(corda_object.references[reference]["message"])
                        # source = CordaObject.default_uml_endpoints["local_source"]
                    # Now get destination...
                    # first check if can be solved by default destination... (this will depend of line message)
                    #
                    if not setup_default_endpoint(corda_object.references[reference]["message"], "default_destination"):
                        # get_uml_values(each_uml_step[action], "uml_object:destination"):
                        destination = define_field_limits(get_uml_values(each_uml_step[action],
                                                                         "uml_object:destination"),
                                                          "uml_object")
                        if not destination:
                            # TODO: Hay que chequear bien el uso de "uml_object" aqui
                            destination = define_field_limits(
                                get_uml_values(each_uml_step[action], "participant:destination"), "uml_object")
                        # destination = get_uml_values(each_uml_step[action], "uml_object:destination")
                    else:
                        destination = define_field_limits(
                            setup_default_endpoint(corda_object.references[reference]["message"],
                                                   "default_destination"),"uml_object")
                        # destination = setup_default_endpoint(corda_object.references[reference]["message"])
                        # destination = CordaObject.default_uml_endpoints["local_destination"]

                    if source:
                        validate_identities(source)
                    if destination:
                        validate_identities(destination)

                    # Check if there's any source/destination that require reporting...
                    if not source:
                        print("="*100)
                        print("Warning: I was not able to determine source for given UML step:")
                        print("Action       : %s" % action)
                        print("Line         : %s" % reference)
                        print("Destination  : %s" % destination)
                        print("Original Line: %s" % corda_object.references[reference]["message"])
                        print("="*100)
                    if not destination:
                        print("="*100)
                        print("Warning: I was not able to determine destination for given UML step:")
                        print("Action       : %s" % action)
                        print("Line         : %s" % reference)
                        print("Source       : %s" % source)
                        print("Original Line: %s" % corda_object.references[reference]["message"])
                        print("="*100)

                    if get_uml_values(each_uml_step[action], "note over:message"):
                        tx_id = ""
                        flow_id = ""
                        if get_uml_values(each_uml_step[action], "annotation:tx_id"):
                            tx_id = "\\n<b>Transaction:</b>\\n%s" % get_uml_values(each_uml_step[action],
                                                                                   "annotation:tx_id")
                        if get_uml_values(each_uml_step[action], "annotation:flow_id"):
                            flow_id = "\\n<b>Flow:</b>\\n%s" % get_uml_values(each_uml_step[action],
                                                                              "annotation:flow_id")

                        note = ": <b>Time stamp:</b>\\n%s\\n<b>Message:</b>\\n%s%s%s" % \
                               (corda_object.references[reference]["timestamp"],
                                define_field_limits(get_uml_values(each_uml_step[action], "note over:message"),
                                                    action), flow_id, tx_id)
                    else:
                        note = ""

                    if action == "->":
                        source = clear_participant_str(source)
                        destination = clear_participant_str(destination)
                        body.append('"%s" %s "%s"%s' % (source, action, destination, note))
                    else:
                        source = clear_participant_str(source)
                        destination = clear_participant_str(destination)
                        body.append('"%s" %s "%s"%s' % (destination, action, source, note))

                if action == "note left":
                    if get_uml_values(each_uml_step[action], "note over:message"):
                        tx_id = ""
                        flow_id = ""
                        if get_uml_values(each_uml_step[action], "annotation:tx_id"):
                            tx_id = "\n<b>Transaction:</b>\n%s" % get_uml_values(each_uml_step[action],
                                                                                 "annotation:tx_id")
                        if get_uml_values(each_uml_step[action], "annotation:flow_id"):
                            flow_id = "\n<b>Flow:</b>\n%s" % get_uml_values(each_uml_step[action],
                                                                            "annotation:flow_id")

                        note = "<b>Time stamp:</b>\n%s\n<b>Message:</b>\n%s%s%s" % \
                               (define_field_limits(corda_object.references[reference]["timestamp"], action),
                                define_field_limits("%s" % (get_uml_values(each_uml_step[action],
                                                                           "note over:message"),),
                                                    action), flow_id, tx_id)

                        if get_uml_values(each_uml_step[action], "uml_object:source"):
                            note += "\n<b>Source</b>:\n"
                            note += " %s" % define_field_limits(get_uml_values(each_uml_step[action],
                                                                               "uml_object:source"), action)

                        note = "note left\n%s\nend note" % (note,)
                        body.append(note)

                if action == "note right":
                    if get_uml_values(each_uml_step[action], "note over:message"):
                        tx_id = ""
                        flow_id = ""
                        if get_uml_values(each_uml_step[action], "annotation:tx_id"):
                            tx_id = "\n<b>Transaction:</b>\n%s" % get_uml_values(each_uml_step[action],
                                                                                 "annotation:tx_id")
                        if get_uml_values(each_uml_step[action], "annotation:flow_id"):
                            flow_id = "\n<b>Flow:</b>\n%s" % get_uml_values(each_uml_step[action],
                                                                            "annotation:flow_id")

                        note = "<b>Time stamp:</b>\n%s\n<b>Message:</b>\n%s%s%s" % \
                               (define_field_limits(corda_object.references[reference]["timestamp"], action),
                                define_field_limits("%s" % (get_uml_values(each_uml_step[action],
                                                                           "note over:message"),),
                                                    action), flow_id, tx_id)

                        if get_uml_values(each_uml_step[action], "uml_object:source"):
                            note += "\n<b>Source</b>:\n"
                            note += " %s" % define_field_limits(get_uml_values(each_uml_step[action],
                                                                               "uml_object:source"), action)

                        note = "note right\n%s\nend note" % (note,)
                        body.append(note)

    # if this setting is active, it will only show actual participants that are being used.
    #
    active_participants = Configs.get_config(section="UML_ENTITY", param="SETTINGS",
                                             sub_param="SHOW_ONLY_ACTIVE_PARTICIPANTS")

    if active_participants:
        for each_element in CordaObject.uml_active_participants:
            start.append(each_element)
        CordaObject.uml_active_participants = []
    else:
        for participants in CordaObject.uml_init:
            start.append(participants)

    end.append("@enduml")
    if body:
        # Check body for overlapped notes...
        body = check_overlapped_notes(body)
        full_script.extend(start)
        full_script.extend(body)
        full_script.extend(end)

    return full_script


def check_overlapped_notes(body):
    """
    This method will check if given text has overlapped notes, and then it will join them to be a single note
    :param body: array list that contains the text to check
    :return: corrected body without overlapped notes
    """
    new_body = list(body)
    index_counter = 0
    while index_counter < len(body) - 1:
        for each_note_type in ["note left", "note right", "note over"]:
            first_line = re.search(each_note_type, body[index_counter])
            second_line = re.search(each_note_type, body[index_counter + 1])
            if first_line and second_line:
                new_body[index_counter] = new_body[index_counter].replace("\nend note", "\n---")
                new_body[index_counter + 1] = new_body[index_counter + 1].replace("%s\n" % (each_note_type,), "")
        index_counter += 1

    return new_body


def define_field_limits(value, uml_definition):
    """
    This method will apply text limits, and wrap its contents depending of length defined on configuration
    :param uml_definition: actual UML definition (uml_object, '->', '<-', etc)
    :param value: Text that need to be checked/limited
    :return: string with the actual value wrapped text using "\n" where is required...
    """

    max_len = {}
    # Setup an alias for max_len for easy handling
    for each_item in Configs.get_config(section="UML_DEFINITIONS"):
        if "MAX_LEN" in Configs.get_config(section="UML_DEFINITIONS", param=each_item):
            max_len[each_item] = Configs.get_config(section="UML_DEFINITIONS",
                                                    param=each_item)["MAX_LEN"]
    if uml_definition in max_len:
        if uml_definition == "note left":
            response = textwrap.fill("%s" % (value,), max_len[uml_definition])
        else:
            response = textwrap.fill("%s" % (value,), max_len[uml_definition]).replace("\n", "\\n")
    else:
        response = value

    return response


def setup_default_endpoint(message, check_end_point=None):
    """
    This method will determine who is the endpoint to given message; if message is lacking for a source it will try to
    infer who is the source of such message, if message is lacking from destination, will also try to infer who is the
    destination and will return these values
    :param message: actual message to scan
    :return: a source or destination depending on default rules defined. will return null otherwise...
    """

    #TODO: hay un problema en este metodo para determinar el default origen o default destino, el problema
    # se presenta cuando un participante es por ejemplo el notario y al mismo tiempo es el dueno del logfile
    # en este sentido el programa le asignara los "endpoints" correspondientes a un "log_owner" y con esto
    # dejara fuera la identidicacion del notario como destino, esto provoca que el destino sea "desconocido"
    # para el programa y falle.
    # Asignar los destinos adicionales para el notario cuando sea log_owner, creo que esto solucionara el problema

    default_end_point = None
    if not check_end_point:
        for each_object in CordaObject.default_uml_endpoints:
            for each_usage in CordaObject.default_uml_endpoints[each_object]:
                if "EXPECT" in CordaObject.default_uml_endpoints[each_object][each_usage]:
                    for each_expect in CordaObject.default_uml_endpoints[each_object][each_usage]['EXPECT']:
                        check_usage = re.findall(each_expect, message)
                        if check_usage:
                            default_end_point = each_object
                            break
            #     if default_end_point:
            #         break
            # if default_end_point:
            #     break
    else:
        for each_object in CordaObject.default_uml_endpoints:
            if not default_end_point and check_end_point in CordaObject.default_uml_endpoints[each_object]:
                if "EXPECT" in CordaObject.default_uml_endpoints[each_object][check_end_point]:
                    for each_expect in CordaObject.default_uml_endpoints[each_object][check_end_point]['EXPECT']:
                        check_usage = re.findall(each_expect, message)
                        if check_usage:
                            default_end_point = each_object
                            break
            # if default_end_point:
            #     break
    pass
    return default_end_point


def validate_identities(identity):
    """
    Method to validate which identities are present on the process, will invalidate any other uml_object
    that has no relevance (no process to report)
    :return:
    """
    # delete unwanted characters...
    unwanted_char = ['\\n']
    for each_unwanted_char in unwanted_char:
        if each_unwanted_char in identity:
            identity = identity.replace(each_unwanted_char, ' ')

    for each_element in CordaObject.uml_init:
        if identity in each_element:
            if each_element not in CordaObject.uml_active_participants:
                CordaObject.uml_active_participants.append(each_element)


def get_uml_values(each_uml_step, what_to_look_for):
    """
    This method will return content of given UML tag; on the corda object which is using a reversed dictionary where
    keys are the values and the values are the keys...
    :param each_uml_step: Actual step that need to be checked
    :param what_to_look_for:
    :return:
    """
    if what_to_look_for in each_uml_step.values():
        value = list(each_uml_step.keys())[list(each_uml_step.values()).index(what_to_look_for)]
    else:
        value = None

    return value


def trace_id():
    """
    Trace a particular corda object over all logs
    :return:
    """
    from ahocorapy.keywordtree import KeywordTree
    global log_file, logfile_format

    # Create keyword search tree
    kwtree = KeywordTree(case_insensitive=True)
    for id_ref in CordaObject.id_ref:
        kwtree.add(id_ref)
    kwtree.finalize()

    # if not args.transaction_details:
    #     print('\n%s' % flow,)
    start = False
    end = False
    print("Phase *2* Analysing... searching references for transactions and flows")

    if log_file:
        # If a file is being specified...
        with open(log_file, 'r') as ftrack_log:
            line_count = 0
            for each_line in ftrack_log:
                line_count += 1
                CordaObject.check_default_uml_references(each_line)
                logfile_fields = get_fields_from_log(each_line, logfile_format)

                if not logfile_fields:
                    # print("UNABLE TO PARSE:\n%s" % each_line)
                    continue

                # Search on the tree...
                results = kwtree.search_all(logfile_fields["message"])
                if results:
                    for each_result in results:
                        ref_found = each_result[0]
                        corda_object = CordaObject.get_object(ref_found)
                        if corda_object:
                            corda_object.add_reference(line_count, logfile_fields)
    else:
        # Search on DB
        pass

    lcount = 0

    if CordaObject.uml_init:
        if not CordaObject.get_log_owner():
            counter = 0

            print("\n-----------------------------------------------------------------------------------")
            print("I was not able to determine who is the owner of given logs,"
                  " please can you choose it from below...\n")
            participant_list = []
            counter = 0
            for each_item in CordaObject.uml_init:
                # if "uml_object" in each_item:
                # counter += 1
                #     party = each_item.replace("uml_object", "").replace('"', '').strip()
                if "participant" in each_item:
                    counter += 1
                    party = clear_participant_str(each_item)
                    print("[%s] %s" % (counter, party))
                    participant_list.append(party)
            counter += 1
            print(f"[{counter}] - Need to define new party for this file")
            selection = input("Please let me know which one is the producer of this log file [1-%s]:" % (counter,))
            if int(selection) == counter:
                party_roles = [
                    "Notary",
                    "Party"
                ]
                print("Please specify a valid x500 name for this party:")
                party_name = input("> ")
                print("Please specify role for this party:")
                for idx, each_role in enumerate(party_roles):
                    print(f"{idx} - {each_role}")
                party_irole = -1
                while int(party_irole) < 0 or int(party_irole) > len(party_roles):
                    party_irole = input("> ")

                party_role = party_roles[int(party_irole)]

                CordaObject.add_uml_object(party_name, "participant")
                participant_list.append(party_name)
                add_participant(party_name, party_role)
                party_object = Party.get_party(party_name)
                if party_object:
                    party_object.set_corda_role(party_role)

            CordaObject.set_participant_role(participant_list[int(selection) - 1], role="log_owner", attach_usages=True)

        print("Party elements found:")

        for each_item in CordaObject.uml_init:
            # if "uml_object" in each_item:
            if "participant" in each_item:
                # party = each_item.replace("uml_object", "").replace('"', '').strip()
                party = clear_participant_str(each_item)
                if CordaObject.get_log_owner() and party == CordaObject.get_log_owner():
                    note = "[ LOG OWNER ]"
                else:
                    if party in CordaObject.default_uml_endpoints and \
                            "ROLE" in CordaObject.default_uml_endpoints[party]:
                        note = "[ %s ]" % CordaObject.default_uml_endpoints[party]["ROLE"]
                    else:
                        note = ""

                print(" * %s %s" % (party, note))
    pause = input("\n\n[PRESS ENTER TO CONTINUE]...")
    for each_type in CordaObject.list:
        for each_object in CordaObject.list[each_type]:
            corda_o = CordaObject.list[each_type][each_object]
            title = "Tracer for %s: %s" % (corda_o.type, corda_o.data["id_ref"])
            operations = Table(table_name=title)
            operations.add_header("Time Stamp", 30, "^", "^")
            operations.add_header("Log Line #", 10, "^", "^")
            #
            if CordaObject.additional_table_fields:
                for each_field in CordaObject.additional_table_fields:
                    operations.add_header(each_field, 70, "^", "<")
            else:
                # Add mere line that held reference...
                operations.add_header("Reference",60,"^","<")

            operations.add_header("UML", 10, "^", "^")
            for each_reference in corda_o.references:
                corda_or = corda_o.references[each_reference]
                operations.add_cell(corda_or["timestamp"])
                operations.add_cell("%s" % (each_reference,))

                if CordaObject.additional_table_fields:
                    for each_field in CordaObject.additional_table_fields:
                        if each_field in corda_or:
                            operations.add_cell(corda_or[each_field])
                        else:
                            operations.add_cell("[*NO MATCH RULE*]: %s" % corda_or["message"])
                else:
                    operations.add_cell(corda_or['message'])

                if "uml" in corda_or:
                    operations.add_cell(list(corda_or["uml"][0].keys())[0])
                else:
                    operations.add_cell("*NO DATA*")
                lcount += 1

            operations.print_table_ascii()
            # Check if we have a default
            script = build_uml_script(corda_o)
            draw_results("%s-%s" % (corda_o.type, corda_o.data["id_ref"]), script, log_file)
            print("===============================")


def list_references():
    """
    Method exposing list of all references found as a list
    :return: string list
    """
    return CordaObject.id_ref


def get_references_beta(line_content, line):
    """
    Collect reference id's that later will help to track them through entire logs
    :param line_content: Line message content
    :param line: line number
    :return:
    """
    global logfile_format, kwtree
    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    # Complete list of corda object regex definition
    all_regex = []
    # A helper list to give the type and avoid to do a second search on the config to gather object type
    all_regex_type = []
    if not corda_objects:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        # corda_objects = Configs.get_config(section="CORDA_OBJECTS")
        #
        # for each_type in corda_objects:
        #     if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
        #         regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
        #         for each_rgx in regex_list:
        #             all_regex.append(build_regex(each_rgx, nogroup_name=True))
        #             all_regex_type.append(each_type)
        #
        # # Prepare full regex for quick detection
        # corda_object_detection = "|".join(all_regex)

        corda_objects = Configs.get_config(section="CORDA_OBJECTS")

        for each_type in corda_objects:
            if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                for each_rgx in regex_list:
                    all_regex.append(each_rgx)
                    all_regex_type.append(each_type)
        #
        # # Prepare full regex for quick detection
        # corda_object_detection = "|".join(all_regex)

    if not logfile_format:
        for each_version in Configs.get_config(section="VERSION"):
            try_version = Configs.get_config(section="VERSION", param=each_version)
            check_version = re.search(try_version["EXPECT"], line_content)
            if check_version:
                logfile_format = each_version
                print("Log file format recognized as: %s" % logfile_format)
                break

    cordaobject_id_match = regex_to_use(all_regex, line_content)
    # cordaobject_id_match = re.finditer(corda_object_detection, line_content)

    if cordaobject_id_match is None:
        return
    else:
        # Make sure that I replace any pseudo variable with proper regex to look for:
        regex = build_regex(all_regex[cordaobject_id_match])
        # Now I got index for the regex to use, I just need to apply it:
        match = re.search(regex, line_content)
        # Get actual type for this object
        match_type = all_regex_type[cordaobject_id_match]

        # Check if this reference has visited any entity that need to be registered
        for groupNum, each_group in enumerate(match.groups(), start=1):
            check_reference_reports(each_group, all_regex_type[cordaobject_id_match], line_content, line)

            if each_group not in CordaObject.id_ref:
                #
                # Also create this object to be identified later:
                # first extract line features (timestamp, severity, etc)
                log_line_fields = get_fields_from_log(line_content, logfile_format)
                # Create object:
                co = CordaObject()

                # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                #  ignorar estas referencias...
                if log_line_fields:
                    co.add_data("id_ref", each_group)
                    co.add_data("Original line", line_content)
                    co.add_data("error_level", log_line_fields["error_level"])
                    co.add_data("timestamp", log_line_fields["timestamp"])
                    co.add_data("type", match_type)
                    co.set_type(match_type)
                    co.add_object()


def get_references(line_content, line):
    """
    Collect reference id's that later will help to track them through entire logs
    :param line_content: Line message content
    :param line: line number
    :return:
    """
    global logfile_format, kwtree
    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    # Complete list of corda object regex definition
    all_regex = []
    # A helper list to give the type and avoid to do a second search on the config to gather object type
    all_regex_type = []
    if not corda_objects:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        corda_objects = Configs.get_config(section="CORDA_OBJECTS")
        if CordaObject.get_cordaobject_regex_definition():
            # Use stored list if they exist already
            all_regex = CordaObject.get_cordaobject_regex_definition()
            all_regex_type = CordaObject.get_cordaobject_types_definition()
        else:
            for each_type in corda_objects:
                if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                    regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                    for each_rgx in regex_list:
                        all_regex.append(build_regex(each_rgx, nogroup_name=True))
                        all_regex_type.append(each_type)

                    CordaObject.set_cordaobject_regex_definition(all_regex)
                    CordaObject.set_cordaobject_types_definition(all_regex_type)

        # Prepare full regex for quick detection
        corda_object_detection = "|".join(all_regex)

    if not logfile_format:
        for each_version in Configs.get_config(section="VERSION"):
            try_version = Configs.get_config(section="VERSION", param=each_version)
            check_version = re.search(try_version["EXPECT"], line_content)
            if check_version:
                logfile_format = each_version
                print("Log file format recognized as: %s" % logfile_format)
                break

    # cordaobject_id_match = re.finditer(corda_object_detection, line_content)

    rcorda_object_detection = RegexLib.use(corda_object_detection)
    cordaobject_id_match = rcorda_object_detection.finditer(line_content)

    if cordaobject_id_match:
        group_count = 0
        for matchNum, match in enumerate(cordaobject_id_match, start=1):

            valid_idx = [idx-1 for idx in range(1, len(match.groups())) if match.group(idx)]
            if valid_idx:
                pass
            for groupNum in range(0, len(match.groups())):
                groupNum = groupNum + 1
                each_group = match.group(groupNum)
                if each_group:
                    # Check if this reference has visited any entity that need to be registered
                    check_reference_reports(each_group, all_regex_type[groupNum-1], line_content, line)
                if each_group and each_group not in CordaObject.id_ref:

                    #
                    # Also create this object to be identified later:
                    # first extract line features (timestamp, severity, etc)
                    log_line_fields = get_fields_from_log(line_content, logfile_format)
                    # Create object:
                    co = CordaObject()

                    # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                    #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                    #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                    #  ignorar estas referencias...
                    if log_line_fields:
                        co.add_data("id_ref", each_group)
                        co.add_data("Original line", line_content)
                        co.add_data("error_level", log_line_fields["error_level"])
                        co.add_data("timestamp", log_line_fields["timestamp"])
                        co.add_data("type", all_regex_type[groupNum-1])
                        co.set_type(all_regex_type[groupNum-1])
                        co.add_object()


def get_references_org(line_content, line):
    """
    Collect reference id's that later will help to track them through entire logs
    :param line_content: Line message content
    :param line: line number
    :return:
    """
    global logfile_format, kwtree
    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    # Complete list of corda object regex definition
    all_regex = []
    # A helper list to give the type and avoid to do a second search on the config to gather object type
    all_regex_type = []
    if not corda_objects:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        corda_objects = Configs.get_config(section="CORDA_OBJECTS")

        for each_type in corda_objects:
            if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                for each_rgx in regex_list:
                    all_regex.append(build_regex(each_rgx, nogroup_name=True))
                    all_regex_type.append(each_type)

        # Prepare full regex for quick detection
        corda_object_detection = "|".join(all_regex)

    if not logfile_format:
        for each_version in Configs.get_config(section="VERSION"):
            try_version = Configs.get_config(section="VERSION", param=each_version)
            check_version = re.search(try_version["EXPECT"], line_content)
            if check_version:
                logfile_format = each_version
                print("Log file format recognized as: %s" % logfile_format)
                break

    cordaobject_id_match = re.finditer(corda_object_detection, line_content)

    if cordaobject_id_match:
        group_count = 0
        for matchNum, match in enumerate(cordaobject_id_match, start=1):
            for groupNum in range(0, len(match.groups())):
                groupNum = groupNum + 1
                each_group = match.group(groupNum)
                if each_group:
                    # Check if this reference has visited any entity that need to be registered
                    check_reference_reports(each_group, all_regex_type[groupNum-1], line_content, line)
                if each_group and each_group not in CordaObject.id_ref:

                    #
                    # Also create this object to be identified later:
                    # first extract line features (timestamp, severity, etc)
                    log_line_fields = get_fields_from_log(line_content, logfile_format)
                    # Create object:
                    co = CordaObject()

                    # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                    #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                    #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                    #  ignorar estas referencias...
                    if log_line_fields:
                        co.add_data("id_ref", each_group)
                        co.add_data("Original line", line_content)
                        co.add_data("error_level", log_line_fields["error_level"])
                        co.add_data("timestamp", log_line_fields["timestamp"])
                        co.add_data("type", all_regex_type[groupNum-1])
                        co.set_type(all_regex_type[groupNum-1])
                        co.add_object()


def identify_a_party(line_content):
    """
    A method that will check given line to verify if a valid party exist.
    :param line_content: line to check
    :return:
    """
    global party_found

    if party_found:
        return

    party_config = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS", sub_param="uml_object")

    if party_config and "EXPECT" in party_config:
        party_regex = "|".join(party_config["EXPECT"])
        party_check = re.search(party_regex, line_content)

        if party_check:
            party_found = True


def create_search_tree(id_ref_list=None):
    """
    This method is creating a search tree to speed up reference key scanning; it will create a search tree with all
    collected references, then this will be used to scan each line to find out if line is relevant for a reference
    :return will return a kwtree object
    """
    global kwtree

    if kwtree:
        return kwtree

    # Create keyword search tree

    if not id_ref_list:
        id_ref_list = CordaObject.id_ref
    # print(id_ref_list)
    tree = KeywordTree(case_insensitive=True)
    for id_ref in id_ref_list:
        tree.add(id_ref)
    tree.finalize()

    return tree


def track(each_line, line_count, ref_id=None):
    """
    Track a particular corda object over all log
    :param ref_id: reference that need to be tracked
    :return:
    """
    global log_file, logfile_format, kwtree

    # Create keyword search tree
    if not kwtree:
        kwtree = create_search_tree()

    # Define actual end-point references; which entities will act as "default" source or destination
    # This will define who will act as default end-point
    CordaObject.check_default_uml_references(each_line)
    logfile_fields = get_fields_from_log(each_line, logfile_format)

    if not logfile_fields:
        # print("UNABLE TO PARSE:\n%s" % each_line)
        return

    # Search on the tree...
    results = kwtree.search_all(logfile_fields["message"])

    if results:
        for each_result in results:
            ref_found = each_result[0]
            corda_object = CordaObject.get_object(ref_found)
            if corda_object:
                corda_object.add_reference(line_count, logfile_fields)


def check_participants(hash_key=None):
    """

    :return:
    """
    if CordaObject.uml_init:
        if not CordaObject.get_log_owner():
            counter = 0
            print("I was not able to determine who is the owner of given logs")
            participant_list = []
            for each_item in CordaObject.uml_init:
                # if "uml_object" in each_item:
                #     counter += 1
                #     party = each_item.replace("uml_object", "").replace('"', '').strip()
                if "participant" in each_item:
                    counter += 1
                    party = clear_participant_str(each_item)
                    print("[%s] %s" % (counter, party))
                    participant_list.append(party)

            save_participants(hash_key)
            #
            # selection = input("Please let me know which one is the owner of this log file [1-%s]:" % (counter,))
            # CordaObject.set_log_owner(participant_list[int(selection) - 1], attach_usages=True)

        if CordaObject.uml_init:
            print("Party elements found:")
        else:
            print("No party entities found on this log")

        for each_item in CordaObject.uml_init:
            # if "uml_object" in each_item:
            #     party = each_item.replace("uml_object", "").replace('"', '').strip()

            if "participant" in each_item:
                party = clear_participant_str(each_item)
                if CordaObject.get_log_owner() and party == CordaObject.get_log_owner():
                    note = "[ LOG OWNER ]"
                else:
                    if party in CordaObject.default_uml_endpoints and \
                            "ROLE" in CordaObject.default_uml_endpoints[party]:
                        note = "[ %s ]" % CordaObject.default_uml_endpoints[party]["ROLE"]
                    else:
                        note = ""
            else:

                party = each_item.replace("participant", "")
                party = party.replace('"', "")
                note = ""

            if 'database' not in each_item:
                print(" * %s %s" % (party, note))

    ### /home/larry/IdeaProjects/support/plugins/trackFlow/sup1290/node-diusp-lweb0004.2020-05-21-1.log
    ### /home/r3support/www/uploads/customers/TradeIX/SUP-1480/20200915171050_pack/
    # trace_logs_receiver_1/2020-09/app-09-15-2020-3.log
    if CordaObject.list:
        print("Summary:")
    for each_type in CordaObject.list:
        print(" * %s %s(S) identified." % (len(CordaObject.list[each_type]), each_type))

    # if not CordaObject.get_log_owner(): # previous version was looking for ---> logfile_format:
    #     print("Sorry I can't find a proper log template to parse this log terminating program")
    #     exit(0)
    #
    # if len(CordaObject.id_ref) > 0:
    #     print('%s file contains %s ids' % (log_file, len(CordaObject.id_ref)))
    #
    # if len(CordaObject.id_ref) > 50 and not args.web_style:
    #     print('**WARNING** this may take long time to complete...')
    #     print('Do you want to track all id\'s in %s file ?' % (log_file,))
    #
    #     response = input('> ')
    #     if response != 'y':
    #         exit(0)

    return CordaObject.get_log_owner()


def check_reference_reports(reference, type, line_content, line_no):
    """
    Check if any reference has been sent to any control entity (that has been flagged on config)
    :return:
    """
    endpoint_entities = Configs.get_config(section="UML_ENTITY", param="OBJECTS")
    regex_match = []
    for each_entity in endpoint_entities:
        if "REGISTER_REFERENCE" in endpoint_entities[each_entity]:
            state = endpoint_entities[each_entity]["REGISTER_REFERENCE"]["STATE"]
            # Check if reference need to be applied to a specific "type" of reference:
            if "APPLY_TO" in endpoint_entities[each_entity]["REGISTER_REFERENCE"]:
                apply_to = endpoint_entities[each_entity]["REGISTER_REFERENCE"]["APPLY_TO"]
            else:
                apply_to = None
            # If this entity was requested to register any reference then will need to take all regex string
            # to check them out
            for each_usage in endpoint_entities[each_entity]['USAGES']:
                regex_match = list(endpoint_entities[each_entity]['USAGES'][each_usage]['EXPECT'])

                check_patterns = r'|'.join(regex_match)
                check_matches = re.search(check_patterns, line_content)

                if check_matches:
                    # Check if registration have a "type"; in the case of FlowHospital I can count how many flows
                    # are in... and how many went out...
                    reference_type = None
                    if "REGISTER" in endpoint_entities[each_entity]["REGISTER_REFERENCE"]:
                        if each_usage in endpoint_entities[each_entity]["REGISTER_REFERENCE"]["REGISTER"]:
                            reference_type = endpoint_entities[each_entity] \
                                ["REGISTER_REFERENCE"]["REGISTER"][each_usage]

                    # if we have a specific type to register, then check it out...
                    if apply_to and apply_to == type:
                        CordaObject.add_register(each_entity, reference,
                                                 reference_type, state, line_no, check_matches.group())

                    # If there's no specific type; just take all references that have this entity
                    if not apply_to:
                        CordaObject.add_register(each_entity, reference,
                                                 reference_type, state, line_no, check_matches.group())


def list_corda_objects(object_type=None):
    """
    Will expose corda list of all objects collected
    :return: Will return list of object found with given type... if type is not present will return a dictionary with
    all objects.
    """

    if object_type:
        if object_type in CordaObject.list:
            return CordaObject.list[object_type]
        else:
            return None

    return CordaObject.list


def get_corda_object_types():
    """
    Will return a list of object types found
    :return:
    """
    return CordaObject.list.keys()


def get_participant_role(participant=None):
    """
    If uml_object is part of default endpoint list, it is possible a role has been assigned to it
    :param participant:
    :return: uml_object role if it has one
    """
    if not participant:
        pass
    if participant in CordaObject.default_uml_endpoints:
        if "ROLE" in CordaObject.default_uml_endpoints[participant]:
            return CordaObject.default_uml_endpoints[participant]["ROLE"]
    else:
        return None


def get_active_roles():
    """
    Will return which roles are being set as "automatics" this will help to define default endpoints
    :return: list of roles
    """
    active_roles = []
    for each_object in Configs.get_config("OBJECTS", section="UML_ENTITY"):
        config_chk = "UML_ENTITY:OBJECTS:%s:ACTIVATE_ROLE" % (each_object,)
        if Configs.get_config_from(config_chk):
            active_roles.append(each_object)

    return active_roles


def get_object_references(object_reference, line_no=None, field=None):
    """
    Will return all objects where this reference was found.

    :param object_reference: this is the reference ID (any given format, program will check what
    kind object is and will return proper one)
    :param line_no: this is the line number to get from references
    :param field: If field is valid from reference storage this will be returned.
    :return: depends on parameters given (list, dictionary, or string)
    """

    cobject = CordaObject.get_object(object_reference)

    # Check if object has references

    if not cobject.references:
        return None

    if cobject.references and not line_no and not field:
        return cobject.references

    if cobject.references and line_no and not field:
        if line_no in cobject.references:
            return cobject.references[line_no]
        else:
            return None

    # if there's no line_no reference, I can't return proper reference, or I got the line_no, but that line is not
    # in the references, then return

    if not line_no or line_no and line_no not in cobject.references:
        return None

    if field:
        if field in cobject.references[line_no]:
            return cobject.references[line_no][field]

    return None


def get_object_uml_notation(object_reference, line_no=None):
    """
    Will return all UML notations associated with the given reference
    :param object_reference:
    :return:
    """

    cobject = CordaObject.get_object(object_reference)

    # Check if object has references
    #
    if not cobject.references:
        return None

    # Check if is asking for a particular reference line:
    if line_no:
        if line_no not in cobject.references:
            return None
        else:
            return get_object_references(object_reference, line_no, "uml")
    # Now check, if this object has an UML notation

    if 'uml' not in cobject.references:
        pass


def get_corda_object(object_reference):
    """
    Will expose a way to obtain an object, if reference to this one exist
    :param object_reference: reference id that represent object identification
    :return: CordaObject class object
    """

    return CordaObject.get_object(object_reference)


def list_participants():
    """
    List actual participants found on logs
    :return: a list of strings (list of participants X500 names/control names)
    """

    for each_participant in CordaObject.uml_participants.keys():
        role = get_participant_role(each_participant)
        if role and not CordaObject.uml_participants[each_participant]:
            CordaObject.uml_participants[each_participant] = role

            if role == "log_owner":
                CordaObject.set_participant_role(each_participant, role)

    return CordaObject.uml_participants


def add_participant(participant, role):
    """
    Add a new uml_object into list, with proper role
    :param participant: uml_object x500 name or control/process name
    :param role: notary, log_owner, etc
    :return:
    """

    CordaObject.uml_participants[participant] = role


def list_entity_report():
    """
    Will return which entities have a report
    :return: a list of Entity names
    """

    return CordaObject.entity_register.keys()


def get_entity_report(entity_name=None, entity_register_type=None, entity_reference=None):
    """
    Get actual report for given entity, this report will contain which references "went through" this an specific
    entity
    :param entity_name: to search for
    :param entity_register_type: kind of register to search for
    :param entity_reference: reference that need to retrieved
    :return:
    """

    if not entity_name and not entity_register_type and not entity_reference:
        # Return whole object if no args
        return CordaObject.entity_register

    if entity_name and not entity_register_type and not entity_reference:
        # if entity name is given and is valid, return its content
        # else return none
        if entity_name in CordaObject.entity_register:
            return CordaObject.entity_register[entity_name]
    else:
        # if entity name is given and entity register is valid and entity_reference is not given
        # then return whole entity_register record; else return None
        if entity_name and entity_register_type and not entity_reference:
            if entity_register_type in CordaObject.entity_register[entity_name]:
                return CordaObject.entity_register[entity_name][entity_register_type]
        else:
            if entity_name and entity_register_type and entity_reference:
                if entity_register_type in CordaObject.entity_register[entity_name]:
                    if entity_reference in CordaObject.entity_register[entity_name][entity_register_type]:
                        return CordaObject.entity_register[entity_name][entity_register_type][entity_reference]

    return None


def set_entity_register(entity_report_register):
    """
    Setup entity register; which will contain stats about entities
    :param entity_report_register:
    :return:
    """

    CordaObject.entity_register=entity_report_register


def results(each_object):
    """

    :return:
    """
    lcount = 0
    each_type = CordaObject.get_type(each_object)
    corda_o = CordaObject.list[each_type][each_object]
    title = "Tracer for %s: %s" % (corda_o.type, corda_o.data["id_ref"])
    operations = Table(table_name=title)
    operations.add_header("Time Stamp", 30, "^", "^")
    operations.add_header("Log Line #", 10, "^", "^")
    for each_field in CordaObject.additional_table_fields:
        operations.add_header(each_field, 70, "^", "<")
    operations.add_header("UML", 10, "^", "^")
    for each_reference in corda_o.references:
        corda_or = corda_o.references[each_reference]
        operations.add_cell(corda_or["timestamp"])
        operations.add_cell("%s" % (each_reference,))

        for each_field in CordaObject.additional_table_fields:
            if each_field in corda_or:
                operations.add_cell(corda_or[each_field])
            else:
                operations.add_cell("[*NO MATCH RULE*]: %s" % corda_or["message"])
        if "uml" in corda_or:
            operations.add_cell(list(corda_or["uml"][0].keys())[0])
        else:
            operations.add_cell("*NO DATA*")
        lcount += 1

    operations.print_table_ascii()
    # Check if we have a default
    script = build_uml_script(corda_o)
    draw_results(script)
    print("===============================")


def get_ref_ids():
    """
    Search for all identifiable ids on a log
    :return:
    """
    global logfile_format

    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    print("Phase *1* Collect ids searching for "+",".join(list(corda_objects.keys())))
    # Complete list of corda object regex definition
    # # A helper list to give the type and avoid to do a second search on the config to gather object type


    # Prepare full regex for quick detection
    all_regex, all_regex_type = join_all_regex('CORDA_OBJECTS')
    all_regex_party, all_regex_type_party = join_all_regex('UML_DEFINITIONS', ['participant'])

    if not all_regex:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        # This will search for "CORDA_OBJECTS" defined (see json file)
        corda_object_detection = "|".join(all_regex)

    corda_party_detection = "|".join(all_regex_party)

    try:
        with open(log_file, 'r') as flog_file:
            for each_line in flog_file:
                if not logfile_format:
                    for each_version in Configs.get_config(section="VERSION"):
                        try_version = Configs.get_config(section="VERSION", param=each_version)
                        check_version = re.search(try_version["EXPECT"], each_line)
                        if check_version:
                            logfile_format = each_version
                            print("Log file format recognized as: %s" % logfile_format)
                            break

                cordaobject_id_match = re.finditer(corda_object_detection, each_line)

                # Definition of references and also collecting information about "CORDA_OBJECTS"(FLOW,TRANSACTIONS)

                if cordaobject_id_match:
                    group_count = 0
                    for matchNum, match in enumerate(cordaobject_id_match, start=1):
                        for groupNum in range(0, len(match.groups())):
                            groupNum = groupNum + 1
                            each_group = match.group(groupNum)
                            if each_group and each_group not in CordaObject.id_ref:
                                # print("id {group} identified as {type}".format(
                                #     group=match.group(groupNum),
                                #     type=all_regex_type[groupNum-1]
                                # ))

                                # Add a new reference found into the list
                                CordaObject.id_ref.append(each_group)
                                #
                                # Also create this object to be identified later:
                                # first extract line features (timestamp, severity, etc)
                                log_line_fields = get_fields_from_log(each_line, logfile_format)
                                # Create object:
                                co = CordaObject()
                                # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                                #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                                #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                                #  ignorar estas referencias...
                                if log_line_fields:
                                    if not 'error_level' in log_line_fields:
                                        log_line_fields['error_level'] = 'INFO'
                                    co.add_data("id_ref", each_group)
                                    co.add_data("Original line", each_line)
                                    co.add_data("error_level", log_line_fields["error_level"])
                                    co.add_data("timestamp", log_line_fields["timestamp"])
                                    co.add_data("type", all_regex_type[groupNum-1])
                                    co.set_type(all_regex_type[groupNum-1])
                                    co.add_object()

                # Definition to check parties
                cordaobject_party_match = re.finditer(corda_party_detection, each_line)
                matches = list(cordaobject_party_match)
                if matches:
                    for matchNum, match in enumerate(matches, start=1):
                        for groupNum in range(0, len(match.groups())):
                            groupNum = groupNum + 1
                            each_group = match.group(groupNum)
                            if each_group:
                                CordaObject.add_uml_object(each_group,'participant')
                                # party = Party()
                                # party.set_name(each_group)
                                # if party.add():
                                #     print(each_group)

        #  /home/larry/IdeaProjects/support/plugins/trackFlow/sup1290/node-diusp-lweb0004.2020-05-21-1.log
        #  /home/r3support/www/uploads/customers/TradeIX/SUP-1480/20200915171050_pack/
        # trace_logs_receiver_1/2020-09/app-09-15-2020-3.log
        print("Summary:")
        for each_type in CordaObject.list:
            print(" * %s %s(S) identified." % (len(CordaObject.list[each_type]), each_type))

        if not logfile_format:
            print("Sorry I can't find a proper log template to parse this log terminating program")
            exit(0)

        if len(CordaObject.id_ref) > 0:
            print('%s file contains %s ids' % (log_file, len(CordaObject.id_ref)))

        if len(CordaObject.id_ref) > 50 and not args.web_style:
            print('**WARNING** this may take long time to complete...')
            print('Do you want to track all id\'s in %s file ?' % (log_file,))

            response = input('> ')
            if response != 'y':
                exit(0)

        # Flows.flow_summary()
        saving_tracing_ref_data(CordaObject.get_all_objects())
        trace_id()
        print('Finished.')
    except IOError as io:
        print('Sorry unable to open %s due to %s' % (log_file, io))

def get_ref_ids_NEW(each_line):
    """
    Search for all identifiable ids on a log

    :return:
    """
    #TODO: transformar estarutina para que trabaje con una sola linea antes lo hacia haciendo un bucle
    global logfile_format
    print("Phase *1* Collect ids")
    corda_objects = Configs.get_config(section='CORDA_OBJECTS')
    corda_object_detection = None
    # Complete list of corda object regex definition
    all_regex = []
    # A helper list to give the type and avoid to do a second search on the config to gather object type
    all_regex_type = []
    if not corda_objects:
        print("No definition for corda objects found, please setup CORDA_OBJECT section on config")
        exit(0)
    else:
        # Collect from "CORDA_OBJECTS" all object definitions:
        corda_objects = Configs.get_config(section="CORDA_OBJECTS")

        for each_type in corda_objects:
            if "EXPECT" in Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]:
                regex_list = Configs.get_config(sub_param=each_type, section="CORDA_OBJECTS")[each_type]["EXPECT"]
                for each_rgx in regex_list:
                    all_regex.append(build_regex(each_rgx, nogroup_name=True))
                    all_regex_type.append(each_type)

        # Prepare full regex for quick detection
        corda_object_detection = "|".join(all_regex)

    try:
        if not logfile_format:
            for each_version in Configs.get_config(section="VERSION"):
                try_version = Configs.get_config(section="VERSION", param=each_version)
                check_version = re.search(try_version["EXPECT"], each_line)
                if check_version:
                    logfile_format = each_version
                    print("Log file format recognized as: %s" % logfile_format)
                    break

        cordaobject_id_match = re.finditer(corda_object_detection, each_line)

        if cordaobject_id_match:
            group_count = 0
            for matchNum, match in enumerate(cordaobject_id_match, start=1):
                for groupNum in range(0, len(match.groups())):
                    groupNum = groupNum + 1
                    each_group = match.group(groupNum)
                    if each_group and each_group not in CordaObject.id_ref:
                        # print("id {group} identified as {type}".format(
                        #     group=match.group(groupNum),
                        #     type=all_regex_type[groupNum-1]
                        # ))

                        # Add a new reference found into the list
                        CordaObject.id_ref.append(each_group)
                        #
                        # Also create this object to be identified later:
                        # first extract line features (timestamp, severity, etc)
                        log_line_fields = get_fields_from_log(each_line, logfile_format)
                        # Create object:
                        co = CordaObject()
                        # TODO: Hay un bug que ocurre cuando el programa detecta un corda_object que esta
                        #  en una linea que esta fuera (tiene retorno de carro) de la linea principal del
                        #  log lo que provoca que el objeto no sea creado... por los momentos voy a
                        #  ignorar estas referencias...
                        if log_line_fields:
                            if not 'error_level' in log_line_fields:
                                log_line_fields['error_level'] = 'INFO'
                            co.add_data("id_ref", each_group)
                            co.add_data("Original line", each_line)
                            co.add_data("error_level", log_line_fields["error_level"])
                            co.add_data("timestamp", log_line_fields["timestamp"])
                            co.add_data("type", all_regex_type[groupNum-1])
                            co.set_type(all_regex_type[groupNum-1])
                            co.add_object()

        #  /home/larry/IdeaProjects/support/plugins/trackFlow/sup1290/node-diusp-lweb0004.2020-05-21-1.log
        #  /home/r3support/www/uploads/customers/TradeIX/SUP-1480/20200915171050_pack/
        # trace_logs_receiver_1/2020-09/app-09-15-2020-3.log
        print("Summary:")
        for each_type in CordaObject.list:
            print(" * %s %s(S) identified." % (len(CordaObject.list[each_type]), each_type))

        if not logfile_format:
            print("Sorry I can't find a proper log template to parse this log terminating program")
            exit(0)

        if len(CordaObject.id_ref) > 0:
            print('%s file contains %s ids' % (log_file, len(CordaObject.id_ref)))

        if len(CordaObject.id_ref) > 50 and not args.web_style:
            print('**WARNING** this may take long time to complete...')
            print('Do you want to track all id\'s in %s file ?' % (log_file,))

            response = input('> ')
            if response != 'y':
                exit(0)

        # Flows.flow_summary()
        saving_tracing_ref_data(CordaObject.get_all_objects())
        trace_id()
        print('Finished.')
    except IOError as io:
        print('Sorry unable to open %s due to %s' % (log_file, io))

def saving_tracing_ref_data(data):
    """
    Will save actual collected reference data to be able to load it quickly
    :param data:
    :return:
    """
    logdir = os.path.dirname(args.log_file)
    log_file = os.path.basename(args.log_file)
    tracer_cache = f'{logdir}/cache'

    if not os.path.exists(tracer_cache):
        os.mkdir(tracer_cache)
    try:
        with open(f"{tracer_cache}/references.json", 'w') as fh_references:
            json.dump(data, fh_references, indent=4)
    except IOError as io:
        print(f'Unable to create cache file {tracer_cache}/references.json due to: {io}')

    return



def build_regex(regex, nogroup_name=False):
    """
    This method will scan given regex to check if a "macro"(regex inside a regex) was included, if so will look for that
    and replace it with its value; then will return complete regex expression
    :param regex: regex to examine
    :return: complete regex expression if a variable needs to be replaced, original regex expression otherwise
    """
    return_regex = regex

    if not Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS"):
        return return_regex

    # cregex = RegexLib.use(r'__([a-zA-Z0-9-_]+)__')
    # check_variable = cregex.findall(regex)
    # check_variable = re.findall(r"__([a-zA-Z0-9-_]+)__", regex)
    ccheck_variable = re.compile(r"__([a-zA-Z0-9-_]+)__")
    check_variable = ccheck_variable.findall(regex)

    if check_variable:
        for each_variable in check_variable:
            # Search where this variable could be applicable to then extract the proper regex replacement for such
            # variable
            #
            for each_object in Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS").keys():
                apply_to = None
                #
                if "APPLY_TO" in Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                    param="OBJECTS", sub_param=each_object):
                    apply_to = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS",
                                                  param="OBJECTS",
                                                  sub_param=each_object)["APPLY_TO"]
                else:
                    print("Warning: %s has no 'APPLY_TO' parameter,"
                          " so I'm not able to identify the match for this label..." %
                          (each_object,))
                #
                # if apply_to list has a content, and check_variable appear in such list, then proceed to do replacement
                if apply_to and each_variable in apply_to:
                    list_expects = "|".join(Configs.get_config(
                        section="CORDA_OBJECT_DEFINITIONS",
                        param="OBJECTS",
                        sub_param=each_object
                    )["EXPECT"])

                    if nogroup_name:
                        regex_replace = "(%s)" % (list_expects,)
                    else:
                        regex_replace = "(?P<%s>%s)" % (
                            each_variable,
                            list_expects
                        )
                    return_regex = regex.replace("__%s__" % each_variable, regex_replace)

                    # if more than one variable is being found make sure to keep previous change before replacing
                    # following variable

                    regex = return_regex
    else:
        # If I do not find the macro variable in the form of "__macro-variable__" then I will need to do a reverse
        # search, to find the actual object... because what I'm sending then is probably a raw Object  definition
        object_definition = Configs.get_config(section="CORDA_OBJECT_DEFINITIONS", param="OBJECTS")
        for each_object in object_definition:
            if regex in object_definition[each_object]['EXPECT']:
                if nogroup_name:
                    regex_replace = "(%s)" % (regex,)
                else:
                    regex_replace = "(?P<%s>%s)" % (
                        each_object,
                        regex
                    )
                return_regex = regex_replace

    return return_regex


def analyse_file(log_file):
    """

    :return:
    """
    logfile_format = None
    with open(log_file, 'r') as ftrack_log:
        for each_line in ftrack_log:
            for each_version in Configs.get_config(section="VERSION"):
                try_version = Configs.get_config(section="VERSION", param=each_version)
                check_version = re.search(try_version["EXPECT"], each_line)
                if check_version:
                    logfile_format = each_version
                    #
                    # print("Log file format recognized as: %s" % logfile_format)
                    break
            if logfile_format:
                logfile_fields = get_fields_from_log(each_line, logfile_format)
                if logfile_fields:
                    if '\\n' in logfile_fields['message']:
                        logfile_fields['message'] = logfile_fields['message'].replace('\\n', '\n')
                    if '\\"' in logfile_fields['message']:
                        logfile_fields['message'] = logfile_fields['message'].replace('\\"', '"')
                    if '\\t' in logfile_fields['message']:
                        logfile_fields['message'] = logfile_fields['message'].replace('\\"', '\t')
                    print(f"{logfile_fields['timestamp']} {logfile_fields['error_level']} {logfile_fields['message']}")
            else:
                print(each_line.strip())


def get_log_format(line, recheck=False):
    """
    Will return log format found on the file
    :return:
    """
    global logfile_format

    if logfile_format and not recheck:
        return logfile_format

    each_format = None
    logfile_format = None
    check_versions = Configs.get_config(section="VERSION")
    for each_version in check_versions:
        check_format = re.search(check_versions[each_version]["EXPECT"], line)
        if check_format:
            logfile_format = each_version
            break

    return logfile_format


def get_fields_from_log(line, log_version):
    """
    Will extract fields results from given log_version on given line
    :param line: Line to extract information from
    :param log_version: Version of log format to extract information
    :return: A dictionary with fields and values
    """
    global logfile_format
    result = {}

    if Configs.get_config("DETECT_LOG_VERSION_EACH_LINE"):
        # it will re-check file format for each line regardless what version has been asked to check
        logfile_format = get_log_format(line, recheck=True)

    # if not format has been found by default, and it has been explicitly set, will use that
    if log_version and not logfile_format:
        logfile_format = log_version

    # if there not format at all, stop process
    if not logfile_format:
        print("I'm not able to recognize log format, in this case I will not be able to pull correct information")
        print("I was unable to find a version template for this file, please create one under VERSION->IDENTITY_FORMAT")
        exit(0)

    extract_fields = Configs.get_config(section="VERSION", param=logfile_format)

    if not extract_fields:
        print("No logfile definitions to check please define at least one (at the section 'VERSION')")
        exit(0)

    fields = re.search(extract_fields["EXPECT"], line)

    if fields:
        if len(fields.groups()) == len(extract_fields["FIELDS"]):
            for each_field in extract_fields["FIELDS"]:
                result[each_field] = fields.group(extract_fields["FIELDS"].index(each_field) + 1)
        else:
            print("Unable to parse log file properly using %s, expecting %s fields got %s fields from extraction" %
                  (logfile_format, len(extract_fields["FIELDS"]), len(fields.groups())))

    return result


def get_endpoints():
    """
    Will return all defined endpoints. these endpoints are used when no source, or destination are explicitly given
    :return:
    """

    return CordaObject.default_uml_endpoints


def set_endpoints(endpoints):
    """
    This will set actual endpoints that were gathered from database
    :return:
    """

    CordaObject.default_uml_endpoints = endpoints


def get_uml_init():
    """
    Will return a list of all participants; this actually had a list of participants that UML script will use at the
    start of script
    :return: a list of participants
    """

    return CordaObject.uml_init


def set_uml_init_list(participant_list):
    """
    This will set all info required by this object at once
    :param participant_list: list uml_object required
    :return: void
    """

    CordaObject.uml_init = participant_list


def load_analysis(hash_key):
    """
    Will load and build required variables to run build_uml_script
    :param hash_key: it is logfile_hash_key reference at database
    :return:
    """
    global database
    # sys.path.append("/home/r3support/www/cgi-bin/support")
    # import support
    # from support import Table, Configs
    support.init_database()
    database = support.database

    #
    # Recover a saved tracer analysis Object from DB
    # Restore uml_init...

    query = database.query(support.TracerUML).filter(
        support.TracerUML.logfile_hash_key==hash_key
    ).order_by(support.TracerUML.order).all()

    if query:
        uml_list = []
        for each_row in query:
            uml_list.append(each_row.participants)

        set_uml_init_list(uml_list)

    # Restore endpoints
    #
    query = database.query(support.TracerDefault_Endpoints).filter(
        support.TracerDefault_Endpoints.logfile_hash_key==hash_key).first()

    if query:
        set_endpoints(json.loads(query.default_uml_endpoints))

    # Restore entities
    #
    query = database.query(support.TracerEntity).filter(support.TracerEntity.logfile_hash_key==hash_key).all()
    for each_row in query:
        set_entity_register(each_row.entity_details)

    # Restore Participants variable
    #
    query = database.query(support.TracerParticipants).filter(
        support.TracerParticipants.logfile_hash_key==hash_key
    ).all()
    if query:
        for each_row in query:
            each_row_participant = clear_participant_str(each_row.participant)
            add_participant(each_row_participant, each_row.role)

            if each_row.role:
                CordaObject.set_participant_role(each_row_participant, each_row.role)

    # Restore stored reference list
    # CordaObject.ref_id and CordaObject.list
    #
    query = database.query(support.TracerDB).filter(support.TracerDB.logfile_hash_key==hash_key).all()
    if query:
        print("Creating Corda Object container...")
        for each_row in query:
            corda_object = CordaObject()
            corda_object.set_type(each_row.type)
            corda_object.data = json.loads(each_row.details)
            corda_object.add_object()
        print("%s Corda Objects created..." % (len(query),))
        #
        # Collect all references (all matching lines with same reference)
        if True:
            print("Collecting references")
            query_references = database.query(support.TracerReferences).filter(
                support.TracerReferences.logfile_hash_key==hash_key).order_by(support.TracerReferences.reference_id,
                                                                              support.TracerReferences.line_no).all()
            print("%s references collected" % (len(query_references,)))
            if query_references:
                ref_counter = 0
                ref_max_counter = 100

                print("Setting up references...")
                for each_reference in query_references:
                    corda_object = get_corda_object(each_reference.reference_id)
                    corda_object.add_reference(each_reference.line_no, json.loads(each_reference.details))
                    corda_object.data = json.loads(each_reference.data)
                    if ref_counter > ref_max_counter:
                        completed = ref_counter*100/len(query_references)
                        print(f"References attached {completed:.2f}%...", flush=True)
                        ref_max_counter += 100

                    ref_counter += 1

                print(f"{ref_counter} references found.")

    list_participants()
    check_participants()


def save_analysis(hash_key):
    """
    Will save actual CordaObject into database for persistence.
    :param hash_key:
    :return:
    """
    global database

    support.init_database()
    database = support.database

    # Store UML init section (participants and controls)
    #
    participant_order = 0
    for each_uml_init in get_uml_init():
        # Generate a unique key for this entry, combining logfile hash_key and a hash created using uml uml_object name
        uml_init_key = support.generate_hash("%s:%s" % (hash_key, each_uml_init))
        if len(uml_init_key) > 255:
            print("logtracer.py: Unable to add uml_object into database, it exceed column character count")
            print("logtracer.py: uml_object value: %s" % uml_init_key)
            print("logtracer.py: string length = %s" % len(uml_init_key))
            print("logtracer.py: this uml_object will not be added.")
            continue
        else:
            query = database.query(support.TracerUML).filter(
                support.TracerUML.participant_key==uml_init_key
            ).first()
        # Check if we have already this information stored
        if not query:
            participant_order += 1
            uml_init = support.TracerUML(
                logfile_hash_key=hash_key,
                participant_key=uml_init_key,
                participants=each_uml_init,
                order=participant_order
            )
            database.add(uml_init)

    # Store all participants found on this file, and role discovered
    #
    save_participants(hash_key)

    # Save all entities with reports
    #
    for each_entity in list_entity_report():
        entity_report = get_entity_report(each_entity)
        #
        # ==== Entity atomization
        #
        # Following code will try to divide content of each entity and try to save its constituent parts; this
        # also have advantage that will keep size of record small, but add difficult task of re-building original object
        # in more steps...
        #
        # if 'state' in get_entity_report(each_entity):
        #     entity_st = get_entity_report(each_entity)['state']
        # else:
        #     entity_st = None
        # valid_states = list(entity_report.keys())
        # valid_states.remove('state')
        #
        # for each_state in valid_states:
        #     for each_entity_reference in get_entity_report(each_entity, each_state):
        #         entity_generated_key = ("%s:%s" % (each_entity_reference, each_state))
        #         # Check if this reference was already stored
        #         query = database.query(support.TracerEntity).\
        #             filter(support.TracerEntity.entity_key==entity_generated_key).first()
        #         if not query:
        #             entity = support.TracerEntity(
        #                 logfile_hash_key=hash_key,
        #                 entity_name=each_entity,
        #                 entity_key=entity_generated_key,
        #                 entity_state=entity_st,
        #                 entity_details=json.dumps(
        #                     get_entity_report(each_entity,
        #                                              each_state,
        #                                              each_entity_reference
        #                                              )
        #                 )
        #             )
        #             database.add(entity)

        # This method will save full object serialising json into a string

        entity_generated_key = support.generate_hash("%s:%s" % (hash_key, each_entity))

        query = database.query(support.TracerEntity).filter(
            support.TracerEntity.entity_key==entity_generated_key
        ).first()

        if not query:
            tracer_entity = support.TracerEntity(
                logfile_hash_key=hash_key,
                entity_key=entity_generated_key,
                entity_name=each_entity,
                entity_details=entity_report
            )

            database.add(tracer_entity)

    # Store current default endpoints
    #
    query = database.query(support.TracerDefault_Endpoints).filter(
        support.TracerDefault_Endpoints.logfile_hash_key == hash_key).first()

    if not query:
        tracer_uml_endpoints = support.TracerDefault_Endpoints(
            logfile_hash_key=hash_key,
            default_uml_endpoints='%s' % json.dumps(get_endpoints())
        )
        database.add(tracer_uml_endpoints)

    # Save the object -- CordaObject.list
    #
    for each_corda_type in get_corda_object_types():
        for each_reference in list_corda_objects(each_corda_type):
            corda_object = get_corda_object(each_reference)
            # I need to make reference unique for this file; there're some type of objects (like transactions) that
            # can be found on other nodes logs, this key will prevent they are loaded on other logs that are not the
            # one being analysed.
            reference_generated_key = support.generate_hash("%s:%s" % (hash_key, each_reference))
            query = database.query(support.TracerDB).filter(
                support.TracerDB.reference_key==reference_generated_key
            ).first()

            # If reference_id do not exist, then store it
            if not query:
                tracerdb = support.TracerDB(
                    logfile_hash_key=hash_key,
                    reference_key=reference_generated_key,
                    type=each_corda_type,
                    reference_id=each_reference,
                    details='%s' % json.dumps(corda_object.data)
                )
                database.add(tracerdb)

            # Store all references for this object
            #
            for each_line in corda_object.get_references():
                reference_generated_key = support.generate_hash("%s:%s:%s" % (hash_key, each_reference, each_line))
                query = database.query(support.TracerReferences).filter(
                    support.TracerReferences.reference_key==reference_generated_key).first()
                if not query:
                    tracer_references = support.TracerReferences(
                        logfile_hash_key=hash_key,
                        reference_id=each_reference,
                        reference_key=reference_generated_key,
                        line_no=each_line,
                        data=json.dumps(corda_object.data),
                        details='%s' % json.dumps(corda_object.get_references(line_no=each_line))
                    )
                    database.add(tracer_references)

    database.commit()


def delete_analysis_batch(logfile_hash_key, database_to_use=None):
    """
    This method will delete all trace analysis done, but will not communicate back its progress...
    :param hash_key:
    :return:
    """
    global database
    if database_to_use:
        database = database_to_use
    else:
        load_analysis(logfile_hash_key)

    print("[WORKER] deleting analysis batch tables")

    database.query(support.TracerDB).filter(support.TracerDB.logfile_hash_key==logfile_hash_key).delete()
    database.query(support.TracerUML).filter(support.TracerUML.logfile_hash_key==logfile_hash_key).delete()
    database.query(support.TracerParticipants).filter(
        support.TracerParticipants.logfile_hash_key==logfile_hash_key).delete()
    database.query(support.TracerEntity).filter(support.TracerEntity.logfile_hash_key==logfile_hash_key).delete()
    database.query(support.TracerReferences).filter(
        support.TracerReferences.logfile_hash_key==logfile_hash_key).delete()
    database.query(support.TracerDefault_Endpoints).filter(
        support.TracerDefault_Endpoints.logfile_hash_key==logfile_hash_key).delete()

    update = database.query(support.AnalysisQueue).filter(
        support.AnalysisQueue.logfile_hash_key==logfile_hash_key).first()

    if update:
        # Update queue message...
        update.message = None

    support.dbcommit()


def save_uml_elements(hash_key):
    """

    :param hash_key:
    :return:
    """
    # Store UML init section (participants and controls)
    #
    global database

    support.init_database()
    database = support.database
    participant_order = 0
    for each_uml_init in get_uml_init():
        # Generate a unique key for this entry, combining logfile hash_key and a hash created using uml uml_object name
        uml_init_key = support.generate_hash("%s:%s" % (hash_key, each_uml_init))
        query = database.query(support.TracerUML).filter(
            support.TracerUML.participant_key==uml_init_key
        ).first()
        # Check if we have already this information stored
        if not query:
            participant_order += 1
            uml_init = support.TracerUML(
                logfile_hash_key=hash_key,
                participant_key=uml_init_key,
                participants=each_uml_init,
                order=participant_order
            )
            database.add(uml_init)


def save_participants(hash_key):
    """
    This method will save current uml_object list... this is made because in some cases log "owner" can not be
    identified automatically, in this case to continue with the analysis user intervention is required to select
    correct log "owner"
    :param hash_key: Logfile_hash_key to identify this log
    :return:
    """
    global database

    if not database:
        support.init_database()
        database = support.database

    # Store all participants found on this file, and role discovered
    #
    for each_participant in list_participants():
        # Create uml_object hash key combining file key and uml_object. This will guarantee uniqueness
        #
        participant_hash_key = support.generate_hash("%s:%s" % (hash_key, support.generate_hash(each_participant)))
        query = database.query(support.TracerParticipants). \
            filter(support.TracerParticipants.participant_key==participant_hash_key).first()
        # Check if we have already this information stored
        if not query:
            if len(each_participant) > 255:
                print("logtracer.py: Unable to add uml_object into database, it exceed column character count")
                print("logtracer.py: uml_object value: %s" % each_participant)
                print("logtracer.py: string length = %s" % len(each_participant))
                print("logtracer.py: this uml_object will not be added.")
            else:
                tracer_participant = support.TracerParticipants(
                    logfile_hash_key=hash_key,
                    participant_key=participant_hash_key,
                    participant=each_participant,
                    role=get_participant_role(each_participant)
                )
                database.add(tracer_participant)

    database.commit()


def check_for_participants(original_line):
    """
    This method was extracted (copied) from its original location at analysis method, reason
    :type original_line: object
    :return:
    """
    global party_found
    # Get uml_object "EXPECT" to search for
    uml_definition = Configs.get_config_from("UML_DEFINITIONS")
    uml_rtn = {}
    uml_step = {}

    # for each_definition in uml_definition:
    #     check_party = RegexLib.use(build_regex(each_definition))
    #
    #     if check_party:
    #         pass

    # Loop over all UML definitions
    # for each_uml_definition in uml_definition:
    uml_participants = ["participant", "log_owner", "notary", "log_owner/notary"]
    # if 'notary' in original_line or 'Notary' in original_line:
    #     print(original_line)
    # now for each uml definition, try to see if we have a match
    #
    # Stage 1: Find out which UML command should be applied to given line
    # In this section, i will loop over all defined UML commands, and find out if this line match any of them
    #
    for each_uml_definition in uml_participants:
        regex_index = regex_to_use(uml_definition[each_uml_definition]["EXPECT"], original_line)

        if regex_index is None:
            return

        each_expect = build_regex(uml_definition[each_uml_definition]["EXPECT"][regex_index])
        # match = re.search(each_expect, original_line)
        #
        reach_expect = RegexLib.use(each_expect)
        match = reach_expect.search(original_line)

        if match:
            grp = 1
            if match.groupdict():
                for each_field in match.groupdict():
                    ignore = False
                    if 'IGNORE' in uml_definition[each_uml_definition]:
                        for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                            if each_ignore_word in original_line:
                                ignore = True
                    # Check if this specific statement has some specific words that should prevent this
                    # assignation to take place
                    #
                    if not ignore:
                        # CordaObject.add_uml(match.group(grp), each_field)
                        # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                        if match.group(each_field):
                            grp_value = match.group(each_field).strip().strip(".")
                            party_found = True
                            if "OPTIONS" in uml_definition[each_uml_definition] and \
                                    "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                already_defined = False
                                for each_definition in CordaObject.uml_init:
                                    if grp_value in each_definition:
                                        already_defined = True
                                if already_defined:
                                    continue
                                else:
                                    uml_def = CordaObject.get_corda_object_definition_for(each_uml_definition)
                                    # grp_value = define_field_limits(grp_value, uml_def)
                                    if uml_def:
                                        CordaObject.add_uml_object(grp_value, uml_def)
                                    else:
                                        CordaObject.add_uml_object(grp_value, each_uml_definition)
                            else:
                                uml_set = False
                                # Search each field on given line to see if it exists and extract its value
                                #
                                for each_field_def in uml_definition[each_uml_definition]["FIELDS"]:
                                    if ":" in each_field_def:
                                        extract_field = each_field_def.split(":")[1]
                                    else:
                                        extract_field = each_field_def
                                        print("Warning: This definition is missing proper labels on regex\n"
                                              "%s" % each_expect)

                                    # if value for this field already exist on the EXPECTED (default one) then
                                    # get it otherwise, get proper expect to extract it from current log line

                                    if each_field == extract_field:
                                        uml_set = True
                                        uml_rtn[grp_value] = each_field_def
                                        uml_step[each_uml_definition] = uml_rtn

                                if not uml_set:
                                    print("Warning unable to set proper values for group %s, not UML group"
                                          " set on '%s' definition" % (each_field, each_uml_definition))
                                    print("Offending line: \n%s" % original_line)

            else:
                #
                # TODO: no estoy seguro para que hice esta seccion, por lo que se ve en la logica ^^
                #  nunca se llegara a alcanzar esta parte porque match.groupdict() "SIEMPRE" devolvera
                #  un grupo amenos que no tenga la definicion de grupo en el "EXPECT" lo cual seria un error
                for each_field in uml_definition[each_uml_definition]["FIELDS"]:
                    if grp > len(match.groups()):
                        print("Warning: There's no group to cover %s definition on '%s' setting...!" %
                              (each_field, each_uml_definition))
                        print("Scanned line:\n %s" % (original_line,))
                    else:
                        ignore = False
                        if 'IGNORE' in uml_definition[each_uml_definition]:
                            for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
                                if each_ignore_word in original_line:
                                    ignore = True
                        # Check if this specific statement has some specific words that should prevent this
                        # assignation to take place
                        #
                        if not ignore:
                            # CordaObject.add_uml(match.group(grp), each_field)
                            # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)

                            if match.group(grp):
                                grp_value = match.group(grp).strip().strip(".")
                                # grp_value = define_field_limits(grp_value, each_uml_definition)

                                if "OPTIONS" in uml_definition[each_uml_definition] and \
                                        "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
                                    if '%s "%s"' % (each_uml_definition, grp_value) not in CordaObject.uml_init:
                                        CordaObject.add_uml_object(grp_value, each_uml_definition)
                                    else:
                                        continue
                                else:
                                    uml_rtn[grp_value] = each_field
                                    uml_step[each_uml_definition] = uml_rtn

                    grp += 1

                # A match message was found (uml action definition), it doesn't make sense to go through the
                # rest This will avoid to do a regex of each 'EXPECT' over action UML_DEFINITION
                #break


# def check_for_participants__x(original_line):
#     """
#     This method was extracted (copied) from its original location at analysis method, reason
#     :type original_line: object
#     :return:
#     """
#     global party_found
#     uml_definition = Configs.get_config(section="UML_DEFINITIONS")
#     uml_rtn = {}
#
#     uml_step = {}
#     # Loop over all UML definitions
#     for each_uml_definition in uml_definition:
#         # now for each uml definition, try to see if we have a match
#         #
#         # Stage 1: Find out which UML command should be applied to given line
#         # In this section, i will loop over all defined UML commands, and find out if this line match any of them
#         #
#         regex_index = regex_to_use(uml_definition[each_uml_definition]["EXPECT"], original_line)
#
#         if regex_index is None:
#             continue
#
#         each_expect = build_regex(uml_definition[each_uml_definition]["EXPECT"][regex_index])
#         # match = re.search(each_expect, original_line)
#         #
#         reach_expect = RegexLib.use(each_expect)
#         match = reach_expect.search(original_line)
#
#         if match:
#             grp = 1
#             if match.groupdict():
#                 for each_field in match.groupdict():
#                     ignore = False
#                     if 'IGNORE' in uml_definition[each_uml_definition]:
#                         for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
#                             if each_ignore_word in original_line:
#                                 ignore = True
#                     # Check if this specific statement has some specific words that should prevent this
#                     # assignation to take place
#                     #
#                     if not ignore:
#                         # CordaObject.add_uml(match.group(grp), each_field)
#                         # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)
#
#                         if match.group(each_field):
#                             grp_value = match.group(each_field).strip().strip(".")
#                             party_found = True
#                             if "OPTIONS" in uml_definition[each_uml_definition] and \
#                                     "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
#                                 already_defined = False
#                                 for each_definition in CordaObject.uml_init:
#                                     if grp_value in each_definition:
#                                         already_defined = True
#                                 if already_defined:
#                                     continue
#                                 else:
#                                     uml_def = CordaObject.get_corda_object_definition_for(each_uml_definition)
#                                     # grp_value = define_field_limits(grp_value, uml_def)
#                                     if uml_def:
#                                         CordaObject.add_uml_object(grp_value, uml_def)
#                                     else:
#                                         CordaObject.add_uml_object(grp_value, each_uml_definition)
#                             else:
#                                 uml_set = False
#                                 # Search each field on given line to see if it exist and extract its value
#                                 #
#                                 for each_field_def in uml_definition[each_uml_definition]["FIELDS"]:
#                                     if ":" in each_field_def:
#                                         extract_field = each_field_def.split(":")[1]
#                                     else:
#                                         extract_field = each_field_def
#                                         print("Warning: This definition is missing proper labels on regex\n"
#                                               "%s" % each_expect)
#
#                                     # if value for this field already exist on the EXPECTED (default one) then
#                                     # get it otherwise, get proper expect to extract it from current log line
#
#                                     if each_field == extract_field:
#                                         uml_set = True
#                                         uml_rtn[grp_value] = each_field_def
#                                         uml_step[each_uml_definition] = uml_rtn
#
#                                 if not uml_set:
#                                     print("Warning unable to set proper values for group %s, not UML group"
#                                           " set on '%s' definition" % (each_field, each_uml_definition))
#                                     print("Offending line: \n%s" % original_line)
#
#             else:
#                 #
#                 # TODO: no estoy seguro para que hice esta seccion, por lo que se ve en la logica ^^
#                 #  nunca se llegara a alcanzar esta parte porque match.groupdict() "SIEMPRE" devolvera
#                 #  un grupo amenos que no tenga la definicion de grupo en el "EXPECT" lo cual seria un error
#                 for each_field in uml_definition[each_uml_definition]["FIELDS"]:
#                     if grp > len(match.groups()):
#                         print("Warning: There's no group to cover %s definition on '%s' setting...!" %
#                               (each_field, each_uml_definition))
#                         print("Scanned line:\n %s" % (original_line,))
#                     else:
#                         ignore = False
#                         if 'IGNORE' in uml_definition[each_uml_definition]:
#                             for each_ignore_word in uml_definition[each_uml_definition]["IGNORE"]:
#                                 if each_ignore_word in original_line:
#                                     ignore = True
#                         # Check if this specific statement has some specific words that should prevent this
#                         # assignation to take place
#                         #
#                         if not ignore:
#                             # CordaObject.add_uml(match.group(grp), each_field)
#                             # uml_rtn += "%s = %s\n" % (match.group(grp), each_field)
#
#                             if match.group(grp):
#                                 grp_value = match.group(grp).strip().strip(".")
#                                 # grp_value = define_field_limits(grp_value, each_uml_definition)
#
#                                 if "OPTIONS" in uml_definition[each_uml_definition] and \
#                                         "SINGLE_DEFINITION" in uml_definition[each_uml_definition]["OPTIONS"]:
#                                     if '%s "%s"' % (each_uml_definition, grp_value) not in CordaObject.uml_init:
#                                         CordaObject.add_uml_object(grp_value, each_uml_definition)
#                                     else:
#                                         continue
#                                 else:
#
#                                     uml_rtn[grp_value] = each_field
#                                     uml_step[each_uml_definition] = uml_rtn
#
#                     grp += 1
#
#                 # A match message was found (uml action definition), it doesn't make sense to go through the
#                 # rest This will avoid to do a regex of each 'EXPECT' over action UML_DEFINITION
#                 #break


def get_log_owner():
    """
    Expose variable log owner from CordaObject
    :return: string
    """

    return CordaObject.log_owner


def set_log_owner(party, attach_usages=False):
    """
    Expose this method from CordaObject
    :param party: Id of log_owner
    :param attach_usages: attach default usages to it
    :return: nothing
    """

    CordaObject.set_participant_role(party, role="log_owner", attach_usages=attach_usages)


def check_party(party):
    """
    This method will keep x500 names in a standard way to keep all consistent
    :param party: party x500 subject name
    :return: return always same standard layout of x500 name
    """
    field_order = Configs.get_config(section="UML_CONFIG")
    fields = party.split(",")
    standard_layout = []
    for each_position in field_order:
        for each_field in fields:
            check = re.search(r'^%s\*s=\*s' % each_position, each_field)
            if check:
                standard_layout.append(each_field)

    final_party_name = ", ".join(standard_layout).strip()

    return final_party_name


if __name__ == "__main__":
    app_path = os.path.dirname(os.path.abspath(__file__))
    app_path_support = app_path
    parser = argparse.ArgumentParser()
    participant_build = []

    parser.add_argument('-t', '--transaction-details',
                        help='Will show each stage for every transaction found for given flow', action='store_true')
    parser.add_argument('-f', '--flow-id', help='Track given flow id and show all transactions created')
    parser.add_argument('-l', '--log-file', help='Log file to analyse')
    parser.add_argument('-tx', '--transaction-id', help='Give all details of given transaction')
    parser.add_argument('-o', '--output', help='Specify output file')
    parser.add_argument('-w', '--web-style', help='Will give a HTML output format', action='store_true')
    parser.add_argument('-i', '--ignore-order', help='Giving this option, output will respect the order'
                                                     ' how a transaction is being set at configuration,'
                                                     ' otherwise it will be ordered by timestamp', action='store_true')
    parser.add_argument('--simple-tables', help='show simple rendered text tables', action='store_true')
    parser.add_argument('--no-tables', help='show simple rendered text tables', action='store_true')
    parser.add_argument('--generate-uml', '-u', help='Makes program generates a UML graph for each '
                                                     'transaction or Flow found', action="store_true")
    parser.add_argument('--full-tables', help='show simple rendered text tables', action='store_true')
    parser.add_argument('--simplify', help='Read original file, and outputs a simplify version of it',
                        action="store_true")
    parser.add_argument('--generate-uml-for','-gu',
                        help='Generate a UML chart for a specific reference')
    args = parser.parse_args()
    load_corda_object_definition()
    Configs.load_config()
    load_rules()

    if not args.log_file:
        print('You must provide a log file to scan')
        exit(0)
    else:
        log_file = args.log_file

    if args.simplify:
        analyse_file(log_file)
        exit(0)
    if args.flow_id:
        flow_id = args.flow_id
    if args.transaction_id:
        transaction_id = args.transaction_id

    if not flow_id and not transaction_id:
        get_ref_ids()
        exit(0)

    print('Working...')
    if args.web_style:
        print('<html>')
    # track_flow(flow_id, transaction_id)

    if args.web_style:
        print("<hr>")
    # Flows.flow_summary()

    if args.web_style:
        print('</html>')

