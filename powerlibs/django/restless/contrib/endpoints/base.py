from django.conf import settings
from django.core.exceptions import FieldError

from powerlibs.django.restless.http import Http400
from powerlibs.django.restless.models import serialize


def block_fields(fields):
    def new_method(method):
        def request(self, request, *args, **kwargs):
            for field in fields:
                if field in request.data:
                    return Http400({"error": "Invalid field name: {}".format(field)})
        return method(self, request, *args, **kwargs)
    return new_method


class PaginatedEndpointMixin:
    def get(self, request, *args, **kwargs):
        limit = int(request.GET.get('_limit') or settings.DEFAULT_PAGE_SIZE)
        offset = int(request.GET.get('_offset') or 0)

        begin = offset
        end = begin + limit

        qs = self.get_query_set(request, *args, **kwargs)
        total = qs.count()

        paginated_qs = qs[begin:end]
        count = paginated_qs.count()

        serialized_results = self.serialize(paginated_qs)

        return {
            'total': total,
            'count': count,
            'results': serialized_results,
        }


class OrderedEndpointMixin:
    def get_query_set(self, request, *args, **kwargs):
        queryset = super().get_query_set(request, *args, **kwargs)

        orderby_field = request.GET.get('_orderby', None)
        if orderby_field:
            try:
                queryset = queryset.order_by(orderby_field)
            except FieldError as ex:
                return Http400("FieldError: {}".format(ex))

        return queryset


class FilteredEndpointMixin:
    def get_query_set(self, request, *args, **kwargs):
        queryset = super().get_query_set(request, *args, **kwargs)

        filter_args = {}
        exclude_filter_args = {}

        for key, value in request.GET.items():
            if key.startswith('_'):
                continue

            args_list = filter_args

            try:
                potential_operator = key.split('__')[1]
            except IndexError:
                pass
            else:
                if potential_operator == 'in':
                    value = value.split(',')
                elif potential_operator == 'not_in':
                    value = value.split(',')
                    args_list = exclude_filter_args

            args_list[key] = value

        return queryset.filter(**filter_args).exclude(**exclude_filter_args)


class SoftDeletableDetailEndpointMixin:

    def serialize(self, data):
        return serialize(data, exclude=['deleted'])

    @block_fields(('deleted',))
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @block_fields(('deleted',))
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        instance = self.get_instance(request, *args, **kwargs)

        old_deleted_status = instance.deleted
        if not old_deleted_status:
            instance.deleted = True
            instance.save()

        return {}


class SoftDeletableListEndpointMixin:

    @block_fields(('deleted',))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def serialize(self, data):
        return serialize(data, exclude=['deleted'])

    def get_query_set(self, request, *args, **kwargs):
        queryset = super().get_query_set(request, *args, **kwargs)
        return queryset.filter(deleted=False)
