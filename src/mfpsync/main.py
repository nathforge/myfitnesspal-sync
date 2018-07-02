from collections import OrderedDict
import argparse
import datetime
import json
import os.path

from mfpsync import Sync
from mfpsync.codec.objects import BinaryObject, SyncResult

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('-P', '--pointers-filename', required=False)

    args = parser.parse_args()

    last_sync_pointers = {}
    if args.pointers_filename:
        try:
            with open(args.pointers_filename) as fp:
                last_sync_pointers = json.load(fp)
        except IOError:
            if os.path.isfile(args.pointers_filename):
                raise

    sync = Sync(args.username, args.password)
    packets = AllPackets(sync, last_sync_pointers)
    print json.dumps(list(packets), cls=JSONEncoder, indent=4)

    if args.pointers_filename:
        with open(args.pointers_filename, "w") as fp:
            json.dump(packets.last_sync_pointers, fp)

class AllPackets(object):
    def __init__(self, sync, last_sync_pointers={}):
        self.sync = sync
        self.last_sync_pointers = last_sync_pointers

    def __iter__(self):
        while True:
            data_packet_count = 0
            for packet in self.sync.get_packets(last_sync_pointers=self.last_sync_pointers):
                if isinstance(packet, SyncResult):
                    self.last_sync_pointers = packet.last_sync_pointers
                else:
                    data_packet_count += 1

                yield packet

            if data_packet_count == 0:
                break

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BinaryObject):
            return OrderedDict((
                ('type', obj.__class__.__name__),
                ('data', {
                    name: getattr(obj, name)
                    for name in obj.repr_names
                })
            ))

        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')

        return super(JSONEncoder, self).default(obj)

if __name__ == '__main__':
    main()
