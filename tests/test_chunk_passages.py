import pytest

from saga_companion.ingest import Chapter, Passage, chunk_chapter, chunk_chapters


def test_short_chapter_returns_one_passage() -> None:
    chapter = Chapter(title="Chapter 1", text="A short chapter.", index=1)

    passages = chunk_chapter(chapter, max_characters=100, overlap_characters=0)

    assert passages == [
        Passage(
            id="chapter-0001-passage-0001",
            chapter_index=1,
            passage_index=1,
            title="Chapter 1",
            text="A short chapter.",
            character_count=len("A short chapter."),
        )
    ]


def test_long_chapter_splits_into_multiple_passages() -> None:
    chapter = Chapter(title="Chapter 1", text="A" * 20 + "\n\n" + "B" * 20, index=1)

    passages = chunk_chapter(chapter, max_characters=25, overlap_characters=0)

    assert len(passages) == 2
    assert [passage.text for passage in passages] == ["A" * 20, "B" * 20]


def test_passages_never_exceed_max_characters() -> None:
    chapter = Chapter(title="Chapter 1", text=("A" * 15 + "\n\n") * 5, index=1)

    passages = chunk_chapter(chapter, max_characters=30, overlap_characters=5)

    assert all(passage.character_count <= 30 for passage in passages)


def test_paragraph_boundary_splitting_is_preferred() -> None:
    chapter = Chapter(title="Chapter 1", text="First paragraph.\n\nSecond paragraph.", index=1)

    passages = chunk_chapter(chapter, max_characters=20, overlap_characters=0)

    assert [passage.text for passage in passages] == [
        "First paragraph.",
        "Second paragraph.",
    ]


def test_oversized_paragraph_falls_back_to_sentence_splitting() -> None:
    chapter = Chapter(title="Chapter 1", text="First sentence. Second sentence.", index=1)

    passages = chunk_chapter(chapter, max_characters=16, overlap_characters=0)

    assert [passage.text for passage in passages] == [
        "First sentence.",
        "Second sentence.",
    ]


def test_oversized_sentence_falls_back_to_hard_splitting() -> None:
    chapter = Chapter(title="Chapter 1", text="A" * 25, index=1)

    passages = chunk_chapter(chapter, max_characters=10, overlap_characters=0)

    assert [passage.text for passage in passages] == ["A" * 10, "A" * 10, "A" * 5]


def test_overlap_appears_between_consecutive_passages_when_possible() -> None:
    chapter = Chapter(title="Chapter 1", text="abcdefghij\n\nklmnopqrst", index=1)

    passages = chunk_chapter(chapter, max_characters=16, overlap_characters=3)

    assert passages[0].text == "abcdefghij"
    assert passages[1].text == "hij\n\nklmnopqrst"


def test_empty_chapter_text_returns_empty_list() -> None:
    chapter = Chapter(title="Chapter 1", text=" \n\n ", index=1)

    assert chunk_chapter(chapter) == []


@pytest.mark.parametrize(
    ("max_characters", "overlap_characters"),
    [
        (0, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ],
)
def test_invalid_max_and_overlap_values_raise(
    max_characters: int,
    overlap_characters: int,
) -> None:
    chapter = Chapter(title="Chapter 1", text="Text.", index=1)

    with pytest.raises(ValueError):
        chunk_chapter(
            chapter,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )


def test_chunk_chapters_returns_flat_list_across_multiple_chapters() -> None:
    chapters = [
        Chapter(title="Chapter 1", text="A" * 10 + "\n\n" + "B" * 10, index=1),
        Chapter(title="Chapter 2", text="C" * 10, index=2),
    ]

    passages = chunk_chapters(chapters, max_characters=12, overlap_characters=0)

    assert [passage.chapter_index for passage in passages] == [1, 1, 2]
    assert [passage.passage_index for passage in passages] == [1, 2, 1]


def test_passage_ids_are_stable_and_one_based() -> None:
    chapter = Chapter(title="Chapter 12", text="A" * 10 + "\n\n" + "B" * 10, index=12)

    passages = chunk_chapter(chapter, max_characters=12, overlap_characters=0)

    assert [passage.id for passage in passages] == [
        "chapter-0012-passage-0001",
        "chapter-0012-passage-0002",
    ]
