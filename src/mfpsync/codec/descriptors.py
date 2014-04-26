class Flag(object):
    """
    Descriptor to get and set binary flags for an integer attribute.

    Example:
        >>> class Test(object):
        ...     flags = 0
        ...     x_is_enabled = Flag('flags', 0x1)
        ...     y_is_enabled = Flag('flags', 0x2)
        ...     z_is_enabled = Flag('flags', 0x4)
        ...
        >>> test = Test()
        ...
        >>> test.x_is_enabled = True
        >>> test.flags
        1
        >>> test.x_is_enabled = False; test.y_is_enabled = True
        >>> test.flags
        2
        >>> test.y_is_enabled = True; test.z_is_enabled = True
        >>> test.flags
        6
    """

    def __init__(self, base_attr, bitmask):
        """
        Create the descriptor. `base_attr` is the name of an integer attribute
        that represents binary flags. `bitmask` is the binary value to toggle
        on `base_attr`.
        """

        self.base_attr = base_attr
        self.bitmask = bitmask

    def __get__(self, obj, type=None):
        """
        Returns a boolean indicating whether `bitmask` is enabled within the
        base attribute.
        """

        return bool(getattr(obj, self.base_attr) & self.bitmask)

    def __set__(self, obj, enabled):
        """
        Sets or clears `bitmask` within the base attribute.
        """

        value = getattr(obj, self.base_attr)
        if enabled:
            value |= self.bitmask
        else:
            value &= ~self.bitmask
        setattr(obj, self.base_attr, value)
