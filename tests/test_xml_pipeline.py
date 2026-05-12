from pathlib import Path

import pytest

from saga_companion.ingest import (
    Chapter,
    IngestedXmlSaga,
    chapters_from_xml_saga,
    ingest_saga_xml_directory,
    ingest_saga_xml_file,
)


def test_ingesting_one_xml_saga_returns_metadata_chapters_and_passages(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    ingested = ingest_saga_xml_file(
        xml_path,
        max_characters=100,
        overlap_characters=0,
    )

    assert ingested.saga.id == "bandamanna-saga"
    assert ingested.saga.metadata.title == "Bandamanna saga"
    assert [chapter.title for chapter in ingested.chapters] == [
        "Titled chapter",
        "Chapter 2",
        "Chapter 3",
    ]
    assert [passage.text for passage in ingested.passages] == [
        "First paragraph.",
        "Second paragraph.",
        "Poetry line one.\nPoetry line two.",
    ]


def test_xml_chapter_title_is_used_when_present(tmp_path: Path) -> None:
    xml_path = tmp_path / "titled.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    ingested = ingest_saga_xml_file(xml_path)

    assert ingested.chapters[0].title == "Titled chapter"


def test_fallback_title_uses_chapter_number_when_title_is_missing(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "numbered.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    ingested = ingest_saga_xml_file(xml_path)

    assert ingested.chapters[1].title == "Chapter 2"


def test_fallback_title_uses_chapter_index_when_title_and_number_are_missing(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "untitled.xml"
    xml_path.write_text("<document><content><chapter><paragraph>Body.</paragraph></chapter></content></document>", encoding="utf-8")

    ingested = ingest_saga_xml_file(xml_path)

    assert ingested.chapters == [Chapter(title="Chapter 1", text="Body.", index=1)]


def test_xml_chapters_with_empty_text_are_skipped(tmp_path: Path) -> None:
    xml_path = tmp_path / "empty_chapter.xml"
    xml_path.write_text(
        """\
<document>
  <content>
    <chapter number="1"><paragraph> </paragraph></chapter>
    <chapter number="2"><paragraph>Body.</paragraph></chapter>
  </content>
</document>
""",
        encoding="utf-8",
    )

    ingested = ingest_saga_xml_file(xml_path)

    assert ingested.chapters == [Chapter(title="Chapter 2", text="Body.", index=2)]


def test_passage_chunking_respects_max_characters(tmp_path: Path) -> None:
    xml_path = tmp_path / "long.xml"
    xml_path.write_text(
        "<document><content><chapter number='1'>"
        "<paragraph>AAAAAAAAAAAAAAAAAAAA</paragraph>"
        "<paragraph>BBBBBBBBBBBBBBBBBBBB</paragraph>"
        "</chapter></content></document>",
        encoding="utf-8",
    )

    ingested = ingest_saga_xml_file(
        xml_path,
        max_characters=25,
        overlap_characters=5,
    )

    assert len(ingested.passages) > 1
    assert all(passage.character_count <= 25 for passage in ingested.passages)


def test_poetry_text_from_xml_appears_in_passages(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    ingested = ingest_saga_xml_file(
        xml_path,
        max_characters=100,
        overlap_characters=0,
    )

    assert "Poetry line one.\nPoetry line two." in [
        passage.text for passage in ingested.passages
    ]


def test_directory_ingestion_returns_xml_sagas_sorted_by_filename(
    tmp_path: Path,
) -> None:
    (tmp_path / "zeta_saga.xml").write_text(
        "<document><content><chapter><paragraph>Zeta.</paragraph></chapter></content></document>",
        encoding="utf-8",
    )
    (tmp_path / "alpha_saga.xml").write_text(
        "<document><content><chapter><paragraph>Alpha.</paragraph></chapter></content></document>",
        encoding="utf-8",
    )

    ingested = ingest_saga_xml_directory(
        tmp_path,
        max_characters=100,
        overlap_characters=0,
    )

    assert [saga.saga.filename for saga in ingested] == [
        "alpha_saga.xml",
        "zeta_saga.xml",
    ]


def test_missing_file_and_directory_errors_propagate(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_saga_xml_file(tmp_path / "missing.xml")

    with pytest.raises(FileNotFoundError):
        ingest_saga_xml_directory(tmp_path / "missing")


def test_xml_pipeline_does_not_create_output_files(tmp_path: Path) -> None:
    xml_path = tmp_path / "egils_saga.xml"
    xml_path.write_text(
        "<document><content><chapter><paragraph>Only input.</paragraph></chapter></content></document>",
        encoding="utf-8",
    )
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    ingest_saga_xml_file(xml_path)

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert after == before


def test_xml_pipeline_exports_are_importable(tmp_path: Path) -> None:
    xml_path = tmp_path / "exported.xml"
    xml_path.write_text(
        "<document><content><chapter><paragraph>Body.</paragraph></chapter></content></document>",
        encoding="utf-8",
    )

    ingested = ingest_saga_xml_file(xml_path)

    assert isinstance(ingested, IngestedXmlSaga)
    assert chapters_from_xml_saga(ingested.saga) == ingested.chapters


def _sample_xml() -> str:
    return """\
<document>
  <metadata>
    <title>Bandamanna saga</title>
    <basename>bandamanna_saga.en</basename>
  </metadata>
  <content>
    <chapter number="1" title="Titled chapter">
      <paragraph>First paragraph.</paragraph>
    </chapter>
    <chapter number="2">
      <paragraph>Second paragraph.</paragraph>
    </chapter>
    <chapter>
      <poetry>
        <line>Poetry line one.</line>
        <line>Poetry line two.</line>
      </poetry>
    </chapter>
  </content>
</document>
"""
