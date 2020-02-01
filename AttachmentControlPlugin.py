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
from qgis.PyQt.QtCore import QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QComboBox, QVBoxLayout, QTableWidgetItem,\
    QDialog, QPushButton, QWidget, QTableWidget, QMessageBox, QApplication, QFileDialog
from qgis.gui import QgsEditorWidgetWrapper, QgsEditorWidgetFactory,\
    QgsEditorConfigWidget, QgsEditorWidgetRegistry, QgsGui
from qgis.core import NULL
from PyQt5.QtCore import Qt
from PyQt5 import uic
from urllib.parse import urlparse
import webbrowser

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
import os.path

def validate_url(url):
    return True
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

    def initGui(self):
        pass

    def unload(self):
        pass

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
        #self.parent = parent
        self.wrapperWidget = None
        self.wrapperListWidget = None
        self.wrapperFeature = None
        #self.layer = vl

    def valid(self):
        return 1

    def setFeature(self, feature):
        super(AttachmentControlWidgetWrapper, self).setFeature(feature)
        self.wrapperFeature = feature

    def value(self):
        values = []
        table = self.wrapperWidget.tableWidget
        for row in range(table.rowCount()):
            values.append( table.item(row, 0).text() )
        if values:
            return ';'.join( values )
        return NULL
    
    def setValue(self, attribute):
        table = self.wrapperWidget.tableWidget
        table.clearContents()
        if not attribute:
            values = []
        else:
            values = attribute.split(';')
        table.setRowCount( len(values) )
        for row, value in enumerate(values):
            table.setItem( row, 0, QTableWidgetItem(value) )
            

    def createWidget(self, parent):
        self.wrapperWidget = AttachmentControlBase()
        return self.wrapperWidget
'''
    def populateWidget(self, editor=None):
        pass
'''

class AttachmentControlBase(QWidget):
    def __init__(self):
        super(AttachmentControlBase, self).__init__()
        ui_path = os.path.join(os.path.dirname(__file__), 'gui/ui_attachmentcontrolpluginbase.ui')
        uic.loadUi(ui_path, self)
        self.dialog = None
        self.fileDialog = None
        self.btnAdd.clicked.connect(self.initAttachmentDialog)
        self.btnDelete.clicked.connect(self.dialogDeleteUrl)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.itemClicked.connect(self.openUrl)
        self.tableWidget.setHorizontalHeaderLabels(['Załącznik'])

    def initAttachmentDialog(self):
        self.dialog = AttachmentControlAddUrlDialog(self)
        self.fileDialog = QFileDialog(self.dialog)
        self.dialog.show()
        self.dialog.btnDialogApply.clicked.connect(self.dialogAddUrl)
        self.dialog.btnDialogFile.clicked.connect(self.dialogAddFilePath)
        self.fileDialog.fileSelected.connect(self.dialogAddUrl)
    
    def dialogAddUrl(self, file=None):
        if not file:
            new_item = QTableWidgetItem(self.dialog.lnDialogUrl.text())
            new_item.setData(Qt.UserRole, 'url')
        else:
            new_item = QTableWidgetItem(file.replace('\\', '/'))
            new_item.setData(Qt.UserRole, 'file')
            self.dialog.setVisible(True)
        if not new_item or len(new_item.text()) == 0:
            return
        for index in range(0, self.tableWidget.rowCount()):
            item = self.tableWidget.item(index, 0).text()
            if item == new_item.text():
                return
        maxRow = self.tableWidget.rowCount()
        self.tableWidget.insertRow(maxRow)
        self.tableWidget.setItem(maxRow, 0, new_item)
        self.dialog.lnDialogUrl.setText('')
        self.tableWidget.resizeColumnsToContents()

    def dialogDeleteUrl(self):
        try:
            selected = self.tableWidget.selectedIndexes()[0].row()
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
            if item.data(Qt.UserRole) == 'url':
                selectedAttachment = item.text()
                webbrowser.open(selectedAttachment)
            else:
                selectedPath = item.text()
                last_slash_index = selectedPath.rfind('/')
                webbrowser.open(selectedPath[:last_slash_index])

    def dialogAddFilePath(self):
        self.dialog.setVisible(False)
        self.fileDialog.show()
        
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
    def __init__(self, parent):
        super(AttachmentControlAddUrlDialog, self).__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), 'gui/ui_addattachmentdialog.ui')
        uic.loadUi(ui_path, self)
        self.parent = parent
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)

    def close(self):
        self.reject()