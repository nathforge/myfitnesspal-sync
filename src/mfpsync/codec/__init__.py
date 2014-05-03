import contextlib
import datetime
import struct
import uuid

from mfpsync.codec import objects

class Codec(object):
    """
    Encodes and decodes MyFitnessPal binary objects.
    """

    def __init__(self, fp):
        """
        Configures class to read from or write to the given file object `fp`.
        """

        self.fp = fp

        # Initialise the `expected_packet_count` and `packet_count` members.
        # `expected_packet_count` is initialised after seeing a `SyncResult`
        # packet. The `packet_count` is incremented for every non-`SyncResult`
        # packet, and checked at the end of the file to see that it matches
        # `expected_packet_count`. If there is no `SyncResult` packet, this
        # check will be disabled - however, this is not expected behaviour.
        self.expected_packet_count = None
        self.packet_count = 0

        # Set `packet_type_classes` to a dict mapping of `packet_type`s to
        # `BinaryPacket` subclasses.
        self.packet_type_classes = {
            packet_class.packet_type: packet_class
            for packet_class in (
                objects.SyncRequest,
                objects.SyncResult,
                objects.Food,
                objects.Exercise,
                objects.FoodEntry,
                objects.ExerciseEntry,
                objects.ClientFoodEntry,
                objects.ClientExerciseEntry,
                objects.MeasurementTypes,
                objects.MeasurementValue,
                objects.MealIngredients,
                objects.MasterIdAssignment,
                objects.UserPropertyUpdate,
                objects.UserRegistration,
                objects.WaterEntry,
                objects.DeleteItem,
                objects.SearchRequest,
                objects.SearchResponse,
                objects.FailedItemCreation,
                objects.AddDeletedMostUsedFood,
                objects.DiaryNote
            )
        }

    def __iter__(self):
        return self.read_packets()

    @property
    def position(self):
        """
        Return the current position within `self.fp`.
        """

        return self.fp.tell()

    @position.setter
    def position(self, value):
        """
        Set a new position within `self.fp`.
        """

        self.fp.seek(value)

    @contextlib.contextmanager
    def temporary_position(self, new_position):
        """
        Context manager that temporarilys set `self.position`, returning the
        previous position.

        Example:
            >>> with codec.temporary_position(codec.position + 100) as prev_position:
            ...     print 'Was as position {}. Now temporarily at position {}'.format(
            ...         prev_position, codec.position
            ...     )
            >>> print 'Returned to prev position {}'.format(codec.position)
        """

        prev_position = self.position
        self.position = new_position
        yield prev_position
        self.position = prev_position

    def read_bytes(self, byte_count):
        """
        Return `byte_count` bytes from `self.fp`, throwing an `EOFError` if
        there are not enough bytes remaining.
        """

        bytes = self.fp.read(byte_count)
        if len(bytes) < byte_count:
            raise EOFError
        return bytes

    def read_2_byte_int(self):
        """
        Return a decoded 2-byte big-endian integer.
        """

        return struct.unpack('>h', self.read_bytes(2))[0]

    def read_4_byte_int(self):
        """
        Return a decoded 4-byte big-endian integer.
        """

        return struct.unpack('>l', self.read_bytes(4))[0]

    def read_8_byte_int(self):
        """
        Return a decoded 8-byte big-endian integer.
        """

        return struct.unpack('>q', self.read_bytes(8))[0]

    def read_float(self):
        """
        Return a IEEE 754 binary32-decoded big-endian float.
        """

        return struct.unpack('>f', self.read_bytes(4))[0]

    def read_string(self):
        """
        Return a decoded string.
        """

        string_length = self.read_2_byte_int()
        encoded_string = self.read_bytes(string_length)
        decoded_string = encoded_string.decode('utf8')
        return decoded_string

    def read_uuid(self):
        """
        Return a decoded `uuid.UUID` object.
        """

        return uuid.UUID(bytes=self.read_bytes(16))

    def read_date(self):
        """
        Return a decoded `datetime.date` object.
        """

        date_string = self.read_bytes(10)
        date = datetime.datetime.strptime(date_string, '%Y-%m-%d').date()
        return date

    def read_timestamp(self):
        """
        Return a decoded `datetime.datetime` object.
        """

        timestamp_string = self.read_bytes(19)
        timestamp = datetime.datetime.strptime(timestamp_string, '%Y-%m-%d %H:%M:%S')
        return timestamp

    def read_map(self, item_count, read_key, read_value):
        """
        Return a decoded map object. `item_count` indicates the number of
        items, `read_key` and `read_value` are functions that decode keys and
        values.

        Example:
            >>> code.read_map(item_count,
            ...     read_key=codec.read_2_byte_int,
            ...     read_value=codec.read_string
            ... )

        Map objects are *sometimes* preceded by an `item_count` field, but not
        always.
        """

        items = {}
        for _ in xrange(item_count):
            key = read_key()
            value = read_value()
            items[key] = value

        return items

    def read_packet_header(self):
        """
        Return a decoded packet header. Throws a `ValueError` if the first two
        bytes don't match the expect `BinaryPacket.MAGIC` value.
        """

        magic_number = self.read_2_byte_int()
        length = self.read_4_byte_int()
        unknown1 = self.read_2_byte_int()
        packet_type = self.read_2_byte_int()

        if magic_number != objects.BinaryPacket.MAGIC:
            raise ValueError('Unexpected magic {:X}'.format(magic_number))

        return {
            'magic_number': magic_number,
            'length': length,
            'unknown1': unknown1,
            'type': packet_type
        }

    def read_packets(self):
        """
        Return an iterator yielding `BinaryPacket`-subclassed objects.
        """

        while True:
            packet_start = self.position
            try:
                yield self.read_packet()
            except EOFError:
                if self.position == packet_start:
                    break

        if self.expected_packet_count is not None:
            if self.packet_count != self.expected_packet_count:
                raise Exception('Expected {} objects, received {}'.format(
                    self.expected_packet_count, self.packet_count
                ))

    def read_packet(self):
        """
        Return the next decoded packet.
        """

        # Record the start position of the packet.
        packet_start = self.position

        # Read the packet header.
        packet_header = self.read_packet_header()
        packet_length = packet_header['length']
        packet_type = packet_header['type']

        # Calculate the expected end position of this packet. This will be
        # checked after decoding the packet.
        expected_packet_end = packet_start + packet_length

        # Decode the packet body.
        packet = None
        try:
            if packet_type in self.packet_type_classes:
                packet = self.packet_type_classes[packet_type]()
                packet.packet_start = packet_start
                packet.packet_length = packet_length
                packet.read_body_from_codec(self)
            else:
                raise NotImplementedError
        except NotImplementedError:
            # `packet_type` is either not registered in
            # `self.packet_type_classes`, or the `BinaryPacket` subclass raised
            # a `NotImplementedError` when calling `read_body_from_codec()`.
            # Fallback to `UnknownPacket`, an object that preserves the raw
            # packet bytes, but doesn't attempt to process them.
            packet = objects.UnknownPacket()
            packet.packet_type = packet_type
            packet.packet_start = packet_start
            packet.packet_length = packet_length
            packet.read_body_from_codec(self)

        # If this is a `SyncResult`, we have an `expected_packet_count`.
        # Record this, so we can check it at the end of the file.
        # If not, increment `packet_count` - `SyncResult` packets are not
        # included in the count.
        if isinstance(packet, objects.SyncResult):
            self.expected_packet_count = packet.expected_packet_count
        else:
            self.packet_count += 1

        # Has `BinaryPacket.read_body_from_codec` left us at the expected
        # position?
        if self.position != expected_packet_end:
            raise Exception(
                'Packet read finished at position {}, but expected to be at position {}'.format(
                    self.position, expected_packet_end
                )
            )

        return packet

    def write_2_byte_int(self, value):
        """
        Write an encoded big-endian 2-byte int.
        """

        self.fp.write(struct.pack('>h', value))

    def write_4_byte_int(self, value):
        """
        Write an encoded big-endian 4-byte int.
        """

        self.fp.write(struct.pack('>l', value))

    def write_8_byte_int(self, value):
        """
        Write an encoded big-endian 8-byte int.
        """

        self.fp.write(struct.pack('>q', value))

    def write_float(self, value):
        """
        Write an IEEE 754 binary32-encoded big-endian float.
        """

        self.fp.write(struct.pack('>f', value))

    def write_string(self, value):
        """
        Write an encoded string.
        """

        encoded_string = value.encode('utf8')
        self.write_2_byte_int(len(encoded_string))
        self.fp.write(encoded_string)

    def write_uuid(self, value):
        """
        Write an encoded `uuid.UUID` object.
        """

        self.fp.write(value.get_bytes())

    def write_date(self, value):
        """
        Write an encoded `datetime.date` object.
        """

        self.fp.write(value.strftime('%Y-%m-%d %H:%M:%S'))

    def write_timestamp(self, value):
        """
        Write an encoded `datetime.datetime` object.
        """

        self.fp.write(value.strftime(''))

    def write_map(self, write_key, write_value, items):
        """
        Write an encoded map object. `write_key` and `write_value` are functions
        that encode keys and values, `items` is a `dict` object.

        Example:
            >>> code.read_map(item_count,
            ...     read_key=codec.read_2_byte_int,
            ...     read_value=codec.read_string
            ... )

        The item count is written as a separate field - the location of this
        depends on the packet type.
        """

        for key, value in items.iteritems():
            write_key(key)
            write_value(value)
