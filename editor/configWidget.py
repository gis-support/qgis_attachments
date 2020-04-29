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
        for backend_name in backends_registry.backends:
            self.cmbBackends.addItem( backend_name )
        self.cmbBackends.currentTextChanged.connect( self.setBackend )
        self.setBackend( self.cmbBackends.currentText() )
    
    def setBackend(self, name):
        """ Zmiana sterownika dla załączników """
        if self.widget is not None:
            self.layout().removeWidget( self.widget )
            self.widget.deleteLater()
        self.currentBackend = backends_registry.backends[name]
        self.widget = self.currentBackend.createConfigWidget()
        self.lblDescription.setText( self.currentBackend.DESCRIPTION )
        self.layout().addWidget( self.widget )

    def config(self):
        """ Zapis ustawień ogólnych i sterownika """
        return {'backend':self.cmbBackends.currentText(), **self.currentBackend.config()}

    def setConfig(self, config):
        """ Odczyt ustawień """
        backend = config.get('backend')
        if not backend:
            return
        self.cmbBackends.setCurrentText(backend)
        self.currentBackend.setConfig(config)