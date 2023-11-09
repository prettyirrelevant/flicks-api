from rest_framework.parsers import BaseParser


class LowerCasePlainTextParser(BaseParser):  # pylint: disable=too-few-public-methods
    media_type = 'text/plain; charset=utf-8'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


class UpperCasePlainTextParser(BaseParser):  # pylint: disable=too-few-public-methods
    media_type = 'text/plain; charset=UTF-8'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()
