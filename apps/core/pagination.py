from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginationUniforme(PageNumberPagination):
    """
    Pagination au format de réponse uniforme du projet :
    {"success": true, "data": {"results": [...], "count": N,
     "next": url|null, "previous": url|null}}
    — à utiliser dans TOUTE vue paginée à la place de la réponse DRF nue.
    page_size hérite de REST_FRAMEWORK['PAGE_SIZE'] (20).
    """

    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': {
                'results':  data,
                'count':    self.page.paginator.count,
                'next':     self.get_next_link(),
                'previous': self.get_previous_link(),
            },
        })
