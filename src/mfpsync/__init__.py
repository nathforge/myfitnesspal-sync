import cStringIO
import shutil
import urllib2
import uuid

from mfpsync.codec import Codec
from mfpsync.codec.objects import SyncRequest
from mfpsync.http import HttpRequestParams

class Sync(object):
    """
    Sync API client.

    Example:
        >>> for packet in Sync(username, password).get_packets():
        ...     print packet

    To aid debugging, `save_response_fp` can be set. This will save the
    response data before further processing. This data can be passed to a
    `Codec` object for offline testing. Example:

        >>> sync = Sync(username, password)
        >>> with open('/tmp/response', 'wb') as sync.save_response_fp:
        ...     for packet in sync.get_packets():
        ...         print packet
    """

    # If set, responses will be saved to this file object before processing.
    # Useful for debugging.
    save_response_fp = None

    def __init__(self, username, password, installation_uuid=None):
        """
        Create a `Sync` object for the given user. Optionally takes an
        `installation_uuid` - this is a `uuid.UUID` object that identifies
        a phone installation. If omitted, a random UUID will be provided.
        """

        self.username = username
        self.password = password
        self.installation_uuid = installation_uuid or uuid.uuid4()

    def get_packets(self, last_sync_pointers={}):
        """
        Returns an iterator yielding decoded packets from the sync API.

        If given an optional `last_sync_pointers` as returned in the
        `SyncResultPacket` of a previous sync call, a partial sync will be
        performed. Otherwise, all data will be returned.
        """

        # Write a `SyncRequest` packet to `request_data_fp`.
        request_data_fp = cStringIO.StringIO()
        encoder = Codec(request_data_fp)
        sync_request = SyncRequest()
        sync_request.username = self.username
        sync_request.password = self.password
        sync_request.installation_uuid = self.installation_uuid
        sync_request.last_sync_pointers = last_sync_pointers
        sync_request.write_packet_to_codec(encoder)

        # Create `HttpRequestParams` from the encoded `SyncRequest`.
        http_request_params = HttpRequestParams(request_data_fp.getvalue())

        # Call the API.
        response_code, response_headers, response_data_fp = self.post_http(
            http_request_params.url, http_request_params.headers, http_request_params.body
        )

        # Create a StringIO from the response data, as `Codec` requires a
        # `tell()` method.
        response_data_fp = cStringIO.StringIO(response_data_fp.read())

        # If requested, save this response to `self.save_response_fp` before
        # processing.
        if self.save_response_fp:
            shutil.copyfileobj(response_data_fp, self.save_response_fp)
            response_data_fp.seek(0)

        # Yield decoded packets.
        decoder = Codec(response_data_fp)
        for packet in decoder.read_packets():
            yield packet

    def post_http(self, url, headers, body):
        """
        Given a URL, HTTP headers and a POST body, return the HTTP status code,
        response headers, and the response body as a file object.
        """

        request = urllib2.Request(url)

        for key, value in headers.iteritems():
            request.add_header(key, value)

        request.add_data(body)

        response = urllib2.urlopen(request)

        return response.getcode(), response.headers, response

if __name__ == '__main__':
    """
    When called from the command-line, takes a MyFitnessPal username and
    password, and dumps the sync API response as a Python representation.
    """

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')

    args = parser.parse_args()

    for packet in Sync(args.username, args.password).get_packets():
        print packet
