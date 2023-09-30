from django_filters import NumberFilter
from django_filters.rest_framework import FilterSet, filters
from rest_framework.filters import SearchFilter

from recipes.models import Recipes


class IngredientsFilter(SearchFilter):
    """Полнотекстовый поиск по ингредиентам"""

    def get_search_fields(self, view, request):
        if request.query_params.get('name'):
            return ['name']
        return super().get_search_fields(view, request)
    search_param = 'name'


class RecipesFilterSet(FilterSet):
    """Фильтр рецептов по тегам, авторам, избранному, подпискам"""

    tags = filters.AllValuesMultipleFilter(field_name='tags__slug')
    is_favorited = NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(method='filter_shopping_cart')

    def filter_is_favorited(self, queryset, is_favorited, number):
        """Фильтрация по избранному"""
        if number:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def filter_shopping_cart(self, queryset, is_in_shopping_cart, number):
        """Фильтрация по списку покупок"""
        if number:
            return queryset.filter(cart__user=self.request.user)
        return queryset

    class Meta:
        model = Recipes
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')
