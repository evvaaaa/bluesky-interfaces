import itertools
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize(
    ("module", "dependency", "extra"),
    [
        ("jsonschema", "jsonschema", "jsonschema"),
        ("jsonschemas", "jsonschema", "jsonschema"),
        ("basemodels", "pydantic", "basemodels"),
    ],
)
def test_missing_optional_dependency(module, dependency, extra):
    script = textwrap.dedent(
        f"""
        import importlib
        import importlib.abc
        import sys

        class BlockDependency(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == {dependency!r}:
                    raise ModuleNotFoundError("blocked", name=fullname)

        sys.meta_path.insert(0, BlockDependency())
        import bluesky_interfaces.documents.typed_dicts

        try:
            importlib.import_module("bluesky_interfaces.documents.{module}")
        except ModuleNotFoundError as exc:
            assert exc.name == {dependency!r}
            assert "pip install bluesky-interfaces[{extra}]" in str(exc)
        else:
            raise AssertionError("Expected a missing dependency error")
        """
    )
    subprocess.run([sys.executable, "-c", script], check=True)


@pytest.mark.parametrize(
    ("module", "dependency"),
    [
        ("jsonschema", "jsonschema"),
        ("jsonschemas", "jsonschema"),
        ("basemodels", "pydantic"),
    ],
)
def test_missing_transitive_dependency_is_not_masked(module, dependency):
    script = textwrap.dedent(
        f"""
        import importlib
        import importlib.abc
        import sys

        class BrokenDependency(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == {dependency!r}:
                    raise ModuleNotFoundError("broken dependency", name="transitive")

        sys.meta_path.insert(0, BrokenDependency())
        try:
            importlib.import_module("bluesky_interfaces.documents.{module}")
        except ModuleNotFoundError as exc:
            assert exc.name == "transitive"
            assert str(exc) == "broken dependency"
        else:
            raise AssertionError("Expected the original error")
        """
    )
    subprocess.run([sys.executable, "-c", script], check=True)


def test_compose_documents_and_validate_schemas():
    pytest.importorskip("jsonschema")
    import numpy as np

    from bluesky_interfaces.documents import jsonschemas
    from bluesky_interfaces.documents.document_names import DocumentNames
    from bluesky_interfaces.documents.jsonschema import compose_run as singular_compose
    from bluesky_interfaces.documents.jsonschemas import (
        EventModelError,
        EventModelValidationError,
        compose_run,
        schema_validators,
        schemas,
    )

    assert set(schemas) == set(DocumentNames) == set(schema_validators)
    assert singular_compose is compose_run
    assert not hasattr(jsonschemas, "DocumentRouter")
    assert not hasattr(jsonschemas, "Filler")
    assert not hasattr(jsonschemas, "pack_event_page")
    run = compose_run(uid="run", time=1)
    descriptor = run.compose_descriptor(
        name="primary",
        data_keys={"x": {"source": "test", "dtype": "array", "shape": [2]}},
    )
    event = descriptor.compose_event(data={"x": np.array([1, 2])}, timestamps={"x": 2})
    page = descriptor.compose_event_page(data={"x": [[3, 4]]}, timestamps={"x": [3]})
    assert event["seq_num"] == 1
    assert page["seq_num"] == [2]
    with pytest.raises(EventModelValidationError, match="sets of keys must match"):
        descriptor.compose_event(data={}, timestamps={})
    resource = run.compose_resource(spec="test", root="/", resource_path="data", resource_kwargs={})
    datum = resource.compose_datum(datum_kwargs={"index": 1})
    datum_page = resource.compose_datum_page(datum_kwargs={"index": [2, 3]})
    assert datum["datum_id"].endswith("/0")
    assert [item.rsplit("/", 1)[-1] for item in datum_page["datum_id"]] == ["1", "2"]
    stream = run.compose_stream_resource(
        mimetype="application/octet-stream",
        uri="file://localhost/data",
        data_key="x",
        parameters={},
    )
    stream_datum = stream.compose_stream_datum(indices={"start": 2, "stop": 4})
    assert stream_datum["indices"] == {"start": 2, "stop": 4}
    assert run.compose_stop()["num_events"] == {"primary": 2}
    with pytest.raises(EventModelError, match="Already composed"):
        run.compose_stop()


def test_compose_stream_datum_arguments():
    pytest.importorskip("jsonschema")
    from bluesky_interfaces.documents.jsonschemas import (
        compose_stream_datum,
        compose_stream_resource,
    )

    resource = compose_stream_resource(
        mimetype="application/octet-stream",
        uri="file://localhost/data",
        data_key="x",
        parameters={},
    ).stream_resource_doc
    with pytest.warns(DeprecationWarning):
        datum = compose_stream_datum(
            stream_resource=resource,
            counter=itertools.count(),
            indices={"start": 2, "stop": 4},
            seq_nums={"start": 5, "stop": 7},
        )
    assert datum["indices"] == {"start": 2, "stop": 4}
    assert datum["seq_nums"] == {"start": 5, "stop": 7}


def test_basemodels_can_be_imported():
    pytest.importorskip("pydantic")
    from bluesky_interfaces.documents.basemodels import RunStart

    assert RunStart(uid="run", time=1).uid == "run"
