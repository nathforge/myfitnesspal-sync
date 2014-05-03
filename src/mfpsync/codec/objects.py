import datetime
import uuid

from mfpsync.codec.descriptors import Flag

PACKET_TYPE_SYNC_REQUEST = 1
PACKET_TYPE_SYNC_RESULT = 2
PACKET_TYPE_FOOD = 3
PACKET_TYPE_EXERCISE = 4
PACKET_TYPE_FOOD_ENTRY = 5
PACKET_TYPE_EXERCISE_ENTRY = 6
PACKET_TYPE_CLIENT_FOOD_ENTRY = 7
PACKET_TYPE_CLIENT_EXERCISE_ENTRY = 8
PACKET_TYPE_MEASUREMENT_TYPES = 9
PACKET_TYPE_MEASUREMENT_VALUE = 10
PACKET_TYPE_MEAL_INGREDIENTS = 11
PACKET_TYPE_MASTER_ID_ASSIGNMENT = 12
PACKET_TYPE_USER_PROPERTY_UPDATE = 13
PACKET_TYPE_USER_REGISTRATION = 14
PACKET_TYPE_WATER_ENTRY = 16
PACKET_TYPE_DELETE_ITEM = 17
PACKET_TYPE_SEARCH_REQUEST = 18
PACKET_TYPE_SEARCH_RESPONSE = 19
PACKET_TYPE_FAILED_ITEM_CREATION = 20
PACKET_TYPE_ADD_DELETED_MOST_USED_FOOD = 21
PACKET_TYPE_DIARY_NOTE = 23

class BinaryObject(object):
    """
    Base class for `Codec` encodable objects. `BinaryObject`'s do not have
    a packet header.
    """

    # Tuple of attribute names shown by a `repr` call. `packet_start` and
    # `packet_length` are implicitly added.
    repr_names = None

    def __init__(self):
        self.set_default_values()

    def set_default_values(self):
        """
        Set default attribute values.
        """

    def read_body_from_codec(self, codec):
        """
        Populate the object from a `Codec`.
        """

        raise NotImplementedError

    def write_body_to_codec(self, codec):
        """
        Write the object to a `Codec`. 
        """

        raise NotImplementedError

    def __repr__(self):
        if self.repr_names is None:
            raise NotImplementedError('{} repr_names is unset'.format(
                self.__class__.__name__
            ))

        return self._repr(self.repr_names)

    def _repr(self, names):
        return '<{}({})>'.format(self.__class__.__name__, ', '.join(
            '{}={!r}'.format(name, getattr(self, name))
            for name in self.repr_names
        ))

class BinaryPacket(BinaryObject):
    """
    Base class for `Codec` packets. Sync API requests and responses are a
    series of packets.
    """

    # Magic number, marks the beginning of a packet.
    MAGIC = 0x04D3

    # Packet type number. A packet header lists it's type - `packet_type` is
    # used to associate it with the appropriate `BinaryPacket` subclass.
    packet_type = None

    def __init__(self):
        self.packet_start = None
        self.packet_length = None
        super(BinaryPacket, self).__init__()

    def _repr(self, names):
        return super(BinaryPacket, self)._repr(('packet_start', 'packet_length') + names)

    def write_packet_to_codec(self, codec):
        packet_start = codec.position
        codec.write_2_byte_int(self.MAGIC) # Magic number
        codec.write_4_byte_int(0) # Length placeholder
        codec.write_2_byte_int(1) # Unknown
        codec.write_2_byte_int(self.packet_type) # Packet type
        self.write_body_to_codec(codec)
        with codec.temporary_position(packet_start + 2) as packet_end:
            codec.write_4_byte_int(packet_end - packet_start) # Length

class UnknownPacket(BinaryPacket):
    repr_names = (
        'packet_type',
        'bytes',
    )

    def set_default_values(self):
        self.bytes = ''

    def read_body_from_codec(self, codec):
        self.bytes = codec.read_bytes(self.packet_start - codec.position + self.packet_length)

class SyncRequest(BinaryPacket):
    packet_type = PACKET_TYPE_SYNC_REQUEST

    repr_names = (
        'api_version',
        'svn_revision',
        'unknown1',
        'username',
        'password',
        'flags',
        'installation_uuid',
        'last_sync_pointers'
    )

    def set_default_values(self):
        self.api_version = 6
        self.svn_revision = 237
        self.unknown1 = 2
        self.username = ''
        self.password = ''
        self.flags = 0x5
        self.installation_uuid = uuid.uuid4()
        self.last_sync_pointers = {}

    def read_body_from_codec(self, codec):
        self.api_version = codec.read_2_byte_int()
        self.svn_revision = codec.read_4_byte_int()
        self.unknown1 = codec.read_2_byte_int()
        self.username = codec.read_string()
        self.password = codec.read_string()
        self.flags = codec.read_2_byte_int()
        self.installation_uuid = codec.read_uuid()
        self.last_sync_pointers = codec.read_map(
            codec.read_2_byte_int(),
            codec.read_string, codec.read_string
        )

    def write_body_to_codec(self, codec):
        codec.write_2_byte_int(self.api_version)
        codec.write_4_byte_int(self.svn_revision)
        codec.write_2_byte_int(self.unknown1)
        codec.write_string(self.username)
        codec.write_string(self.password)
        codec.write_2_byte_int(self.flags)
        codec.write_uuid(self.installation_uuid)
        codec.write_2_byte_int(len(self.last_sync_pointers))
        codec.write_map(
            codec.write_string, codec.write_string,
            self.last_sync_pointers
        )

class SyncResult(BinaryPacket):
    packet_type = PACKET_TYPE_SYNC_RESULT

    repr_names = (
        'status_code',
        'status_message',
        'error_message',
        'optional_extra_message',
        'master_id',
        'flags',
        'expected_packet_count',
        'last_sync_pointers',
        'more_data_to_sync',
        'upgrade_available',
        'upgrade_alert',
        'upgrade_url'
    )

    status_messages = {
        0: 'ok',
        1: 'invalid_registration',
        2: 'authentication_failed',
        None: 'unknown'
    }

    more_data_to_sync = Flag('flags', 0x1)
    upgrade_available = Flag('flags', 0x2)

    def set_default_values(self):
        self.status_code = 0
        self.error_message = ''
        self.optional_extra_message = ''
        self.master_id = 0
        self.flags = 0
        self.expected_packet_count = 0
        self.last_sync_pointers = {}

    @property
    def status_message(self):
        return self.status_messages.get(self.status_code, self.status_messages[None])

    @status_message.setter
    def status_message(self, value):
        if value is None or value not in self.status_messages:
            raise ValueError('Unknown status message {}'.format(value))

        self.status_code = next(
            status_code
            for status_code, status_message
            in self.status_messages
            if status_message == value
        )

    @property
    def upgrade_alert(self):
        return self.optional_extra_message.partition('|')[0]

    @upgrade_alert.setter
    def upgrade_alert(self, value):
        self.optional_extra_message = '|'.join(value, self.upgrade_url or '')

    @property
    def upgrade_url(self):
        return self.optional_extra_message.partition('|')[2]

    @upgrade_url.setter
    def upgrade_url(self, value):
        self.optional_extra_message = '|'.join(self.upgrade_alert or '', value)

    def read_body_from_codec(self, codec):
        self.status_code = codec.read_2_byte_int()
        self.error_message = codec.read_string()
        self.optional_extra_message = codec.read_string()
        self.master_id = codec.read_4_byte_int()
        self.flags = codec.read_2_byte_int()
        last_sync_pointer_count = codec.read_2_byte_int()
        self.expected_packet_count = codec.read_4_byte_int()
        self.last_sync_pointers = codec.read_map(
            last_sync_pointer_count,
            codec.read_string, codec.read_string
        )

class Food(BinaryPacket):
    packet_type = PACKET_TYPE_FOOD

    repr_names = (
        'master_food_id',
        'owner_user_master_id',
        'original_master_id',
        'description',
        'brand',
        'flags',
        'is_public',
        'is_deleted',
        'nutrients',
        'grams',
        'type',
        'is_meal',
        'portions'
    )

    nutrient_names = (
        'calories',
        'fat',
        'saturated_fat',
        'polyunsaturated_fat',
        'monounsaturated_fat',
        'trans_fat',
        'cholesterol',
        'sodium',
        'potassium',
        'carbohydrates',
        'fiber',
        'sugar',
        'protein',
        'vitamin_a',
        'vitamin_c',
        'calcium',
        'iron'
    )

    is_public = Flag('flags', 0x1)
    is_deleted = Flag('flags', 0x2)

    @property
    def is_meal(self):
        return self.type == 1

    @is_meal.setter
    def is_meal(self, value):
        if value:
            self.type = 1
        else:
            self.type = 0

    def set_default_values(self):
        self.master_food_id = 0
        self.owner_user_master_id = 0
        self.original_master_id = 0
        self.description = ''
        self.brand = ''
        self.flags = 0
        self.nutrients = {}
        self.grams = 0
        self.type = 0
        self.portions = []

    def read_body_from_codec(self, codec):
        self.master_food_id = codec.read_4_byte_int()
        self.owner_user_master_id = codec.read_4_byte_int()
        self.original_master_id = codec.read_4_byte_int()
        self.description = codec.read_string()
        self.brand = codec.read_string()
        self.flags = codec.read_4_byte_int()

        self.nutrients = {}
        for nutrient in self.nutrient_names:
            value = codec.read_float()
            self.nutrients[nutrient] = value

        self.grams = codec.read_float()
        self.type = codec.read_2_byte_int()

        portion_count = codec.read_2_byte_int()
        self.portions = []
        for _ in xrange(portion_count):
            food_portion = FoodPortion()
            food_portion.read_body_from_codec(codec)
            self.portions.append(food_portion)

class Exercise(BinaryPacket):
    packet_type = PACKET_TYPE_EXERCISE

    repr_names = (
        'master_exercise_id',
        'owner_user_master_id',
        'original_master_exercise_id',
        'exercise_type',
        'description',
        'flags',
        'is_public',
        'is_deleted',
        'mets',
    )

    is_public = Flag('flags', 0x1)
    is_deleted = Flag('flags', 0x2)

    def set_default_values(self):
        self.master_exercise_id = 0
        self.owner_user_master_id = 0
        self.original_master_exercise_id = 0
        self.exercise_type = 0
        self.description = ''
        self.flags = 0
        self.mets = 0

    def read_body_from_codec(self, codec):
        self.master_exercise_id = codec.read_4_byte_int()
        self.owner_user_master_id = codec.read_4_byte_int()
        self.original_master_exercise_id = codec.read_4_byte_int()
        self.exercise_type = codec.read_2_byte_int()
        self.description = codec.read_string()
        self.flags = codec.read_4_byte_int()
        self.mets = codec.read_float()

class FoodEntry(BinaryPacket):
    packet_type = PACKET_TYPE_FOOD_ENTRY

    repr_names = (
        'master_food_id',
        'food',
        'date',
        'meal_name',
        'quantity',
        'weight_index'
    )

    def set_default_values(self):
        self.master_food_id = 0
        self.food = Food()
        self.date = datetime.date.today()
        self.meal_name = ''
        self.quantity = 0
        self.weight_index = 0

    def read_body_from_codec(self, codec):
        self.master_food_id = codec.read_8_byte_int()
        self.food = Food()
        self.food.read_body_from_codec(codec)
        self.date = codec.read_date()
        self.meal_name = codec.read_string()
        self.quantity = codec.read_float()
        self.weight_index = codec.read_4_byte_int()

    @property
    def portion(self):
        return self.food.portions[self.weight_index]

    @property
    def nutrients(self):
        multiplier = (self.quantity * self.portion.gram_weight) / self.food.grams
        return {
            key: value * multiplier if value is not None else None
            for key, value in self.food.nutrients.iteritems()
        }

class ExerciseEntry(BinaryPacket):
    packet_type = PACKET_TYPE_EXERCISE_ENTRY

    repr_names = (
        'master_exercise_id',
        'exercise',
        'date',
        'quantity',
        'sets',
        'weight',
        'calories',
    )

    def set_default_values(self):
        self.master_exercise_id = 0
        self.exercise = Exercise()
        self.date = datetime.date.today()
        self.quantity = 0
        self.sets = 0
        self.weight = 0
        self.calories = 0

    def read_body_from_codec(self, codec):
        self.master_exercise_entry_id = codec.read_8_byte_int()
        self.exercise = Exercise()
        self.exercise.read_body_from_codec(codec)
        self.date = codec.read_date()
        self.quantity = codec.read_4_byte_int()
        self.sets = codec.read_4_byte_int()
        self.weight = codec.read_4_byte_int()
        self.calories = codec.read_4_byte_int()

class ClientFoodEntry(BinaryPacket):
    packet_type = PACKET_TYPE_CLIENT_FOOD_ENTRY

class ClientExerciseEntry(BinaryPacket):
    packet_type = PACKET_TYPE_CLIENT_EXERCISE_ENTRY

class MeasurementTypes(BinaryPacket):
    packet_type = PACKET_TYPE_MEASUREMENT_TYPES

    repr_names = (
        'descriptions',
    )

    def set_default_values(self):
        self.descriptions = {}

    def read_body_from_codec(self, codec):
        self.descriptions = codec.read_map(
            codec.read_2_byte_int(),
            codec.read_4_byte_int, codec.read_string
        )

class MeasurementValue(BinaryPacket):
    packet_type = PACKET_TYPE_MEASUREMENT_VALUE

    repr_names = (
        'master_measurement_id',
        'type_name',
        'entry_date',
        'value',
    )

    def set_default_values(self):
        self.master_measurement_id = 0
        self.type_name = ''
        self.entry_date = datetime.date.today()
        self.value = 0

    def read_body_from_codec(self, codec):
        self.master_measurement_id = codec.read_8_byte_int()
        self.type_name = codec.read_string()
        self.entry_date = codec.read_date()
        self.value = codec.read_float()

class MealIngredients(BinaryPacket):
    packet_type = PACKET_TYPE_MEAL_INGREDIENTS

    repr_names = (
        'ingredients',
    )

    def set_default_values(self):
        self.ingredients = []

    def read_body_from_codec(self, codec):
        self.master_food_id = codec.read_4_byte_int()
        ingredient_count = codec.read_4_byte_int()
        self.ingredients = []
        for _ in xrange(ingredient_count):
            ingredient = MealIngredient()
            ingredient.read_body_from_codec(codec)
            self.ingredients.append(ingredient)

class MasterIdAssignment(BinaryPacket):
    packet_type = PACKET_TYPE_MASTER_ID_ASSIGNMENT

class UserPropertyUpdate(BinaryPacket):
    packet_type = PACKET_TYPE_USER_PROPERTY_UPDATE

    repr_names = (
        'properties',
    )

    def set_default_values(self):
        self.properties = {}

    def read_body_from_codec(self, codec):
        self.properties = codec.read_map(
            codec.read_2_byte_int(), codec.read_string, codec.read_string
        )

class UserRegistration(BinaryPacket):
    packet_type = PACKET_TYPE_USER_REGISTRATION

class WaterEntry(BinaryPacket):
    packet_type = PACKET_TYPE_WATER_ENTRY

class DeleteItem(BinaryPacket):
    packet_type = PACKET_TYPE_DELETE_ITEM

    repr_names = (
        'item_type',
        'master_id',
        'status',
        'is_destroyed'
    )

    @property
    def is_destroyed(self):
        return self.status == 2

    @is_destroyed.setter
    def is_destroyed(self, value):
        self.status = 2 if value else 0

    def set_default_values(self):
        self.item_type = 0
        self.master_id = 0
        self.status = 0

    def read_body_from_codec(self, codec):
        self.item_type = codec.read_2_byte_int()
        self.master_id = codec.read_8_byte_int()
        self.status = codec.read_2_byte_int()

class SearchRequest(BinaryPacket):
    packet_type = PACKET_TYPE_SEARCH_REQUEST

class SearchResponse(BinaryPacket):
    packet_type = PACKET_TYPE_SEARCH_RESPONSE

class FailedItemCreation(BinaryPacket):
    packet_type = PACKET_TYPE_FAILED_ITEM_CREATION

class AddDeletedMostUsedFood(BinaryPacket):
    packet_type = PACKET_TYPE_ADD_DELETED_MOST_USED_FOOD

class DiaryNote(BinaryPacket):
    packet_type = PACKET_TYPE_DIARY_NOTE

class FoodPortion(BinaryObject):
    repr_names = (
        'amount',
        'gram_weight',
        'description',
        'fraction_int',
        'is_fraction'
    )

    @property
    def is_fraction(self):
        return self.fraction_int != 0

    @is_fraction.setter
    def is_fraction(self, value):
        self.fraction_int = 1 if value else 0

    def set_default_values(self):
        self.amount = 0
        self.gram_weight = 0
        self.description = ''
        self.is_fraction = 0

    def read_body_from_codec(self, codec):
        self.amount = codec.read_float()
        self.gram_weight = codec.read_float()
        self.description = codec.read_string()
        self.fraction_int = codec.read_2_byte_int()

class MealIngredient(BinaryObject):
    repr_names = (
        'master_ingredient_id',
        'master_food_id',
        'fraction_int',
        'is_fraction',
        'quantity',
        'weight_index',
    )

    @property
    def is_fraction(self):
        return self.fraction_int > 0

    @is_fraction.setter
    def is_fraction(self, value):
        self.fraction_int = 1 if value else 0

    def set_default_values(self):
        self.master_ingredient_id = 0
        self.master_food_id = 0
        self.fraction_int = 0
        self.quantity = 0
        self.weight_index = 0

    def read_body_from_codec(self, codec):
        self.master_ingredient_id = codec.read_4_byte_int()
        self.master_food_id = codec.read_4_byte_int()
        self.fraction_int = codec.read_4_byte_int()
        self.quantity = codec.read_float()
        self.weight_index = codec.read_2_byte_int()
