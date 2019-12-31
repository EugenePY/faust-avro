from typing import Any, Callable, ClassVar, Dict, Iterable, Optional, cast

import faust
from faust.utils import codegen
from typing_inspect import is_union_type


def faust_annotate(data):
    # Translate from avro's named union records which returns (branch name, value)
    # to faust's {..., "__faust": {"ns": branch name}}.
    try:
        ns, data = data
        return dict(**data, __faust=dict(ns=ns))
    except (TypeError, ValueError):
        return data


class Record(faust.Record, abstract=True):
    _avro_name: ClassVar[str]
    _avro_aliases: ClassVar[Iterable[str]]

    def __init_subclass__(
        cls,
        avro_name: str = None,
        avro_aliases: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        super().__init_subclass__(**kwargs)
        cls._avro_name = avro_name or f"{cls.__module__}.{cls.__name__}"
        cls._avro_aliases = avro_aliases or [cls.__name__]

    # Modify the translation of input fields in order to change
    # from fastavro's schemaless reader's union return ('type', ...)
    # to faust's {..., '__faust'={'ns': 'type'}}
    @classmethod
    def _BUILD_input_translate_fields(cls):
        """Copied and modified from faust's Record._BUILD_input_translate_fields"""
        translate = [
            f"data[{field!r}] = data.pop({d.input_name!r}, None)"
            for field, d in cls._options.descriptors.items()
            if d.field != d.input_name
        ]

        for field, d in cls._options.descriptors.items():
            if is_union_type(d.type):
                translate.append(f"data[{field!r}] = faust_annotate(data[{field!r}])")

        return cast(
            Callable,
            classmethod(
                codegen.Function(
                    "_input_translate_fields",
                    ["cls", "data"],
                    translate if translate else ["pass"],
                    globals=globals(),
                    locals=locals(),
                )
            ),
        )

    @classmethod
    def to_avro(cls, registry) -> Dict[str, Any]:
        from faust_avro.parsers.faust import parse

        avro_schema = parse(registry, cls)
        return avro_schema.to_avro()
