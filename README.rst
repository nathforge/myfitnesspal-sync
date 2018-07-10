DEPRECATED
----------

MyFitnessPal are moving to a new API protocol. This library implements the
original V1 binary protocol - it's unknown how long that API will be supported.

You may have better luck with this V2 library:
https://github.com/coddingtonbear/python-myfitnesspal

mfpsync
=======

MyFitnessPal sync API client. Consists of a program that outputs sync data as a
JSON object, and a Python library for programmatic use.

Command-line::

  $ pip install mfpsync
  $ mfpsync USERNAME PASSWORD
  [
  ...
    {
        "type": "Food",
        "data": {
            "original_master_id": 13599087,
            "is_deleted": false,
            "description": "Oats",
            "nutrients": {
                "calories": 371.0,
                "fat": 8.0,
                "protein": 12.0,
                "carbohydrates": 59.0,
  ...
  ]

Python::

  from mfpsync import Sync

  for packet in Sync(username, password).get_packets():
      print packet
