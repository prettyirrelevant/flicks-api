from rest_framework.parsers import BaseParser


class PlainTextParser(BaseParser):  # pylint: disable=too-few-public-methods
    media_type = 'text/plain; charset=utf-8'

    def parse(self, stream, media_type=None, parser_context=None):  # noqa: PLR6301 ARG002
        return stream.read()
