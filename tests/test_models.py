from album_tracker_api.models.base import pascal_to_snake


class TestPascalToSnake:
    def test_returns_empty_string_for_empty_input(self) -> None:
        assert pascal_to_snake("") == ""

    def test_preserves_acronym_without_internal_underscores(self) -> None:
        assert pascal_to_snake("HTTP") == "http"
        assert pascal_to_snake("HTTPRequest") == "http_request"
