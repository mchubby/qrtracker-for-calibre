#!/usr/bin/env python2
# vim:fileencoding=utf-8:ai:ts=4:sw=4:et:sts=4:tw=128:
from __future__ import (unicode_literals, division, absolute_import, print_function)

__license__ = 'GPL v3'
__copyright__ = '2016, Marco77 <http://www.mobileread.com/forums/member.php?u=271721>'
__docformat__ = 'restructuredtext en'

from copy import deepcopy 
from datetime import datetime 
from future_builtins import map 
import io 
from lxml import etree 
import os
from PyQt5.Qt import (
    Qt,
    QAction,
    QMenu)
import calibre.constants
from calibre.ebooks.oeb.base import (
    XHTML)
from calibre.ebooks.oeb.polish.container import (
    OEB_DOCS,
    OEB_STYLES)
from calibre.ebooks.oeb.polish.cover import (
    find_cover_image_in_page,
    get_cover_page_name)
from calibre.ebooks.oeb.polish.split import (
    AbortError)
from calibre.gui2 import (
    error_dialog,
    info_dialog)
from calibre.gui2.tweak_book import (
    current_container,
    editors,
    editor_name)
from calibre.gui2.tweak_book.plugin import (
    Tool)  # base class for all tools
from calibre.gui2.tweak_book.polish import (
    show_report)
from calibre.gui2.tweak_book.widgets import (
    BusyCursor)
from calibre.utils.config import (
    JSONConfig)

###########################################################
"""Import packages local to this plugin"""
try:
    # from calibre_plugins.qrcode_tracker_philidel.extern import six
    from calibre_plugins.qrcode_tracker_philidel.extern.main import QRCode
except ImportError as e:
    import traceback
    print(traceback.format_exc())
###########################################################


class GroupedAbortError(AbortError):
    """Exception grouping several errors"""

    _messages = []

    def __init__(self, messages_iterable):
        """Store messages passed from constructor"""
        self._messages = [x for x in messages_iterable]

    @property
    def messages(self):
        """Accessor"""
        return self._messages


class EditBook_QrCodeTrackerFilidelPlugin(Tool):
    """
    Implement a Calibre "Edit Book" Plugin

    base class is ``calibre.gui2.tweak_book.plugin.Tool``, defined
    in <https://github.com/kovidgoyal/calibre/blob/master/src/calibre/gui2/tweak_book/plugin.py>
    """

    name = 'qr-tracker-filidel'  # doubles as QAction id
    allowed_in_toolbar = True  # user can place in plugins toolbar
    allowed_in_menu = True  # user can place in plugins menu

    # toggle switch for single file mode
    act_on_current = True if calibre.constants.DEBUG else False

    title_headings_list = ('h1', 'h2', 'h3', 'h4')

    toolbar_checkbox_ref = None

    def __init__(self):
        """Initialize plugin preferences"""
        # Default settings {{{
        self.cprefs = JSONConfig(self.name)
        d = self.cprefs.defaults
        d['auto_insert_xmlns_epub'] = False
        d['node_element_id'] = ['qrtracker', 'qrtrack', 'filidel']
        d['node_element_tagname'] = 'aside'
        d['node_element_type'] = None   # epub:type attribute
        d['imagepath_fmt'] = "filidelqr-{pagename_noext}.png"
        # }}}


    def create_action(self, for_toolbar=True):
        """
        Implement function defined in base class

        Called back to create Actions for Plugin Menu and Toolbar
        """
        ac = QAction(get_icons('images/{0}-icon.png'.format(self.name)), _('Filidel: Add QR trackers'), self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, self.name, default_keys=('Ctrl+Shift+Alt+Q',))
        else:
            menu = QMenu()
            ac.setMenu(menu)
            checked_menu_item = menu.addAction('placeholder', self.toggle_act_on_current)
            checked_menu_item.setCheckable(True)
            checked_menu_item.setChecked(self.act_on_current)
            self.toolbar_checkbox_ref = checked_menu_item
            self.plugin_ui_refresh()
        ac.triggered.connect(self.dispatcher)
        return ac


    def toggle_act_on_current(self):
        """
        Uncheck, or check, the 'single file mode' menu item flag, then refreshes the UI.

        Called by toolbar menu action.
        """
        self.act_on_current = not self.act_on_current
        self.plugin_ui_refresh()
        # self.save_prefs()


    def plugin_ui_refresh(self):
        """Change plugin-related UI elements based on context, such as menu item labels"""
        if self.toolbar_checkbox_ref is not None:
            self.toolbar_checkbox_ref.setText(_('Add QR only to active file in editor [enabled]')
                                              if self.act_on_current
                                              else _('Add QR only to active file in editor [disabled]'))


    @property
    def book_title(self):
        """Extract series from open book"""
        if self.current_container is not None:
            if not self.current_container.mi.is_null('title'):
                return self.current_container.mi.title
            if not self.current_container.mi.is_null('series'):
                if not self.current_container.mi.is_null('series_index'):
                    return "{0} #{1}".format(self.current_container.mi.series, self.current_container.mi.series_index)
                return self.current_container.mi.series
        return None


    def dispatcher(self):
        """
        Execute actions based on user-selected preferences

        Called by menu or toolbar action (UI 'slot')
        """
        if not self.boss.ensure_book(_('You must first open a book to tweak, before trying to Add QR Trackers.')):
            return
        if self.book_title is None:
            show_report(False,
                        _('Operation was cancelled'),
                        [_('Please set a title and/or a series name in the book metadata')],
                        self.gui, False)
            return

        self.boss.commit_all_editors_to_container()

        # check media type for single file mode
        if self.act_on_current:
            current_name = editor_name(self.gui.central.current_editor)
            if not current_name or self.current_container.mime_map[current_name] not in OEB_DOCS:
                show_report(False,
                            _('Operation was cancelled'),
                            [_('No file open for editing or the current file is not an (x)html file.')],
                            self.gui, False)
                return
        else:
            try:
                next(self.current_container.manifest_items_of_type(OEB_DOCS))
            except StopIteration:
                show_report(False,
                            _('Operation was cancelled'),
                            [_('This book does not seem to reference html files in its spine.')],
                            self.gui, False)
                return

        self.boss.add_savepoint(_('Before: Filidel: Add QR trackers ({0})').format(datetime.now().strftime('%c')))
        with BusyCursor():
            try:
                num_qr, num_max, grouped_exc = self.process_files()
            except Exception:
                import traceback
                error_dialog(self.gui,
                             _('Failed to add QR trackers'),
                             _('The complete error details may be viewed by clicking the "Show details" button'),
                             det_msg=traceback.format_exc(),
                             show=True)
                self.boss.rewind_savepoint()
            else:
                if grouped_exc is not None:
                    show_report(False,
                                _('The following items could not be processed'),
                                grouped_exc.messages,
                                self.gui, False)
                msg = _('{0} QR images were added out of {1}. Click "See What Changed" below to view differences.').format(
                    num_qr, num_max)
                d = info_dialog(self.gui,
                                _('Filidel plugin has added QR trackers'),
                                msg,
                                show=False)
                d.b = d.bb.addButton(_('See what &changed'), d.bb.AcceptRole)
                # d.b.setIcon(QIcon(I('diff.png'))), b.setAutoDefault(False)
                d.b.clicked.connect(lambda: self.boss.show_current_diff(allow_revert=False), type=Qt.QueuedConnection)
                d.exec_()
                self.boss.apply_container_update_to_gui()
                # todo: scroll to inserted element in single-mode
                # self.gui.show_status_message(msg, 5)


    def process_files(self):
        """
        Run plugin logic against one or more several "names"

        If running in single file mode, we have asserted an active (x)HTML entry is in use.
        For a rough idea of prerequisites and actions, see docs
        For each input file, which passes validation:
            - Generate QR text contents, convert to indexed png
            - Get node insertion point and contents
            - (over)write target image to spine
        """
        if self.act_on_current:
            names = [editor_name(self.gui.central.current_editor)]
        else:
            cover_page_name = get_cover_page_name(self.current_container)
            if cover_page_name is not None:
                names = [name
                         for name in self.current_container.manifest_items_of_type(OEB_DOCS)
                         if cover_page_name != name]
            else:
                names = [name
                         for name in self.current_container.manifest_items_of_type(OEB_DOCS)]
                # is first item a simple cover wrapper?
                if find_cover_image_in_page(self.current_container, names[0]) is not None:
                    names = names[1:]

        # todo: use a progress dialog class worker
        # d = QrAddingProgress(names=names)
        names_to_process = [name
                            for name in self.get_probable_chapters(names, 0.3)]
        if len(names_to_process) == 0:
            raise GroupedAbortError([_('Filidel has found no suitable candidate HTML page to process in the book spine.')])

        logarray = []
        num_qr = 0
        for name in names_to_process:
            try:
                title = self.get_chapter_title(self.current_container, name)
                # prepare_html_node() invokes remove_previous_qr(), so make sure to only insert target image afterwards
                insert_parent = self.prepare_html_node(self.current_container, name)
                self.current_container.dirty(name)

                qr_image_name = self.generate_qrcode(self.current_container, name, title)  # add_to_spine=True
                self.embed_qr_link(self.current_container, name, insert_parent, qr_image_name)
                self.current_container.dirty(name)
            except AbortError as e:  # those are raised errors where stack trace is not deemed very important
                logarray.append('<b>{name}</b>: {msg}'.format(name=name, msg=e.message))
            else:
                num_qr += 1
        grouped_exc = GroupedAbortError(logarray) if len(logarray) > 0 else None
        return num_qr, len(names_to_process), grouped_exc

    def get_probable_chapters(self, names, min_score):
        """
        Gather pages deemed to have content

        Return an iterator containing items scoring above or equal to min_score
        (in [0.0-1.0] range)
        """
        for name in names:
            if self.real_chapter_probability(self.current_container, name) >= min_score:
                # We do not want to attach QR codes to cover page, galleries and so forth
                yield name


    def real_chapter_probability(self, container, name):
        """
        Compute probability a given chapter has textual contents

        (e.g. as opposed to an illustration gallery)
        Return a decimal value in [0-1] representing the computed probability
        name refers to a chapter with actual content.
        """
        score = 0.8
        if len(container.raw_data(name)) >= 10240:
            return score  # quite positive it is a chapter
        root = container.parsed(name)  # Parsed HTML files are lxml elements
        if 'epub' in root.nsmap:
            score += 0.3
            nsmap = {}
            nsmap['epub'] = root.nsmap['epub']
            for element in root.xpath('//*[@epub:type]', namespaces=nsmap):
                # print("*-{0}\n".format(element.attrib))
                # retard notation brought to you by lxml
                epubtype = element.attrib['{' + '{0}'.format(nsmap['epub']) + '}type']
                # print(" - type = {0}\n".format(epubtype))
                if epubtype is not None and epubtype.lower() == 'introduction':
                    score += -0.7
        # Score down pages which look like an illustration gallery
        images_tag_count = root.xpath('count(//*[local-name()="svg" or local-name()="img"])')
        # print("svg/img = {0}\n".format(images_tag_count))
        if images_tag_count < 1:
            score += 0.3
        else:
            score += -images_tag_count / len(container.raw_data(name)) * 1024

        # print("Name = {0} Score= {1} -> {2}\n".format(name, score, max(0.0, min(1.0, score))))
        return max(0.0, min(1.0, score))


    def get_chapter_title(self, container, name):
        """
        Attempt to obtain title for an (x)html file using various approaches.

        Falls back to entry filename as a last resort
        Returns a string
        """
        root = container.parsed(name)
        nsmap = deepcopy(root.nsmap)
        nsmap.pop(None, None)

        if 'epub' in root.nsmap:
            for heading in self.title_headings_list:
                expr = '//*[@epub:type="title" and local-name()="' + heading + '"]'
                title = self._get_enclosed_text_from_xpath(root, expr, nsmap)
                if title is not None:
                    return title
            expr = '//*[@epub:type="chapter" and @title!=""]'
            for node in root.xpath(expr, namespaces=nsmap):
                title = node.attrib['title']
                if title is not None and title.strip() != "":
                    return title.strip()

        for titlenode in root.xpath('//title', namespaces=nsmap):
            if len(titlenode.text.strip()) > 0:
                # print("<title> = {0}\n".format(titlenode.text.strip()))
                return titlenode.text.strip()

        for heading in self.title_headings_list:
            expr = '//*[local-name()="' + heading + '"]'
            title = self._get_enclosed_text_from_xpath(root, expr, nsmap)
            if title is not None:
                return title
        return os.path.basename(name)


    def _get_enclosed_text_from_xpath(self, element, expr, namespaces):
        """
        Select an element via provided xpath expression and returns its rendered contents

        Convert inner text/nodes to text using ``lxml``, regardless of spans etc.
        """
        headingnodes = element.xpath(expr, namespaces=namespaces)
        if len(headingnodes) > 0:
            title = etree.tostring(headingnodes[0], method='text', encoding="UTF-8").strip()
            # print("heading type = {0}\n".format(title))
            return title
        return None


    def prepare_html_node(self, container, name, prefs=None):
        """
        Clean up HTML container for the QR image

        Search if suitable node in chapter already exists
        Delete existing image if applicable
        """
        prefs = prefs or self.cprefs
        # prefs = {k:prefs.get(k) for k in cprefs.defaults}
        # prefs = Prefs(**prefs)

        root = container.parsed(name)

        expr = '//*[' + ' or '.join(map(lambda x: '@id="{0}"'.format(x), prefs['node_element_id'])) + ']'
        nodes = root.xpath(expr)
        insert_element = nodes[0] if len(nodes) > 0 else None
        # raise AbortError(etree.tostring(nodes[0], method='html', encoding="UTF-8").strip())
        self.remove_previous_qr(container, name, insert_element)
        insert_element = self.create_element_placeholder(container, name, insert_element)
        return insert_element


    def remove_previous_qr(self, container, name, insert_element):
        """
        Remove previous image from spine, if applicable.

        insert_element must be an instance of lxml's API element
        """
        container.remove_item(self.target_qr_filename_from_name(name))
        if insert_element is None:
            return

        root = container.parsed(name)

        for elt in insert_element.iter('{' + '{0}'.format(root.nsmap[None]) + '}img'):
            # resolve relative or absolute hyperlink
            qrname = container.href_to_name(elt.attrib['src'], name)
            # print(etree.tostring(elt, method='html', encoding="UTF-8").strip())
            if qrname not in container.names_that_must_not_be_removed:
                # print("! {0}\n".format(qrname))
                self.boss.commit_dirty_opf()
                container.remove_item(qrname)
                if qrname in editors:
                    self.boss.close_editor(qrname)
            break


    def create_element_placeholder(self, container, name, insert_element, prefs=None):
        """
        Create an element to place our code

        insert_element must be an instance of lxml's API element
        """
        prefs = prefs or self.cprefs
        root = container.parsed(name)

        if insert_element is not None:
            if 'id' not in insert_element.attrib:
                insert_element.attrib['id'] = prefs['node_element_id'][0]
            if 'class' not in insert_element.attrib:
                insert_element.attrib['class'] = prefs['node_element_id'][0]
            container.dirty(name)
            etree.tostring(root)
            return insert_element

        body_nodes = root.xpath('//*[local-name()="body"][1]')
        if len(body_nodes) == 0:
            raise AbortError("{0} does not have a &lt;body> tag, please check book prior to running this plugin.".format(name))
        node = etree.SubElement(body_nodes[0], XHTML(prefs['node_element_tagname']),
                                id=prefs['node_element_id'][0])
        node.attrib['class'] = prefs['node_element_id'][0]
        node.tail = '\n'
        if prefs['node_element_type'] is not None and 'epub' in root.nsmap:
            node.attrib['{' + '{0}'.format(root.nsmap['epub']) + '}type'] = prefs['node_element_type']
        # works: etree.SubElement(body_nodes[0], XHTML('div'), id='testing0')
        # works: etree.SubElement(root, XHTML('span'), id='testing')
        container.dirty(name)
        return node


    def generate_qrcode(self, container, name, item_title, add_to_spine=True, prefs=None):
        """
        Generate a QR image and optionally add it to spine

        Return its name
        """
        prefs = prefs or self.cprefs

        qr = QRCode()
        qr.add_data(_('Completed {0} - {1}').format(self.book_title, item_title))
        im = qr.make_image()
        data = None
        with io.BytesIO() as output:
            im.save(output, format='png')
            output.seek(0)
            data = output.read()
        # debug: set edit_file param to True to automatically open in editor
        return container.add_file(self.target_qr_filename_from_name(name), data)

    def target_qr_filename_from_name(self, item_name, prefs=None):
        """Return spine name for target QR png"""
        prefs = prefs or self.cprefs

        path = os.path.basename(item_name)
        path_noext = os.path.splitext(path)[0]
        return prefs['imagepath_fmt'].format(pagename=path, pagename_noext=path_noext)


    def embed_qr_link(self, container, name, insert_element, image_name, prefs=None):
        """
        Add image link in given element

        Commit changes to editor
        """
        root = container.parsed(name)

        eltimg = None
        for elt in insert_element.iter('{' + '{0}'.format(root.nsmap[None]) + '}img'):
            eltimg = elt
            break
        if eltimg is None:
            eltimg = etree.SubElement(insert_element, XHTML('img'))
            eltimg.tail = '\n'

        eltimg.attrib['src'] = container.name_to_href(image_name, name)

        container.dirty(name)
        print(etree.tostring(insert_element, method='html', encoding="UTF-8").strip())
        return eltimg
