from collections import OrderedDict
import argparse
import datetime
import json
import os.path
import sys

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
    sys.stdout.write("[")
    first_packet = True
    for packet in packets:
        sys.stdout.write(
            ("\n" if first_packet else ",\n") + indent(
                json.dumps(packet, cls=JSONEncoder, indent=4),
                "    "
            )
        )
        first_packet = False
    sys.stdout.write("\n]")

    if args.pointers_filename:
        with open(args.pointers_filename, "w") as fp:
            json.dump(packets.last_sync_pointers, fp)

def indent(string, prefix):
    return "\n".join(
        prefix + line
        for line in string.split("\n")
    )

class AllPackets(object):
    def __init__(self, sync, last_sync_pointers={}):
        self.sync = sync
        self.last_sync_pointers = last_sync_pointers

    def __iter__(self):
        while True:
            sync_result = None
            for packet in self.sync.get_packets(last_sync_pointers=self.last_sync_pointers):
                if isinstance(packet, SyncResult):
                    sync_result = packet
                yield packet

            self.last_sync_pointers = sync_result.last_sync_pointers
            if not sync_result.more_data_to_sync:
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
