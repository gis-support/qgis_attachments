# coding: utf-8

from pathlib import Path
from qgis.core import QgsApplication
from qgis.gui import QgsEditorWidgetWrapper
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import QMessageBox, QFrame, QHBoxLayout
from qgis_attachments.backends.registry import backends_registry

class AttachmentControlWidgetWrapper(QgsEditorWidgetWrapper):
    """ Kontrolka formularza """

    def __init__(self, vl, fieldIdx, editor, parent):
        super(AttachmentControlWidgetWrapper, self).__init__(vl, fieldIdx, editor, parent)
        self.widget = None

    def valid(self):
        """ Czy właściwa kontrolka została zainicjowana """
        return bool(self.widget)
    
    def createWidget(self, parent):
        """ Stworzenie kontrolki """
        ui_path = Path(__file__).parent.joinpath('widget.ui')
        self.widget = uic.loadUi(str(ui_path))
        if self.isInTable(parent):
            #Wyśwetlenie kontrolki w tabeli atrybutów
            # https://www.qgis.org/api/qgskeyvaluewidgetwrapper_8cpp_source.html#l00036
            frame = QFrame(parent)
            self.widget.setParent(frame)
            frame.setFrameShape( QFrame.StyledPanel )
            layout = QHBoxLayout( frame )
            layout.addWidget( self.widget )
            frame.setMinimumSize( QSize( 320, 200 ) )
            return frame
        #Kontrolka w formularzu
        self.widget.setParent(parent)
        return self.widget
    
    def initWidget(self, editor):
        """ Konfiguracja kontrolki """
        #Pobranie aktualnego sterownika
        backend_name = self.config()['backend']
        self.backend = backends_registry.backends[backend_name]
        #Ikony przycisków
        self.widget.btnAdd.setIcon( QgsApplication.getThemeIcon('/mActionAdd.svg') )
        self.widget.btnDelete.setIcon( QgsApplication.getThemeIcon('/mActionRemove.svg') )
        #Sygnały
        self.widget.btnAdd.clicked.connect( self.addAttachment )
        self.widget.btnDelete.clicked.connect( self.deleteAttachment  )
        #Model listy załączników
        self.widget.tblAttachments.setModel( self.backend.model )
        self.backend.setOptions( self.widget.tblAttachments )
    
    def setEnabled(self, enabled):
        """ Ustawienie aktywności elementów formularza w zależności od trybu edycji """
        self.widget.btnAdd.setEnabled( enabled )
        self.widget.btnDelete.setEnabled( enabled )
    
    def value(self):
        """ Lista załączników jako tekst """
        return self.backend.value()
    
    def setValue(self, attribute):
        """ Tekst na listę załączników """
        self.backend.setValue( attribute )
    
    def addAttachment(self):
        """ Dodanie załącznika """
        self.backend.addAttachment(self)
        self.emitValueChanged()
    
    def deleteAttachment(self):
        """ Usunięcie załącznika """
        result = QMessageBox.question(self.widget, 'Usuwanie', 'Usunąć wybranny załącznik z listy?')
        if result == QMessageBox.No:
            return
        self.backend.deleteAttachment(self)
        self.emitValueChanged()