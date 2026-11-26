from pathlib import Path

from bluesky_interfaces.documents.generate.create_documents import (
    JSONSCHEMA,
    TYPEDDICTS,
    generate,
)


def test_generated_json_matches_typed_dict(tmp_path: Path):
    tmp_documents = tmp_path / "typed_dicts"
    tmp_documents.mkdir()
    tmp_jsonschema = tmp_path / "jsonschema"
    tmp_jsonschema.mkdir()

    generate(jsonschema_root=tmp_jsonschema, documents_root=tmp_documents)

    assert {path.name for path in tmp_jsonschema.glob("*.json")} == {
        path.name for path in JSONSCHEMA.glob("*.json") if not path.name.startswith("bulk")
    }
    assert {path.name for path in tmp_documents.glob("*.py")} == {
        path.name for path in TYPEDDICTS.glob("*.py")
    }

    for new_jsonschema_path in tmp_jsonschema.iterdir():
        old_jsonschema_path = JSONSCHEMA / new_jsonschema_path.name

        if (
            not old_jsonschema_path.exists()
            or new_jsonschema_path.read_text() != old_jsonschema_path.read_text()
        ):
            raise Exception(
                f"{str(old_jsonschema_path)} does not match "
                f"{str(new_jsonschema_path)}. Did you forget to run "
                "`python -m bluesky_interfaces.documents.generate` after changes?"
            )

    for new_document_path in tmp_documents.iterdir():
        old_document_path = TYPEDDICTS / new_document_path.name

        if (
            not old_document_path.exists()
            or new_document_path.read_text() != old_document_path.read_text()
        ):
            raise Exception(
                f"{str(old_document_path)} does not match "
                f"{str(new_document_path)}. Did you forget to run "
                "`python -m bluesky_interfaces.documents.generate` after changes?"
            )
