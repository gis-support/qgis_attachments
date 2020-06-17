from qgis.PyQt.QtCore import QCoreApplication, QTranslator, qVersion
from qgis.core import QgsSettings
import os

#Stworzenie QTranslatora
directory = os.path.dirname(__file__)

locale = QgsSettings().value('locale/userLocale', 'en')[0:2]
if locale not in ['pl', 'en']:
    #Ręczne ustawianie języka EN w przypadku locale != PL, EN
    locale = 'en'
locale_path = os.path.join(
    directory,
    'i18n',
    'qgis_attachments_{}.qm'.format(locale))

if os.path.exists(locale_path):
    translator = QTranslator()
    translator.load(locale_path)

    if qVersion() > '4.3.3':
        QCoreApplication.installTranslator(translator)

#Funkcja tłumacząca teksty
def translate(context, message):
    return QCoreApplication.translate(context, message)
