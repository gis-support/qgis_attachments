from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import Qt, QUrl, QDir, QSettings
from qgis.PyQt.QtGui import QDesktopServices
from qgis_attachments.backends.base.baseBackend import BackendAbstract
from qgis_attachments.backends.base.baseModel import AttachmentsAbstractModel
from qgis_attachments.backends.base.baseDelegates import OptionButton
from qgis_attachments.backends.qgis_cloud.model import CloudAttachmentItem
from qgis_attachments.backends.qgis_cloud.buffer import CloudBuffer
from qgis_attachments.backends.qgis_cloud.cloud_driver import CloudDriver
from qgis_attachments.backends.utils import saveFile
from qgis_attachments.translator import translate
from qgis.core import QgsApplication, NULL
from qgis.utils import iface
from qgis.PyQt import uic
from pathlib import Path
import tempfile
import os

translate_ = lambda msg: translate('CloudBackend', msg)

class CloudBackend(BackendAbstract):

    LABEL = 'GIS Support Cloud'
    NAME = 'cloud'
    DESCRIPTION = 'Przechowuje załączniki w GIS Support Cloud'

    def __init__(self, parent):
        super(CloudBackend, self).__init__([
            OptionButton(QgsApplication.getThemeIcon('/mActionFileNew.svg'),
                lambda index, option='saveTemp': self.fileAction(index, option)
            ),
            OptionButton(QgsApplication.getThemeIcon('/mActionSharingExport.svg'),
                lambda index, option='saveToDir': self.fileAction(index, option)
            ),
        ], parent=parent)
        self.model = AttachmentsAbstractModel(
                columns=[translate_('Opcje'), translate_('Pliki')],
                separator=self.SEPARATOR,
                ItemClass=CloudAttachmentItem
        )
        buffer.backend = self
        buffer.config = self.parent.config()
        buffer.registerLayer( self.parent.layer() )

    #Konfiguracja
    def createConfigWidget(self):
        """ Utworzenie kontrolki z kofiguracją """
        ui_path = Path(__file__).parent.joinpath('config.ui')
        self.configWidget = uic.loadUi(str(ui_path))
        return self.configWidget

    def config(self):
        """Zapis ustawień konfiguracji"""
        url = self.configWidget.lnAddress.text().strip()
        data = {
            'user': self.configWidget.lnLogin.text(),
            'password': self.configWidget.lnPassword.text()
        }
        if url:
            data.update({'api_url': url if url.endswith('/') else url + '/'})
        buffer.config = data
        #Odświeżenie tokena w przypadku zmiany danych logowania
        self.getApiToken(data=data, refresh=True, show_message=False)
        return data

    def setConfig(self, config):
        """Odczyt ustawień i dostosowanie GUI"""
        self.configWidget.lnAddress.setText(config.get('api_url'))
        self.configWidget.lnLogin.setText(config.get('user'))
        self.configWidget.lnPassword.setText(config.get('password'))
        buffer.config = self.parent.config()

    def getApiToken(self, data={}, refresh=False, show_message=True):
        """Pobiera token z Cloud i zapisuje informacje o danych połączenia"""
        config = self.parent.config() if not data else data
        token = QSettings().value(f'{config.get("api_url")}_token', None)

        if not token or refresh:
            auth_output = CloudDriver.authenticate(config)
            if not buffer.config:
                buffer.config = config
            if 'error' not in auth_output:
                QSettings().setValue(f'{config.get("api_url")}_token', auth_output)
            else:
                if show_message:
                    iface.messageBar().pushCritical(translate_('Błąd'), auth_output['error'])
                QSettings().setValue(f'{config.get("api_url")}_token', None)
                return None

        return QSettings().value(f'{config.get("api_url")}_token', None)

    def isTokenValid(self):
        """Sprawdza ważność tokena poprzez zapytanie do API"""
        config = self.parent.config()
        token = self.getApiToken()
        if CloudDriver.checkToken(config, token):
            return True
        else:
            token = self.getApiToken(refresh=True)

        if CloudDriver.checkToken(config, token):
            return True
        else:
            self.parent.bar.pushCritical(translate_('Błąd'), translate_('Podczas próby odświeżenia tokena Cloud wystąpił błąd. Sprawdź poprawność danych połączenia'))   
            return False

    #Formularz
    def setValue(self, value):
        """Parsowanie tekstu do listy załączników"""
        #Wyczyszczenie listy załączników
        self.model.clear()
        if value == NULL:
            return
        token = self.getApiToken()
        cloud_ids = value.split( self.SEPARATOR )
        if token:
            #Wypełnienie lisy załączników
            if '-1' not in cloud_ids:
                values = CloudDriver.fetchAttachmentsMetadata(self.parent.config()['api_url'], cloud_ids, token)
                if values is None:
                    #Token wygasł
                    token = self.getApiToken(refresh=True)
                    if not token:
                        self.model.insertRows([[cid, translate_('Załącznik niedostępny')] for cid in cloud_ids], max_length=self.parent.field().length())
                        return
                    values = CloudDriver.fetchAttachmentsMetadata(self.parent.config()['api_url'], cloud_ids, token)
                layer = self.parent.layer()
                feature = self.getFeature()
                self.model.insertRows(values)
                #Dodane i niezapisane załączniki
                items = buffer.added[layer.id()][self.parent.fieldIdx()][feature.id()]
                self.model.insertRows( items, max_length=self.parent.field().length())
            else:
                #Załączniki dodane, ale nie wysłane do Cloud
                self.model.insertRows( [[cloud_id, translate_('Załącznik niedostępny')] for cloud_id in cloud_ids], max_length=self.parent.field().length())
        else:
            self.model.insertRows([[cid, translate_('Załącznik niedostępny')] for cid in cloud_ids], max_length=self.parent.field().length())

    def addAttachment(self):
        """Dodaje załącznik"""
        if self.isTokenValid():
            self.parent.widget.setFocus()
            files, _ = QFileDialog.getOpenFileNames(self.parent.widget, 'Wybierz załączniki')

            feature = self.getFeature()
            #Nowy załącznik, niezapisane załączniki mają id -1
            items = [ ['-1', f] for f in files ]
            buffer.added[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()].extend( items )
            result = self.model.insertRows( items, max_length=self.parent.field().length())

            return result

    def deleteAttachment(self):
        """Usuwa załącznik"""
        #Pobranie i ewentulane odświeżenie tokena
        if self.isTokenValid():
            selected = self.parent.widget.tblAttachments.selectedIndexes()
            index = selected[0]
            if len(selected) < 1:
                return
            index = selected[0]
            item = self.model.data(index, Qt.UserRole)
            item.to_delete = True
            self.parent.widget.tblAttachments.model().dataChanged.emit( index, index )
            cloud_id = item.cloud_id
            self.model.removeRow(index.row())
            feature = self.getFeature()
            buffer.deleted[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()].append( cloud_id )
            added = buffer.added[self.parent.layer().id()][self.parent.fieldIdx()][feature.id()]
            #Sprawdzenie czy usunięty załącznik nie znajduje się na liście dodawanych załączników
            item_to_delete = [cloud_id, item.value]
            if item_to_delete in added:
                added.pop(added.index(item_to_delete))
            return True

    def fileAction(self, index, option):
        """Zapisuje plik do katalogu tymczasowego lub wskazanego przez użytkownika"""
        if self.isTokenValid():
            item = self.model.data(index, Qt.UserRole)
            if item.cloud_id == '-1':
                self.parent.bar.pushWarning(
                    translate_('Uwaga'),
                    translate_('Plik zapisać można po załadowaniu go do Cloud. Nastąpi to po zakończeniu lub zapisaniu edycji.')
                )
                return
            file_name, file_data = CloudDriver.fetchAttachments(self.parent.config()['api_url'], [item.cloud_id], token)
            if file_name is None or file_data is None:
                return
            save_dir = ''
            if option == 'saveTemp':
                path = tempfile.gettempdir()
                out_path = saveFile(path, file_data, file_name)
                QDesktopServices.openUrl(QUrl(f'file:///{QDir.toNativeSeparators(out_path)}'))
            elif option == 'saveToDir':
                self.parent.widget.setFocus()
                path, _ = QFileDialog.getSaveFileName(directory=file_name)
                out_path = saveFile(path, file_data)
                if out_path:
                    self.parent.bar.pushSuccess(
                        translate_('Sukces'),
                        '{} {}'.format(
                            translate_('Pomyślnie wyeksportowano plik'),
                            file_name
                        )
                    )

    def downloadAll(self):
        """Pobiera załącznik lub załączniki spakowane w archiwum dla danego obiektu"""
        if self.isTokenValid():
            ids = []
            for row in range(0, self.model.rowCount()):
                index = self.model.index(row, 0, self.parent.widget.tblAttachments.rootIndex())
                cloud_id = self.model.data(index, Qt.UserRole).cloud_id
                if cloud_id == '-1':
                    self.parent.bar.pushWarning(
                        translate_('Uwaga'),
                        translate_('Paczkę z załącznikami można zapisać po ich załadowaniu do Cloud. Nastąpi to po zakończeniu lub zapisaniu edycji.')
                    )
                    return
                ids.append(cloud_id)
            if len(ids) > 1:
                file_name = f'{self.parent.layer().name()}_{self.getFeature().id()}.zip'
                path, _ = QFileDialog.getSaveFileName(directory=file_name)
                attachments_data = CloudDriver.fetchAttachments(self.parent.config()['api_url'], ids, token)
            elif ids:
                file_name, attachments_data = CloudDriver.fetchAttachments(self.parent.config()['api_url'], ids, token)
                path, _ = QFileDialog.getSaveFileName(directory=file_name)
            else:
                self.parent.bar.pushWarning(
                    translate_('Uwaga'),
                    translate_('Brak załączników do pobrania')
                )
                return
            if path:
                saveFile(path, attachments_data)
                iface.messageBar().pushSuccess(translate_('Sukces'), 'Pomyślnie zapisano załączniki')

    #Ustawienia
    @staticmethod
    def isSupported(layer):
        if layer.providerType() == 'postgres':
            for field in layer.fields():
                if field.name() == '__attachments':
                    return True
        return False

#Stworzenie instancji bufora edycyjnego załączników
buffer = CloudBuffer(CloudBackend.SEPARATOR)