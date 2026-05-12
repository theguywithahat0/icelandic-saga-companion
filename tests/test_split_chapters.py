from saga_companion.ingest import Chapter, split_into_chapters


def test_splits_uppercase_roman_numeral_headings() -> None:
    chapters = split_into_chapters(
        "Preface text\n\nCHAPTER I\nThe first chapter.\n\nCHAPTER II\nThe second chapter."
    )

    assert chapters == [
        Chapter(title="CHAPTER I", text="The first chapter.", index=1),
        Chapter(title="CHAPTER II", text="The second chapter.", index=2),
    ]


def test_splits_numeric_headings() -> None:
    chapters = split_into_chapters("Chapter 1\nOpening.\n\nChapter 2\nNext.")

    assert [chapter.title for chapter in chapters] == ["Chapter 1", "Chapter 2"]
    assert [chapter.text for chapter in chapters] == ["Opening.", "Next."]


def test_splits_chap_abbreviation_headings() -> None:
    chapters = split_into_chapters("CHAP. I\nA short passage.\n\nCHAP. II\nAnother.")

    assert [chapter.title for chapter in chapters] == ["CHAP. I", "CHAP. II"]


def test_falls_back_to_blank_line_chunks() -> None:
    chapters = split_into_chapters("First block.\n\n\nSecond block.\n\n  \nThird block.")

    assert chapters == [
        Chapter(title="Chunk 1", text="First block.", index=1),
        Chapter(title="Chunk 2", text="Second block.", index=2),
        Chapter(title="Chunk 3", text="Third block.", index=3),
    ]


def test_normalizes_windows_line_endings() -> None:
    chapters = split_into_chapters("CHAPTER 1\r\nLine one.\r\nLine two.\r\n\r\nCHAPTER 2\r\nNext.")

    assert chapters[0].text == "Line one.\nLine two."
    assert chapters[1].text == "Next."


def test_empty_input_returns_empty_list() -> None:
    assert split_into_chapters("") == []
    assert split_into_chapters(" \n\r\n ") == []


def test_chapter_indexes_are_one_based_after_skipping_empty_chapters() -> None:
    chapters = split_into_chapters("CHAPTER I\n\nCHAPTER II\nBody.")

    assert chapters == [Chapter(title="CHAPTER II", text="Body.", index=1)]
