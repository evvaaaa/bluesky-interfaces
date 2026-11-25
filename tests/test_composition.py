import numpy

from bluesky_interfaces.documents.jsonschemas import compose_resource, compose_run
from bluesky_interfaces.documents.typed_dicts.stream_datum import StreamRange


def test_compose_run():
    bundle = compose_run()
    start_doc, compose_descriptor, compose_resource, compose_stop = bundle
    assert bundle.start_doc is start_doc
    assert bundle.compose_descriptor is compose_descriptor
    assert bundle.compose_resource is compose_resource
    assert bundle.compose_stop is compose_stop
    bundle = compose_descriptor(
        data_keys={
            "motor": {"shape": [], "dtype": "number", "source": "...", "units": "s"},
            "image": {
                "shape": [512, 512],
                "dtype": "number",
                "source": "...",
                "external": "FILESTORE:",
            },
        },
        name="primary",
    )
    descriptor_doc, compose_event, compose_event_page = bundle
    assert bundle.descriptor_doc is descriptor_doc
    assert bundle.compose_event is compose_event
    assert bundle.compose_event_page is compose_event_page
    bundle = compose_resource(
        spec="TIFF", root="/tmp", resource_path="stack.tiff", resource_kwargs={}
    )
    resource_doc, compose_datum, compose_datum_page = bundle
    assert bundle.resource_doc is resource_doc
    assert bundle.compose_datum is compose_datum
    assert bundle.compose_datum_page is compose_datum_page
    datum_doc = compose_datum(datum_kwargs={"slice": 5})
    event_doc = compose_event(
        data={"motor": 0, "image": datum_doc["datum_id"]},
        timestamps={"motor": 0, "image": 0},
        filled={"image": False},
    )
    datum_page = compose_datum_page(datum_kwargs={"slice": [10, 15]})
    event_page = compose_event_page(
        data={"motor": [1, 2], "image": datum_page["datum_id"]},
        timestamps={"motor": [0, 0], "image": [0, 0]},
        filled={"image": [False, False]},
        seq_num=[1, 2],
    )
    assert event_doc["descriptor"] == descriptor_doc["uid"]
    assert event_page["descriptor"] == descriptor_doc["uid"]
    assert event_doc["seq_num"] == 1
    assert compose_stop()["num_events"]["primary"] == 3


def test_compose_stream_resource(tmp_path):
    run = compose_run()
    assert run.compose_stream_resource is not None
    bundle = run.compose_stream_resource(
        mimetype="image/tiff",
        uri=f"file://localhost{tmp_path}/test_streams",
        data_key="det1",
        parameters={},
    )
    resource_doc, compose_stream_datum = bundle
    assert bundle.stream_resource_doc is resource_doc
    assert bundle.compose_stream_datum is compose_stream_datum
    datum = compose_stream_datum(StreamRange(start=0, stop=2), StreamRange(start=1, stop=3))
    assert datum["stream_resource"] == resource_doc["uid"]
    assert datum["indices"] == {"start": 0, "stop": 2}
    assert datum["seq_nums"] == {"start": 1, "stop": 3}


def test_array_like():
    run = compose_run()
    descriptor = run.compose_descriptor(
        data_keys={"a": {"shape": (3,), "dtype": "array", "source": ""}},
        name="primary",
    )
    page = descriptor.compose_event_page(
        data={"a": numpy.ones((5, 3))},
        timestamps={"a": [1, 2, 3, 4, 5]},
        seq_num=[1, 2, 3, 4, 5],
    )
    assert len(page["data"]["a"]) == 5


def test_resource_start_optional():
    resource = compose_resource(
        spec="TEST", root="/", resource_path="", resource_kwargs={}
    ).resource_doc
    assert "run_start" not in resource
