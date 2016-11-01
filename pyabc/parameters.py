from collections import UserDict


class ParameterStructure(UserDict):
    @staticmethod
    def flatten_dict(dict_: dict):
        new_dict = {}
        for key, value in dict_.items():
            if isinstance(value, dict):
                flattened = ParameterStructure.flatten_dict(value)
                for key_flat, value_flat in flattened.items():
                    new_dict.update({str(key) + "." + key_flat: value_flat})
            else:
                new_dict.update({key: value})
        return new_dict

    def __init__(self, *args, **kwargs):
        if len(args) > 0 and len(kwargs) > 0:
            raise Exception("Only keyword or dictionary allowed")
        if len(args) > 0:
            flattened = ParameterStructure.flatten_dict(args[0])
        if len(kwargs) > 0:
            flattened = ParameterStructure.flatten_dict(kwargs)
        if len(args) == 0 and len(kwargs) == 0:
            flattened = {}
        super().__init__(flattened)


class Parameter(ParameterStructure):
    """
    A single model parameter.

    Parameters are essentially a dictionary with the additional functionality
    to add and subtract parameters.

    I.e. ``par_1 + par_2`` adds key wise.

    Contents can be accessed with square brackets or in dot notation.

    For example

    .. code:: python

        >>> p = Parameter(a=1, b=2)
        >>> assert p.a == p["a"]

    or

    .. code:: python

        >>> p = Parameter({"a": 1, "b": 2})
        >>> assert p.a == p["a"]

    """
    def __add__(self, other: "Parameter") -> "Parameter":
        return Parameter(**{key: self[key] + other[key] for key in self})

    def __sub__(self, other: "Parameter") -> "Parameter":
        return Parameter(**{key: self[key] - other[key] for key in self})

    def __repr__(self):
        return "<Parameter " + super().__repr__()[1:-1] + ">"

    def __getattr__(self, item):
        """
        Convenience for dot notation access.
        """
        return self[item]

    def copy(self) -> "Parameter":
        """
        Copy the parameter.
        """
        return Parameter(**self)
