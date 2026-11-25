from typing import get_args

from bluesky_interfaces.documents import typed_dicts
from bluesky_interfaces.documents.document_names import DocumentNames
from bluesky_interfaces.documents.jsonschemas import compose_run, schema_validators
from bluesky_interfaces.documents.typed_dicts import (
    ALL_TYPED_DICTS,
    Datum,
    DatumPage,
    Event,
    EventDescriptor,
    EventPage,
    NamedTyped_Dict,
    Resource,
    RunStart,
    RunStop,
    StreamDatum,
    StreamResource,
)

EXPECTED_PAIRS = {
    DocumentNames.datum: Datum,
    DocumentNames.datum_page: DatumPage,
    DocumentNames.descriptor: EventDescriptor,
    DocumentNames.event: Event,
    DocumentNames.event_page: EventPage,
    DocumentNames.resource: Resource,
    DocumentNames.start: RunStart,
    DocumentNames.stop: RunStop,
    DocumentNames.stream_datum: StreamDatum,
    DocumentNames.stream_resource: StreamResource,
}


def named_document_pairs():
    pairs = {}
    for named_document in get_args(NamedTyped_Dict):
        name_literal, document_class = get_args(named_document)
        (name,) = get_args(name_literal)
        pairs[name] = document_class
    return pairs


def test_named_document_pairs_each_name_with_its_document():
    assert named_document_pairs() == EXPECTED_PAIRS
    for document_class in ALL_TYPED_DICTS:
        alias = getattr(typed_dicts, f"Named{document_class.__name__}")
        assert alias in get_args(NamedTyped_Dict)


def test_composed_documents_match_the_name_they_are_emitted_under(tmp_path):
    run = compose_run()
    descriptor = run.compose_descriptor(
        name="primary",
        data_keys={"motor": {"shape": [], "dtype": "number", "source": "..."}},
    )
    resource = run.compose_resource(
        spec="TIFF", root=str(tmp_path), resource_path="stack.tiff", resource_kwargs={}
    )
    assert run.compose_stream_resource is not None
    stream = run.compose_stream_resource(
        mimetype="image/tiff",
        uri=f"file://localhost{tmp_path}/test_streams",
        data_key="motor",
        parameters={},
    )
    documents = {
        DocumentNames.start: run.start_doc,
        DocumentNames.descriptor: descriptor.descriptor_doc,
        DocumentNames.resource: resource.resource_doc,
        DocumentNames.stream_resource: stream.stream_resource_doc,
        DocumentNames.datum: resource.compose_datum(datum_kwargs={"slice": 5}),
        DocumentNames.datum_page: resource.compose_datum_page(datum_kwargs={"slice": [6]}),
        DocumentNames.event: descriptor.compose_event(data={"motor": 0}, timestamps={"motor": 0}),
        DocumentNames.event_page: descriptor.compose_event_page(
            data={"motor": [1]}, timestamps={"motor": [1]}
        ),
        DocumentNames.stream_datum: stream.compose_stream_datum(indices={"start": 0, "stop": 1}),
        DocumentNames.stop: run.compose_stop(),
    }

    pairs = named_document_pairs()
    assert set(documents) == set(pairs)
    for name, doc in documents.items():
        assert set(doc) <= set(pairs[name].__annotations__)
        schema_validators[name].validate(doc)
