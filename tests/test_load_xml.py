from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from saga_companion.ingest import (
    SagaXmlBlock,
    load_saga_xml_directory,
    load_saga_xml_file,
)


def test_loads_metadata_fields_from_sagadB_style_xml(tmp_path: Path) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    saga = load_saga_xml_file(xml_path)

    assert saga.metadata.title == "Bandamanna saga"
    assert saga.metadata.title_orig == "Bandamanna saga"
    assert saga.metadata.language == "English"
    assert saga.metadata.language_iso == "en"
    assert saga.metadata.basename == "bandamanna_saga.en"
    assert saga.filename == "bandamanna_saga.en.xml"
    assert saga.path == xml_path


def test_maps_special_metadata_field_names(tmp_path: Path) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    metadata = load_saga_xml_file(xml_path).metadata

    assert metadata.translator == "William Morris"
    assert metadata.translation_date == "1891"
    assert metadata.source_name == "SagaDB"
    assert metadata.source_url == "https://example.test/source"


def test_preserves_all_metadata_in_raw(tmp_path: Path) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    raw = load_saga_xml_file(xml_path).metadata.raw

    assert raw["trans"] == "William Morris"
    assert raw["custom_field"] == "Custom & escaped value"


def test_extracts_chapter_fields_text_and_character_count(tmp_path: Path) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    chapter = load_saga_xml_file(xml_path).chapters[0]

    assert chapter.number == "1"
    assert chapter.title == "Of Ufeig and Odd his son."
    assert chapter.blocks == [
        SagaXmlBlock(kind="paragraph", text="First paragraph.", lines=[]),
        SagaXmlBlock(kind="paragraph", text="Second paragraph.", lines=[]),
    ]
    assert chapter.paragraphs == ["First paragraph.", "Second paragraph."]
    assert chapter.text == "First paragraph.\n\nSecond paragraph."
    assert chapter.character_count == len(chapter.text)


def test_builds_saga_level_text_and_character_count(tmp_path: Path) -> None:
    xml_path = tmp_path / "bandamanna_saga.en.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    saga = load_saga_xml_file(xml_path)

    assert saga.text == (
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    )
    assert saga.character_count == len(saga.text)


def test_builds_stable_id_from_metadata_basename(tmp_path: Path) -> None:
    xml_path = tmp_path / "ignored_filename.xml"
    xml_path.write_text(_sample_xml(), encoding="utf-8")

    assert load_saga_xml_file(xml_path).id == "bandamanna-saga"


def test_falls_back_to_filename_if_basename_is_missing(tmp_path: Path) -> None:
    xml_path = tmp_path / "egils_saga.is.xml"
    xml_path.write_text(
        "<document><metadata><title>Egils saga</title></metadata></document>",
        encoding="utf-8",
    )

    assert load_saga_xml_file(xml_path).id == "egils-saga"


def test_directory_loading_returns_xml_files_sorted_by_filename(tmp_path: Path) -> None:
    (tmp_path / "zeta_saga.xml").write_text("<document />", encoding="utf-8")
    (tmp_path / "alpha_saga.xml").write_text("<document />", encoding="utf-8")
    (tmp_path / "not_xml.txt").write_text("<document />", encoding="utf-8")

    sagas = load_saga_xml_directory(tmp_path)

    assert [saga.filename for saga in sagas] == ["alpha_saga.xml", "zeta_saga.xml"]


def test_directory_loading_ignores_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "alpha_saga.xml").write_text("<document />", encoding="utf-8")
    (tmp_path / "nested.xml").mkdir()

    sagas = load_saga_xml_directory(tmp_path)

    assert [saga.filename for saga in sagas] == ["alpha_saga.xml"]


def test_missing_xml_file_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_saga_xml_file(tmp_path / "missing.xml")


def test_directory_path_passed_to_file_loader_raises(tmp_path: Path) -> None:
    with pytest.raises(IsADirectoryError):
        load_saga_xml_file(tmp_path)


def test_file_path_passed_to_directory_loader_raises(tmp_path: Path) -> None:
    xml_path = tmp_path / "saga.xml"
    xml_path.write_text("<document />", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        load_saga_xml_directory(xml_path)


def test_missing_metadata_and_content_do_not_crash(tmp_path: Path) -> None:
    xml_path = tmp_path / "empty_document.xml"
    xml_path.write_text("<document />", encoding="utf-8")

    saga = load_saga_xml_file(xml_path)

    assert saga.metadata.raw == {}
    assert saga.chapters == []
    assert saga.text == ""
    assert saga.character_count == 0


def test_malformed_xml_raises_standard_parse_error(tmp_path: Path) -> None:
    xml_path = tmp_path / "bad.xml"
    xml_path.write_text("<document>", encoding="utf-8")

    with pytest.raises(ET.ParseError):
        load_saga_xml_file(xml_path)


def test_poetry_block_lines_are_extracted(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry_saga.xml"
    xml_path.write_text(_poetry_xml(), encoding="utf-8")

    poetry_block = load_saga_xml_file(xml_path).chapters[0].blocks[1]

    assert poetry_block.kind == "poetry"
    assert poetry_block.lines == ["Line one.", "Line two."]


def test_poetry_text_joins_lines_with_single_newlines(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry_saga.xml"
    xml_path.write_text(_poetry_xml(), encoding="utf-8")

    poetry_block = load_saga_xml_file(xml_path).chapters[0].blocks[1]

    assert poetry_block.text == "Line one.\nLine two."


def test_chapter_text_preserves_paragraph_poetry_paragraph_order(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry_saga.xml"
    xml_path.write_text(_poetry_xml(), encoding="utf-8")

    chapter = load_saga_xml_file(xml_path).chapters[0]

    assert chapter.text == "Before.\n\nLine one.\nLine two.\n\nAfter."


def test_empty_poetry_lines_are_skipped(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry_saga.xml"
    xml_path.write_text(_poetry_xml(), encoding="utf-8")

    poetry_block = load_saga_xml_file(xml_path).chapters[0].blocks[1]

    assert poetry_block.lines == ["Line one.", "Line two."]


def test_empty_poetry_blocks_are_skipped(tmp_path: Path) -> None:
    xml_path = tmp_path / "empty_poetry_saga.xml"
    xml_path.write_text(
        """\
<document>
  <content>
    <chapter number="1">
      <paragraph>Before.</paragraph>
      <poetry><line> </line></poetry>
      <paragraph>After.</paragraph>
    </chapter>
  </content>
</document>
""",
        encoding="utf-8",
    )

    chapter = load_saga_xml_file(xml_path).chapters[0]

    assert chapter.blocks == [
        SagaXmlBlock(kind="paragraph", text="Before.", lines=[]),
        SagaXmlBlock(kind="paragraph", text="After.", lines=[]),
    ]
    assert chapter.text == "Before.\n\nAfter."


def test_saga_level_text_includes_poetry(tmp_path: Path) -> None:
    xml_path = tmp_path / "poetry_saga.xml"
    xml_path.write_text(_poetry_xml(), encoding="utf-8")

    saga = load_saga_xml_file(xml_path)

    assert saga.text == "Before.\n\nLine one.\nLine two.\n\nAfter."
    assert saga.character_count == len(saga.text)


def test_saga_xml_block_is_exported() -> None:
    assert SagaXmlBlock(kind="paragraph", text="Text.", lines=[]).text == "Text."


def _sample_xml() -> str:
    return """\
<document>
  <metadata>
    <title> Bandamanna saga </title>
    <title_orig>Bandamanna saga</title_orig>
    <language>English</language>
    <language_iso>en</language_iso>
    <basename>bandamanna_saga.en</basename>
    <trans>William Morris</trans>
    <editor>Editor Name</editor>
    <trans_date>1891</trans_date>
    <sourcename>SagaDB</sourcename>
    <sourceurl>https://example.test/source</sourceurl>
    <custom_field>Custom &amp; escaped value</custom_field>
  </metadata>
  <content>
    <chapter number="1" title="Of Ufeig and Odd his son.">
      <paragraph> First paragraph. </paragraph>
      <paragraph></paragraph>
      <paragraph>Second paragraph.</paragraph>
    </chapter>
    <chapter number="2">
      <paragraph>Third paragraph.</paragraph>
    </chapter>
  </content>
</document>
"""


def _poetry_xml() -> str:
    return """\
<document>
  <content>
    <chapter number="1" title="Mixed chapter">
      <paragraph>Before.</paragraph>
      <poetry>
        <line>Line one.</line>
        <line> </line>
        <line>Line two.</line>
      </poetry>
      <unknown>Ignored.</unknown>
      <paragraph>After.</paragraph>
    </chapter>
  </content>
</document>
"""
