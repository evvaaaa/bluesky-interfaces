from .datum import Datum
from .datum_page import DatumPage
from .event import Event
from .event_descriptor import (
    Dtype,
    EventDescriptor,
    Limits,
    LimitsRange,
)
from .event_page import EventPage
from .resource import Resource
from .run_start import RunStart
from .run_stop import RunStop
from .stream_datum import StreamDatum
from .stream_resource import StreamResource

DocumentType = (
    type[Datum]
    | type[DatumPage]
    | type[Event]
    | type[EventDescriptor]
    | type[EventPage]
    | type[Resource]
    | type[RunStart]
    | type[RunStop]
    | type[StreamDatum]
    | type[StreamResource]
)

Document = (
    Datum
    | DatumPage
    | Event
    | EventDescriptor
    | EventPage
    | Resource
    | RunStart
    | RunStop
    | StreamDatum
    | StreamResource
)

ALL_BASEMODELS: tuple[DocumentType, ...] = (
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


__all__ = [
    "Datum",
    "DatumPage",
    "Dtype",
    "Event",
    "EventDescriptor",
    "EventPage",
    "Limits",
    "LimitsRange",
    "Resource",
    "RunStart",
    "RunStop",
    "StreamDatum",
    "StreamResource",
    "DocumentType",
]
