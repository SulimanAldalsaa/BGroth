from rest_framework.pagination import PageNumberPagination


class OptionalPageNumberPagination(PageNumberPagination):
    """Paginate only when the client sends ``page`` or ``page_size``.

    Without either parameter the endpoint keeps returning a plain JSON array,
    so existing clients are not affected.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if not {"page", "page_size"} & set(request.query_params):
            return None

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response_schema(self, schema):
        # OpenAPI documents the default response (a plain array); the
        # paginated envelope is described in docs/API.md.
        return {"type": "array", "items": schema}
