from collections import OrderedDict
import argparse
import datetime
import json

from mfpsync import Sync
from mfpsync.codec.objects import BinaryObject

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username', nargs=1)
    parser.add_argument('password', nargs=1)

    args = parser.parse_args()

    sync = Sync(args.username[0], args.password[0])
    print json.dumps(list(sync.get_packets()), cls=JSONEncoder, indent=4)

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
