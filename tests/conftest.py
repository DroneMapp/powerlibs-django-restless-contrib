import pytest
from unittest import mock
from django.core.exceptions import FieldError

from powerlibs.django.restless.contrib.endpoints import (PaginatedEndpointMixin, FilteredEndpointMixin,
                                                         SoftDeletableDetailEndpointMixin, SoftDeletableListEndpointMixin,
                                                         OrderedEndpointMixin)
from powerlibs.django.restless.contrib.endpoints.nested import NestedEntitiesDetailEndpointMixin, NestedEntitiesListEndpointMixin


class MockedQuerySet(list):
    def count(self):
        return len(self)

    def __getitem__(self, slice):
        results = super().__getitem__(slice)
        if isinstance(results, list):
            return MockedQuerySet(results)
        else:
            return results

    def order_by(self, key):
        if key not in ('id', 'deleted'):
            raise FieldError('No such field')

        unordered = super().__getitem__(slice(0, None))
        ordered = sorted(unordered, key=lambda x: getattr(x, key))
        return MockedQuerySet(ordered)

    def filter(self, **kwargs):
        results = []
        for item in self:
            for key, expected_value in kwargs.items():
                value = getattr(item, key)
                if value == expected_value:
                    results.append(item)

        return MockedQuerySet(results)

    def exclude(self, **kwargs):
        for item in self:
            for key, expected_value in kwargs.items():
                value = getattr(item, key)
                if value == expected_value:
                    self.remove(item)
                    break

        return self


@pytest.fixture
def instances():
    return (
        mock.Mock(id=1, deleted=False),
        mock.Mock(id=2, deleted=False),
        mock.Mock(id=3, deleted=False),
        mock.Mock(id=4, deleted=True),
        mock.Mock(id=5, deleted=True),
        mock.Mock(id=7, deleted=True),
    )


@pytest.fixture
def mocked_queryset(instances):
    return MockedQuerySet(instances)


class Endpoint:
    get_query_set = mock.Mock(return_value=mocked_queryset(instances()))


class DetailEndpoint(Endpoint):
    field_1 = mock.Mock()
    field_1.configure_mock(name='id')
    field_2 = mock.Mock()
    field_2.configure_mock(name='name')

    related_model = mock.Mock()
    related_model.configure_mock(name='related_model')
    foreign_keys = ['related_model']

    get = mock.Mock(return_value={
        'id': 1,
        'name': 'TEST NAME',
    })

    get_instance = mock.Mock(return_value=instances()[0])
    model = mock.Mock(
        _meta=mock.Mock(
            fields=(field_1, field_2)
        )
    )


class ListEndpoint(DetailEndpoint):
    get = mock.Mock(return_value=[
        {
            'id': 1,
            'name': 'TEST 1',
        },
        {
            'id': 2,
            'name': 'TEST 2',
        },
    ])


@pytest.fixture
def filtered_endpoint():
    class MyClass(FilteredEndpointMixin, Endpoint):
        pass

    return MyClass()


@pytest.fixture
def original_filtered_endpoint():
    class MyClass(FilteredEndpointMixin, DetailEndpoint):
        pass

    return MyClass()


@pytest.fixture
def paginated_endpoint():
    class MyClass(PaginatedEndpointMixin, Endpoint):
        def serialize(self, arg):
            return arg

    return MyClass()


@pytest.fixture
def soft_deletable_detail_endpoint():
    instance = mock.Mock(deleted=False)

    class MyClass(SoftDeletableDetailEndpointMixin):
        get_instance = mock.Mock(return_value=instance)

    obj = MyClass()
    obj.instance = instance
    return obj


@pytest.fixture
def soft_deletable_detail_endpoint_with_deleted_instance():
    instance = mock.Mock(deleted=True)

    class MyClass(SoftDeletableDetailEndpointMixin):
        get_instance = mock.Mock(return_value=instance)

    obj = MyClass()
    obj.instance = instance
    return obj


@pytest.fixture
def soft_deletable_list_endpoint():
    class MyClass(SoftDeletableListEndpointMixin, Endpoint):
        pass
    obj = MyClass()
    return obj


@pytest.fixture
def soft_deletable_list_endpoint_no_field_deleted():
    class MyClass(SoftDeletableListEndpointMixin, Endpoint):
        pass

    obj = MyClass()
    data = obj.get_query_set(None)
    for d in data:
        del d.__dict__['deleted']
    return data


@pytest.fixture
def nested_list_endpoint():
    class MyClass(NestedEntitiesListEndpointMixin, ListEndpoint):
        pass

    obj = MyClass()
    return obj


@pytest.fixture
def nested_detail_endpoint():
    class MyClass(NestedEntitiesDetailEndpointMixin, DetailEndpoint):
        pass

    obj = MyClass()
    return obj


@pytest.fixture
def ordered_list_endpoint():
    class MyClass(OrderedEndpointMixin, DetailEndpoint):
        pass

    obj = MyClass()
    return obj
