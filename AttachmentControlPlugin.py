# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AttachmentControl
                                 A QGIS plugin
 empty
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-09-19
        git sha              : $Format:%H$
        copyright            : (C) 2019 by GIS Support
        email                : info@gis-support.pl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QComboBox, QVBoxLayout, QTableWidgetItem,\
    QDialog, QPushButton, QWidget, QTableWidget, QMessageBox, QApplication
from qgis.gui import QgsEditorWidgetWrapper, QgsEditorWidgetFactory,\
    QgsEditorConfigWidget, QgsEditorWidgetRegistry, QgsGui
from PyQt5.QtCore import Qt
from PyQt5 import uic
from urllib.parse import urlparse
import webbrowser

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
import os.path

def validate_url(url):
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc, parsed.path])
    except:
        return False

class AttachmentControlPlugin():
    def __init__(self, iface):
        self.widget = AttachmentControlWidget('Załącznik (AttachmentControl)')
        QgsGui.editorWidgetRegistry().registerWidget('attachmentcontrolwidget', self.widget)
        iface._WidgetPlugin = self.widget
        self.settings = QSettings()
        self.settings.setValue('AttachmentControl/urls', [])

    def initGui(self):
        pass

    def unload(self):
        self.settings.setValue('AttachmentControl/urls', None)

class AttachmentControlWidget(QgsEditorWidgetFactory):
    def __init__(self, name):
        super(AttachmentControlWidget, self).__init__(name)
        self.wrapper = None
        self.dlg = None

    def create(self, vl, fieldIdx, editor, parent):
        self.wrapper = AttachmentControlWidgetWrapper(vl, fieldIdx, editor, parent)
        return self.wrapper

    def configWidget(self, vl, fieldIdx, parent):
        self.config = AttachmentControlWidgetConfig(vl, fieldIdx, parent)
        return self.config


class AttachmentControlWidgetWrapper(QgsEditorWidgetWrapper):
    def __init__(self, vl, fieldIdx, editor, parent):
        super(AttachmentControlWidgetWrapper, self).__init__(vl, fieldIdx, editor, parent)
        self.editor = editor
        self.parent = parent
        self.wrapperWidget = None
        self.wrapperListWidget = None
        self.wrapperFeature = None
        self.layer = vl

    def valid(self):
        return 1

    def setFeature(self, feature):
        super(AttachmentControlWidgetWrapper, self).setFeature(feature)
        self.wrapperFeature = feature
        self.populateWidget()

    def value(self):
        try:
            return self.wrapperWidget.tableWidget.selectedIndexes()[0].data()
        except IndexError:
            return u'Brak załącznika'
    
    def setValue(self, value):
        pass

    def createWidget(self, parent):
        self.wrapperWidget = AttachmentControlBase()
        return self.wrapperWidget

    def populateWidget(self, editor=None):
        pass

class AttachmentControlBase(QWidget):
    def __init__(self):
        super(AttachmentControlBase, self).__init__()
        ui_path = os.path.join(os.path.dirname(__file__), 'gui/ui_attachmentcontrolpluginbase.ui')
        uic.loadUi(ui_path, self)
        self.dialog = None
        self.btnAdd.clicked.connect(self.initAttachmentDialog)
        self.btnDelete.clicked.connect(self.dialogDeleteUrl)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.itemClicked.connect(self.openUrl)
        self.tableWidget.setHorizontalHeaderLabels(['Adres URL'])
        self.settings = QSettings()
        urls = self.settings.value('AttachmentControl/urls')
        if urls:
            self.loadUrls(urls)

    def initAttachmentDialog(self):
        self.dialog = AttachmentControlAddUrlDialog()
        self.dialog.show()
        self.dialog.btnDialogApply.clicked.connect(self.dialogAddUrl)
        self.dialog.btnDialogDecline.clicked.connect(self.dialog.close)
    
    def dialogAddUrl(self):
        url = self.dialog.lnDialogUrl.text()
        url_item = QTableWidgetItem(self.dialog.lnDialogUrl.text())
        if not validate_url(url):
            self.dialog.close()
            QMessageBox.critical(
                None,
                'Załączniki',
                'Podany adres URL jest niepoprawny'
            )
            return
        current_urls = self.settings.value('AttachmentControl/urls')
        if url in current_urls:
            return
        current_urls.append(url)
        self.settings.setValue('AttachmentControl/urls', current_urls)
        maxRow = self.tableWidget.rowCount()
        self.tableWidget.insertRow(maxRow)
        self.tableWidget.setItem(maxRow, 0, url_item)
        self.dialog.lnDialogUrl.setText('')
        self.tableWidget.resizeColumnsToContents()

    def dialogDeleteUrl(self):
        try:
            selected = self.tableWidget.selectedIndexes()[0].row()
            savedItems = self.settings.value('AttachmentControl/urls')
            savedItems.pop(selected)
            self.settings.setValue('AttachmentControl/urls', savedItems)
            self.tableWidget.removeRow(selected)
        except IndexError:
            QMessageBox.critical(
                None,
                'Załaczniki',
                'Nie wybrano obiektu do usunięcia'
            )
            return

    def openUrl(self, item):
        pressed = QApplication.keyboardModifiers()
        if pressed == Qt.ControlModifier:
            selectedUrl = item.text()
            webbrowser.open(selectedUrl)

    def loadUrls(self, urls):
        maxRow = len(urls)
        self.tableWidget.setRowCount(maxRow)
        for id, url in enumerate(urls):
            item = QTableWidgetItem(url)
            self.tableWidget.setItem(id, 0, item)
        
class AttachmentControlWidgetConfig(QgsEditorConfigWidget):
    def __init__(self, vl, fieldIdx, parent):
        super(AttachmentControlWidgetConfig, self).__init__(vl, fieldIdx, parent)
        ui_path = os.path.join(os.path.dirname(__file__), 'gui/ui_attachmentcontrolpluginconfig.ui')
        uic.loadUi(ui_path, self)

    def config(self):
        return {}

    def setConfig(self, config):
        pass
    
class AttachmentControlAddUrlDialog(QDialog):
    def __init__(self):
        super(AttachmentControlAddUrlDialog, self).__init__()
        ui_path = os.path.join(os.path.dirname(__file__), 'gui/ui_addattachmentdialog.ui')
        uic.loadUi(ui_path, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def close(self):
        self.reject()