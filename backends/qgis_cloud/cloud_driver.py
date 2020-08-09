from qgis.PyQt.QtCore import QEventLoop, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager
from base64 import b64encode
from pathlib import Path
from io import BytesIO
import json

class CloudDriver:

    ATTACHMENTS_ROUTE = '/api/attachments_qgis'
    LOGIN_ROUTE = '/api/login'

    @classmethod
    def authenticate(cls, api_data):
        url = api_data.get('api_url', '')
        request_data = {'user': api_data.get('user'), 'password': api_data.get('password')}
        response = cls._sendRequest(url + cls.LOGIN_ROUTE, data=request_data, method='post', get_token=True)
        try:
            response_data = json.loads(response.readAll().data().decode())
        except:
            return {'error': 'Podczas autentykacji wystąpił błąd'}
        if 'token' in response_data:
            return response_data['token']
        else:
            return {'error': 'Niepoprawne dane logowania'}

    @classmethod
    def fetchAttachmentsMetadata(cls, route, ids, token, name_only=False):
        response = cls._sendRequest(route + f'{cls.ATTACHMENTS_ROUTE}/metadata?ids={",".join(ids)}&', token=token)
        response_decoded = response.readAll().data().decode()
        if 'invalid token' in response_decoded:
            return None
        response_data = json.loads(response_decoded)['data']
        if name_only:
            return response_data[0]['file_name']
        return [[str(obj['id']), obj['file_name']] for obj in response_data]

    @classmethod
    def fetchAttachments(cls, route, ids, token):
        response = cls._sendRequest(route + f'{cls.ATTACHMENTS_ROUTE}/files?ids={",".join(ids)}&', token=token)
        response_data = response.readAll().data()
        count = len(ids)
        if not response_data:
            response_data = response.readAll()
        if count == 1:
            file_name = cls.fetchAttachmentsMetadata(route, ids, token, name_only=True)
            return file_name, response_data
        else:
            return response_data
            
    @classmethod
    def uploadAttachments(cls, route, token, attachments):
        request_data = {'data': []}

        for attachment in attachments:
            file_path = Path(attachment)
            content = file_path.read_bytes()
            request_data['data'].append({
                'content': b64encode(content).decode(),
                'name': file_path.parts[-1]
            })

        response = cls._sendRequest(route + cls.ATTACHMENTS_ROUTE, method='post', data=json.dumps(request_data), token=token)
        response_decoded = response.readAll().data().decode()
        if 'invalid token' in response_decoded:
            return None
        response_data = json.loads(response_decoded)['data']
        ids = [added['attachment_id'] for added in response_data]
        return ids

    @classmethod
    def deleteAttachments(cls, route, token, attachments_ids):
        ids = ','.join(attachments_ids)
        response_data = cls._sendRequest(route + f'{cls.ATTACHMENTS_ROUTE}?ids={ids}&', method='delete', token=token)
        return None if 'invalid token' in response_data.readAll().data().decode() else response_data

    @staticmethod
    def _sendRequest(route, method='get', data=None, token=None, get_token=False):
        """Wysyła zapytanie do API"""
        manager = QgsNetworkAccessManager.instance()

        if get_token:
            #Logowanie
            data = json.dumps({'user': data['user'], 'password': data['password']})
        else:
            route += '{}token={}'.format('?' if not route.endswith('&') else '', token)
        request = QNetworkRequest(QUrl(route))

        if method == 'get':
            response = manager.get(request)
        elif method == 'post':
            response = manager.post(request, data.encode())
            request.setHeader(QNetworkRequest.ContentTypeHeader, 'application/json')
        elif method == 'delete':
            response = manager.deleteResource(request)

        loop = QEventLoop()
        response.finished.connect(loop.exit)
        loop.exec_()
        return response

