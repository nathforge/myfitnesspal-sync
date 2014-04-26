import random
import string

class HttpRequestParams(object):
    """
    Given a encoded sync API request, construct headers and a POST body.
    """

    url = 'https://www.myfitnesspal.com/iphone_api/synchronize'
    user_agent = 'Dalvik/1.6.0 (Linux; U; Android 4.4.2; sdk Build/KK)'

    def __init__(self, data):
        """
        Set `self.body` and `self.headers` for an encoded sync API request.
        """

        mime_boundary = ''.join(
            random.choice(string.ascii_lowercase)
            for _ in xrange(78)
        )

        self.body = self._get_body(mime_boundary, data)
        self.headers = self._get_headers(mime_boundary, self.body)

    def _get_body(self, mime_boundary, data):
        """
        Return the POST body for a `mime_boundary` and `data`.
        """

        return (
            '--{mime_boundary}\r\n'
            'Content-Disposition: form-data; name="syncdata"; filename="syncdata.dat"\r\n'
            'Content-Type: application/octet-stream\r\n'
            '\r\n'
            '{data}'
            '\r\n'
            '--{mime_boundary}--\r\n'
        ).format(
            mime_boundary=mime_boundary,
            data=data
        )

    def _get_headers(self, mime_boundary, body):
        """
        Return the HTTP request headers for a `mime_boundary` and POST body.
        """

        return {
            'User-Agent': self.user_agent,
            'Content-Type': 'multipart/form-data; boundary={}'.format(mime_boundary),
            'Content-Length': len(body)
        }
