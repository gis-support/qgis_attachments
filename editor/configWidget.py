# coding: utf-8

from qgis.gui import QgsEditorConfigWidget
import os
from qgis.PyQt import uic
from qgis_attachments.backends.registry import backends_registry

class AttachmentControlWidgetConfig(QgsEditorConfigWidget):
    """ Kontrolka ustawień """

    def __init__(self, vl, fieldIdx, parent):
        super(AttachmentControlWidgetConfig, self).__init__(vl, fieldIdx, parent)
        #Utworzenie kontrolki
        self.widget = None
        self.currentBackend = None
        ui_path = os.path.join(os.path.dirname(__file__), 'configWidget.ui')
        uic.loadUi(ui_path, self)
        for index, backend in enumerate(backends_registry.backends.values()):
            self.cmbBackends.addItem( backend.LABEL, backend.NAME )
            self.cmbBackends.model().item(index).setEnabled( backend.isSupported(vl) )
        self.cmbBackends.currentIndexChanged.connect( self.setBackend )
        self.setBackend( self.cmbBackends.currentIndex() )
    
    def setBackend(self, index):
        """ Zmiana sterownika dla załączników """
        if self.widget is not None:
            self.layout().removeWidget( self.widget )
            self.widget.deleteLater()
        name = self.cmbBackends.itemData( index )
        self.currentBackend = backends_registry.getBackendInstance( name, self )
        self.setDescription()
        self.widget = self.currentBackend.createConfigWidget()
        if self.widget:
            self.layout().addWidget( self.widget )
    
    def setDescription(self):
        """ Opis sterownika """
        texts = [self.currentBackend.DESCRIPTION]
        texts.extend( self.currentBackend.warnings(self.layer(), self.field()) )
        self.lblDescription.setText( '\n'.join(texts) )

    def config(self):
        """ Zapis ustawień ogólnych i sterownika """
        return {'backend':self.cmbBackends.currentData(),
                **self.currentBackend.config(),
            'label': self.cmbBackends.currentText()
        }

    def setConfig(self, config):
        """ Odczyt ustawień """
        label = config.get('label')
        if not label:
            return
        self.cmbBackends.setCurrentText(label)
        self.currentBackend.setConfig(config)