from rest_framework.pagination import CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = 10
    max_page_size = 20
    cursor_query_param = 'page'
    ordering = '-created_at'
