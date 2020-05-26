# coding: utf-8

from pathlib import Path
from qgis.core import QgsApplication
from qgis.gui import QgsEditorWidgetWrapper, QgsMessageBar
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import (QMessageBox, QFrame, QVBoxLayout,
    QSizePolicy, QPushButton, QSpacerItem, QHBoxLayout)
from qgis_attachments.backends.registry import backends_registry

class AttachmentControlWidgetWrapper(QgsEditorWidgetWrapper):
    """ Kontrolka formularza """

    def __init__(self, vl, fieldIdx, editor, parent):
        super(AttachmentControlWidgetWrapper, self).__init__(vl, fieldIdx, editor, parent)
        self.widget = None

    def getBackendLabel(self):
        """Pobiera label obecnego backendu"""
        return self.backend.LABEL if self.backend else ''


    def valid(self):
        """ Czy właściwa kontrolka została zainicjowana """
        return bool(self.widget)
    
    def createWidget(self, parent):
        """ Stworzenie kontrolki """
        ui_path = Path(__file__).parent.joinpath('widget.ui')
        self.widget = uic.loadUi(str(ui_path))
        #Pomocniczy obiekt do wyświetlania komunikatów
        self.bar = QgsMessageBar()
        self.bar.setSizePolicy( QSizePolicy.Minimum, QSizePolicy.Fixed )
        self.widget.layout().insertWidget( 0, self.bar )
        if self.isInTable(parent):
            #Wyśwetlenie kontrolki w tabeli atrybutów
            # https://www.qgis.org/api/qgskeyvaluewidgetwrapper_8cpp_source.html#l00036
            frame = QFrame(parent)
            self.widget.setParent(frame)
            frame.setFrameShape( QFrame.StyledPanel )
            frame.setMinimumSize( QSize( 320, 200 ) )
            formLayout = QVBoxLayout( frame )
            formLayout.addWidget( self.widget )
            
            #Dodatkowy przycisk Zamknij
            btn_layout = QHBoxLayout()
            spacer = QSpacerItem(40, 5, QSizePolicy.Expanding, QSizePolicy.Minimum)
            btn_layout.addItem( spacer )
            btnClose = QPushButton('Zamknij', frame)
            btnClose.clicked.connect( frame.close )
            btn_layout.addWidget( btnClose )
            formLayout.addLayout( btn_layout )
            return frame
        else:
            #Kontrolka w formularzu
            self.widget.setParent(parent)
        return self.widget
    
    def initWidget(self, editor):
        """ Konfiguracja kontrolki """
        #Pobranie aktualnego sterownika
        backend_name = self.config()['backend']
        self.backend = backends_registry.getBackendInstance( backend_name, self )
        #Ikony przycisków
        self.widget.btnAdd.setIcon( QgsApplication.getThemeIcon('/mActionAdd.svg') )
        self.widget.btnDelete.setIcon( QgsApplication.getThemeIcon('/mActionRemove.svg') )
        #Sygnały
        self.widget.btnAdd.clicked.connect( self.addAttachment )
        self.widget.btnDelete.clicked.connect( self.deleteAttachment  )
        #Model listy załączników
        self.widget.tblAttachments.setModel( self.backend.model )
        self.backend.setOptions()
    
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
        result = self.backend.addAttachment()
        if result:
            self.emitValueChanged()
    
    def deleteAttachment(self):
        """ Usunięcie załącznika """
        selected = self.widget.tblAttachments.selectedIndexes()
        if len(selected) < 1:
            self.bar.pushWarning(
                'Uwaga',
                'Nie wybrano obiektów do usunięcia'
            )
            return
        result = self.backend.deleteAttachment()
        if result:
            self.emitValueChanged()