# coding: utf-8

from pathlib import Path
from qgis.PyQt import uic
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.db.model import ProjectModel

class FilesBackend(BackendAbstract):

    LABEL = 'Projekt'
    DESCRIPTION = 'Przechowuje załączniki z projektem QGIS.'

    def createConfigWidget(self):
        ui_path = Path(__file__).parent.joinpath('config.ui')
        self.widget = uic.loadUi(str(ui_path))
        return self.widget
    
    def addAttachment(self):
        print( 'Project add' )
    
    def deleteAttachment(self):
        print( 'Project remove' )
