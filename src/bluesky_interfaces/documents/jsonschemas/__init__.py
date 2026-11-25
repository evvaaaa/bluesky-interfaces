"""Compose and validate documents against the bundled JSON schemas."""

import itertools
import json
import os
import time as ttime
import uuid
import warnings
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

try:
    import jsonschema
except ModuleNotFoundError as exc:
    if exc.name != "jsonschema":
        raise
    raise ModuleNotFoundError(
        "JSON Schema support requires jsonschema. "
        "Install it with 'pip install bluesky-interfaces[jsonschema]'.",
        name="jsonschema",
    ) from exc

from bluesky_interfaces.documents.document_names import DocumentNames
from bluesky_interfaces.documents.typed_dicts import (
    Datum,
    DatumPage,
    Event,
    EventDescriptor,
    EventPage,
    Resource,
    RunStart,
    RunStop,
    StreamDatum,
    StreamResource,
)
from bluesky_interfaces.documents.typed_dicts.event_descriptor import (
    Configuration,
    DataKey,
    PerObjectHint,
)
from bluesky_interfaces.documents.typed_dicts.stream_datum import StreamRange

_SCHEMA_NAMES = {
    DocumentNames.start: "run_start.json",
    DocumentNames.stop: "run_stop.json",
    DocumentNames.event: "event.json",
    DocumentNames.event_page: "event_page.json",
    DocumentNames.descriptor: "event_descriptor.json",
    DocumentNames.datum: "datum.json",
    DocumentNames.datum_page: "datum_page.json",
    DocumentNames.resource: "resource.json",
    DocumentNames.stream_datum: "stream_datum.json",
    DocumentNames.stream_resource: "stream_resource.json",
    DocumentNames.bulk_datum: "bulk_datum.json",
    DocumentNames.bulk_events: "bulk_events.json",
}
schemas = {}
for name, filename in _SCHEMA_NAMES.items():
    ref = Path(__file__).parent / filename
    with ref.open() as f:
        schemas[name] = json.load(f)


__all__ = [
    "ComposeDatum",
    "ComposeDatumPage",
    "ComposeDescriptor",
    "ComposeDescriptorBundle",
    "ComposeEvent",
    "ComposeEventPage",
    "ComposeResource",
    "ComposeResourceBundle",
    "ComposeRunBundle",
    "ComposeStop",
    "ComposeStreamDatum",
    "ComposeStreamResource",
    "ComposeStreamResourceBundle",
    "EventModelError",
    "EventModelValidationError",
    "compose_datum",
    "compose_datum_page",
    "compose_descriptor",
    "compose_event",
    "compose_event_page",
    "compose_resource",
    "compose_run",
    "compose_stop",
    "compose_stream_datum",
    "compose_stream_resource",
    "schema_validators",
    "schemas",
]


class EventModelError(Exception): ...


class EventModelValidationError(EventModelError): ...


def _is_array(checker, instance):
    return (
        jsonschema.validators.Draft202012Validator.TYPE_CHECKER.is_type(
            instance, "array"
        )
        or isinstance(instance, tuple)
        or hasattr(instance, "__array__")
    )


_array_type_checker = jsonschema.validators.Draft202012Validator.TYPE_CHECKER.redefine(
    "array", _is_array
)

_Validator = jsonschema.validators.extend(
    jsonschema.validators.Draft202012Validator, type_checker=_array_type_checker
)

schema_validators = {
    name: _Validator(schema=schema) for name, schema in schemas.items()
}


@dataclass
class ComposeDatum:
    resource: Resource
    counter: Iterator

    def __call__(self, datum_kwargs: dict[str, Any], validate: bool = True) -> Datum:
        resource_uid = self.resource["uid"]
        doc = Datum(
            resource=resource_uid,
            datum_kwargs=datum_kwargs,
            datum_id=f"{resource_uid}/{next(self.counter)}",
        )
        if validate:
            schema_validators[DocumentNames.datum].validate(doc)
        return doc


def compose_datum(
    *,
    resource: Resource,
    counter: Iterator,
    datum_kwargs: dict[str, Any],
    validate: bool = True,
) -> Datum:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeDatum(resource, counter)(datum_kwargs, validate=validate)


@dataclass
class ComposeDatumPage:
    resource: Resource
    counter: Iterator

    def __call__(self, datum_kwargs: dict, validate: bool = True) -> DatumPage:
        resource_uid = self.resource["uid"]
        any_column, *_ = datum_kwargs.values()
        count = len(any_column)
        doc = DatumPage(
            resource=resource_uid,
            datum_kwargs=datum_kwargs,
            datum_id=[f"{resource_uid}/{next(self.counter)}" for _ in range(count)],
        )
        if validate:
            schema_validators[DocumentNames.datum_page].validate(doc)
        return doc


def compose_datum_page(
    *,
    resource: Resource,
    counter: Iterator,
    datum_kwargs: dict[str, list[Any]],
    validate: bool = True,
) -> DatumPage:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeDatumPage(resource, counter)(datum_kwargs, validate=validate)


@dataclass
class ComposeResourceBundle:
    resource_doc: Resource
    compose_datum: ComposeDatum
    compose_datum_page: ComposeDatumPage

    # iter for backwards compatibility
    def __iter__(self) -> Iterator:
        return iter(
            (
                self.resource_doc,
                self.compose_datum,
                self.compose_datum_page,
            )
        )


PATH_SEMANTICS: dict[str, Literal["posix", "windows"]] = {
    "posix": "posix",
    "nt": "windows",
}
default_path_semantics: Literal["posix", "windows"] = PATH_SEMANTICS[os.name]


@dataclass
class ComposeResource:
    start: RunStart | None

    def __call__(
        self,
        spec: str,
        root: str,
        resource_path: str,
        resource_kwargs: dict[str, Any],
        path_semantics: Literal["posix", "windows"] = default_path_semantics,
        uid: str | None = None,
        validate: bool = True,
    ) -> ComposeResourceBundle:
        if uid is None:
            uid = str(uuid.uuid4())

        doc = Resource(
            path_semantics=path_semantics,
            uid=uid,
            spec=spec,
            root=root,
            resource_kwargs=resource_kwargs,
            resource_path=resource_path,
        )

        if self.start:
            doc["run_start"] = self.start["uid"]

        if validate:
            schema_validators[DocumentNames.resource].validate(doc)

        counter = itertools.count()
        return ComposeResourceBundle(
            doc,
            ComposeDatum(resource=doc, counter=counter),
            ComposeDatumPage(resource=doc, counter=counter),
        )


def compose_resource(
    *,
    spec: str,
    root: str,
    resource_path: str,
    resource_kwargs: dict[str, Any],
    path_semantics: Literal["posix", "windows"] = default_path_semantics,
    start: RunStart | None = None,
    uid: str | None = None,
    validate: bool = True,
) -> ComposeResourceBundle:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeResource(start)(
        spec,
        root,
        resource_path,
        resource_kwargs,
        path_semantics=path_semantics,
        uid=uid,
        validate=validate,
    )


@dataclass
class ComposeStreamDatum:
    stream_resource: StreamResource
    counter: Iterator

    def __call__(
        self,
        indices: StreamRange,
        seq_nums: StreamRange | None = None,
        descriptor: EventDescriptor | None = None,
        validate: bool = True,
    ) -> StreamDatum:
        resource_uid = self.stream_resource["uid"]

        # If the seq_nums aren't passed in then the bluesky
        # bundler will keep track of them
        if not seq_nums:
            seq_nums = StreamRange(start=0, stop=0)

        doc = StreamDatum(
            stream_resource=resource_uid,
            uid=f"{resource_uid}/{next(self.counter)}",
            seq_nums=seq_nums,
            indices=indices,
            descriptor=descriptor["uid"] if descriptor else "",
        )

        if validate:
            schema_validators[DocumentNames.stream_datum].validate(doc)

        return doc


def compose_stream_datum(
    *,
    stream_resource: StreamResource,
    counter: Iterator,
    seq_nums: StreamRange,
    indices: StreamRange,
    validate: bool = True,
) -> StreamDatum:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    warnings.warn(
        "compose_stream_datum() will be removed in the minor version.",
        DeprecationWarning,
        stacklevel=2,
    )
    return ComposeStreamDatum(stream_resource, counter)(
        indices,
        seq_nums,
        validate=validate,
    )


@dataclass
class ComposeStreamResourceBundle:
    stream_resource_doc: StreamResource
    compose_stream_datum: ComposeStreamDatum

    # iter for backwards compatibility
    def __iter__(self) -> Iterator:
        return iter(
            (
                self.stream_resource_doc,
                self.compose_stream_datum,
            )
        )


@dataclass
class ComposeStreamResource:
    start: RunStart | None = None

    def __call__(
        self,
        mimetype: str,
        uri: str,
        data_key: str,
        parameters: dict[str, Any],
        uid: str | None = None,
        validate: bool = True,
    ) -> ComposeStreamResourceBundle:
        if uid is None:
            uid = str(uuid.uuid4())

        doc = StreamResource(
            uid=uid,
            data_key=data_key,
            mimetype=mimetype,
            uri=uri,
            parameters=parameters,
        )

        if self.start:
            doc["run_start"] = self.start["uid"]

        if validate:
            schema_validators[DocumentNames.stream_resource].validate(doc)

        return ComposeStreamResourceBundle(
            doc,
            ComposeStreamDatum(
                stream_resource=doc,
                counter=itertools.count(),
            ),
        )


def compose_stream_resource(
    *,
    mimetype: str,
    uri: str,
    data_key: str,
    parameters: dict[str, Any],
    start: RunStart | None = None,
    uid: str | None = None,
    validate: bool = True,
) -> ComposeStreamResourceBundle:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeStreamResource(start=start)(
        mimetype,
        uri,
        data_key,
        parameters,
        uid=uid,
        validate=validate,
    )


@dataclass
class ComposeStop:
    start: RunStart
    event_counters: dict[str, int]
    poison_pill: list

    def __call__(
        self,
        exit_status: Literal["success", "abort", "fail"] = "success",
        reason: str = "",
        uid: str | None = None,
        time: float | None = None,
        validate: bool = True,
    ) -> RunStop:
        if self.poison_pill:
            raise EventModelError(
                "Already composed a RunStop document for run {!r}.".format(
                    self.start["uid"]
                )
            )
        self.poison_pill.append(object())
        if uid is None:
            uid = str(uuid.uuid4())
        if time is None:
            time = ttime.time()
        doc = RunStop(
            uid=uid,
            time=time,
            run_start=self.start["uid"],
            exit_status=exit_status,
            reason=reason,
            num_events={k: v - 1 for k, v in self.event_counters.items()},
        )
        if validate:
            schema_validators[DocumentNames.stop].validate(doc)
        return doc


def compose_stop(
    *,
    start: RunStart,
    event_counters: dict[str, int],
    poison_pill: list,
    exit_status: Literal["success", "abort", "fail"] = "success",
    reason: str = "",
    uid: str | None = None,
    time: float | None = None,
    validate: bool = True,
) -> RunStop:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeStop(
        start=start,
        event_counters=event_counters,
        poison_pill=poison_pill,
    )(exit_status=exit_status, reason=reason, uid=uid, time=time, validate=validate)


def _length_of_value(dictionary: dict[str, list], error_msg: str) -> int | None:
    length = None
    for _, v in dictionary.items():
        v_len = len(v)
        if length is not None:
            if v_len != length:
                raise EventModelError(error_msg)
        length = v_len
    return length


@dataclass
class ComposeEventPage:
    descriptor: EventDescriptor
    event_counters: dict[str, int]

    def __call__(
        self,
        data: dict[str, list],
        timestamps: dict[str, Any],
        seq_num: list[int] | None = None,
        filled: dict[str, list[bool | str]] | None = None,
        uid: list | None = None,
        time: list | None = None,
        validate: bool = True,
    ) -> EventPage:
        timestamps_length = _length_of_value(
            timestamps,
            "Cannot compose event_page: event_page contains `timestamps` "
            "list values of different lengths",
        )
        data_length = _length_of_value(
            data,
            "Cannot compose event_page: event_page contains `data` "
            "lists of different lengths",
        )
        assert timestamps_length == data_length, (
            "Cannot compose event_page: the lists in `timestamps` are of a different "
            "length to those in `data`"
        )

        if seq_num is None:
            last_seq_num = self.event_counters[self.descriptor["name"]]
            seq_num = list(
                range(last_seq_num, len(next(iter(data.values()))) + last_seq_num)
            )
        count = len(seq_num)
        if uid is None:
            uid = [str(uuid.uuid4()) for _ in range(count)]
        if time is None:
            time = [ttime.time()] * count
        if filled is None:
            filled = {}
        doc = EventPage(
            uid=uid,
            time=time,
            data=data,
            timestamps=timestamps,
            seq_num=seq_num,
            filled=filled,
            descriptor=self.descriptor["uid"],
        )
        if validate:
            schema_validators[DocumentNames.event_page].validate(doc)

            if not (
                set(
                    _keys_without_stream_keys(
                        self.descriptor["data_keys"], self.descriptor["data_keys"]
                    )
                )
                == set(_keys_without_stream_keys(data, self.descriptor["data_keys"]))
                == set(
                    _keys_without_stream_keys(timestamps, self.descriptor["data_keys"])
                )
            ):
                raise EventModelValidationError(
                    'These sets of keys must match (other than "STREAM:" keys):\n'
                    "event['data'].keys(): {}\n"
                    "event['timestamps'].keys(): {}\n"
                    "descriptor['data_keys'].keys(): {}\n".format(
                        data.keys(),
                        timestamps.keys(),
                        self.descriptor["data_keys"].keys(),
                    )
                )
            if set(filled) - set(data):
                raise EventModelValidationError(
                    f"Keys in event['filled'] {filled.keys()} "
                    "must be a subset of those in "
                    f"event['data'] {data.keys()}"
                )
        self.event_counters[self.descriptor["name"]] += len(seq_num)
        return doc


def compose_event_page(
    *,
    descriptor: EventDescriptor,
    event_counters: dict[str, int],
    data: dict[str, list],
    timestamps: dict[str, Any],
    seq_num: list[int],
    filled: dict[str, list[bool | str]] | None = None,
    uid: list | None = None,
    time: list | None = None,
    validate: bool = True,
) -> EventPage:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeEventPage(descriptor, event_counters)(
        data,
        timestamps,
        seq_num=seq_num,
        filled=filled,
        uid=uid,
        time=time,
        validate=validate,
    )


def _keys_without_stream_keys(dictionary, descriptor_data_keys):
    return [
        key
        for key in dictionary.keys()
        if (
            "external" not in descriptor_data_keys[key]
            or descriptor_data_keys[key]["external"] != "STREAM:"
        )
    ]


@dataclass
class ComposeEvent:
    descriptor: EventDescriptor
    event_counters: dict[str, int]

    def __call__(
        self,
        data: dict,
        timestamps: dict,
        seq_num: int | None = None,
        filled: dict[str, bool | str] | None = None,
        uid: str | None = None,
        time: float | None = None,
        validate: bool = True,
    ) -> Event:
        if seq_num is None:
            seq_num = self.event_counters[self.descriptor["name"]]
        if uid is None:
            uid = str(uuid.uuid4())
        if time is None:
            time = ttime.time()
        if filled is None:
            filled = {}
        doc = Event(
            uid=uid,
            time=time,
            data=data,
            timestamps=timestamps,
            seq_num=seq_num,
            filled=filled,
            descriptor=self.descriptor["uid"],
        )
        if validate:
            schema_validators[DocumentNames.event].validate(doc)

            if not (
                set(
                    _keys_without_stream_keys(
                        self.descriptor["data_keys"], self.descriptor["data_keys"]
                    )
                )
                == set(_keys_without_stream_keys(data, self.descriptor["data_keys"]))
                == set(
                    _keys_without_stream_keys(timestamps, self.descriptor["data_keys"])
                )
            ):
                raise EventModelValidationError(
                    'These sets of keys must match (other than "STREAM:" keys):\n'
                    "event['data'].keys(): {}\n"
                    "event['timestamps'].keys(): {}\n"
                    "descriptor['data_keys'].keys(): {}\n".format(
                        data.keys(),
                        timestamps.keys(),
                        self.descriptor["data_keys"].keys(),
                    )
                )
            if set(filled) - set(data):
                raise EventModelValidationError(
                    f"Keys in event['filled'] {filled.keys()} "
                    "must be a subset of those in "
                    f"event['data'] {data.keys()}"
                )
        self.event_counters[self.descriptor["name"]] = seq_num + 1
        return doc


def compose_event(
    *,
    descriptor: EventDescriptor,
    event_counters: dict[str, int],
    data: dict[str, Any],
    timestamps: dict[str, Any],
    seq_num: int,
    filled: dict[str, bool | str] | None = None,
    uid: str | None = None,
    time: float | None = None,
    validate: bool = True,
) -> Event:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeEvent(descriptor, event_counters)(
        data,
        timestamps,
        seq_num=seq_num,
        filled=filled,
        uid=uid,
        time=time,
        validate=validate,
    )


@dataclass
class ComposeDescriptorBundle:
    descriptor_doc: EventDescriptor
    compose_event: ComposeEvent
    compose_event_page: ComposeEventPage

    def __iter__(self) -> Iterator:
        return iter(
            (
                self.descriptor_doc,
                self.compose_event,
                self.compose_event_page,
            )
        )


@dataclass
class ComposeDescriptor:
    start: RunStart
    streams: dict
    event_counters: dict[str, int]

    def __call__(
        self,
        name,
        data_keys,
        hints=None,
        configuration=None,
        object_keys=None,
        object_classes=None,
        time=None,
        uid=None,
        validate=True,
    ) -> ComposeDescriptorBundle:
        if time is None:
            time = ttime.time()
        if uid is None:
            uid = str(uuid.uuid4())
        if hints is None:
            hints = {}
        if configuration is None:
            configuration = {}
        if object_keys is None:
            object_keys = {}
        if object_classes is None:
            object_classes = {}

        doc = EventDescriptor(
            configuration=configuration,
            data_keys=data_keys,
            name=name,
            object_keys=object_keys,
            run_start=self.start["uid"],
            time=time,
            uid=uid,
            object_classes=object_classes,
            hints=hints,
        )
        if validate:
            if name in self.streams and self.streams[name] != set(data_keys):
                raise EventModelValidationError(
                    f"A descriptor with the name {name} has already been composed with "
                    f"data_keys {self.streams[name]}. The requested data_keys were "
                    f"{set(data_keys)}. All descriptors in a given stream must have "
                    "the same data_keys."
                )
            schema_validators[DocumentNames.descriptor].validate(doc)

        if name not in self.streams:
            self.streams[name] = set(data_keys)
            self.event_counters[name] = 1

        return ComposeDescriptorBundle(
            descriptor_doc=doc,
            compose_event=ComposeEvent(
                descriptor=doc, event_counters=self.event_counters
            ),
            compose_event_page=ComposeEventPage(
                descriptor=doc, event_counters=self.event_counters
            ),
        )


def compose_descriptor(
    *,
    start: RunStart,
    streams: dict[str, Iterable],
    event_counters: dict[str, int],
    name: str,
    data_keys: dict[str, DataKey],
    uid: str | None = None,
    time: float | None = None,
    object_keys: dict[str, Any] | None = None,
    configuration: dict[str, Configuration] | None = None,
    hints: PerObjectHint | None = None,
    validate: bool = True,
) -> ComposeDescriptorBundle:
    """
    Here for backwards compatibility, the Compose class is prefered.
    """
    return ComposeDescriptor(start, streams, event_counters)(
        name,
        data_keys,
        hints=hints,
        configuration=configuration,
        object_keys=object_keys,
        time=time,
        uid=uid,
        validate=validate,
    )


@dataclass
class ComposeRunBundle:
    """Extensible compose run bundle. This maintains backward compatibility
    by unpacking into a basic run bundle
    (start, compose_descriptor, compose_resource, stop).
    Further extensions are optional and require keyword referencing
    (i.e. compose_stream_resource).
    """

    start_doc: RunStart
    compose_descriptor: ComposeDescriptor
    compose_resource: ComposeResource
    compose_stop: ComposeStop
    compose_stream_resource: ComposeStreamResource | None = None

    # iter for backwards compatibility
    def __iter__(self) -> Iterator:
        return iter(
            (
                self.start_doc,
                self.compose_descriptor,
                self.compose_resource,
                self.compose_stop,
            )
        )


def compose_run(
    *,
    uid: str | None = None,
    time: float | None = None,
    metadata: dict | None = None,
    validate: bool = True,
    event_counters: dict[str, int] | None = None,
) -> ComposeRunBundle:
    """
    Compose a RunStart document and factory functions for related documents.

    Parameters
    ----------
    uid : string, optional
        Unique identifier for this run, conventionally a UUID4. If None is
        given, a UUID4 will be generated.
    time : float, optional
        UNIX epoch time of start of this run. If None is given, the current
        time will be used.
    metadata : dict, optional
        Additional metadata include the document
    validate : boolean, optional
        Validate this document conforms to the schema.
    event_counters : dict, optional
        A dict for counting events, when an event is composed by any of the
        descriptors composed by this run, the element in this dict with the key of the
        descriptor name will be increased by 1.

    Returns
    -------
    ComposeRunBundle
    """
    if uid is None:
        uid = str(uuid.uuid4())
    if time is None:
        time = ttime.time()
    if metadata is None:
        metadata = {}

    # Define some mutable state to be shared internally by the closures composed
    # below.
    streams: dict[str, Iterable] = {}
    if event_counters is None:
        event_counters = {}
    poison_pill: list = []

    doc = dict(uid=uid, time=time, **metadata)

    if validate:
        schema_validators[DocumentNames.start].validate(doc)

    return ComposeRunBundle(
        cast(RunStart, doc),
        ComposeDescriptor(
            start=cast(RunStart, doc), streams=streams, event_counters=event_counters
        ),
        ComposeResource(start=cast(RunStart, doc)),
        ComposeStop(
            start=cast(RunStart, doc),
            event_counters=event_counters,
            poison_pill=poison_pill,
        ),
        compose_stream_resource=ComposeStreamResource(start=cast(RunStart, doc)),
    )
