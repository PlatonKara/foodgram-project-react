from django.db.models import Sum
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientsFilter, RecipesFilterSet
from api.permissions import IsOwnerOrReadOnly
from api.serializers import (CartSerializer, FavoriteSerializer,
                             IngredientsSerializer, RecipesGetSerializer,
                             RecipesPostSerializer, SubscribeGetSerializer,
                             TagsSerializer, UserSerializer)
from api.utils import download_pdf
from recipes.models import (Cart, Favorite, IngredientInRecipe, Ingredients,
                            Recipes, Tags)
from users.models import Subscribe, User


class UserViewSet(DjoserUserViewSet):
    """Вьюсет для модели User и Subscribe"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get_permissions(self):
        """Возвращает список разрешений, которые должны быть применены"""
        if self.action == 'me':
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @action(
        methods=['get'], detail=False,
        permission_classes=[IsAuthenticated],
        pagination_class=PageNumberPagination
    )
    def subscriptions(self, request):
        """Получить подписки пользователя"""

        serializer = SubscribeGetSerializer(
            self.paginate_queryset(
                Subscribe.objects.filter(user=request.user)
            ), many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=['post'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk):
        """Функция подписки."""

        data = {
            'user': request.user.id,
            'author': pk
        }
        serializer = SubscribeGetSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        methods=['delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def unsubscribe(self, request, id):
        """Функция отписки."""
        instance = get_object_or_404(
            Subscribe, user=request.user, author_id=id
        )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели Ingredients"""

    serializer_class = IngredientsSerializer
    queryset = Ingredients.objects.all()
    pagination_class = None
    filter_backends = [IngredientsFilter, ]
    search_fields = ('^name',)


class TagsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели Tags"""

    serializer_class = TagsSerializer
    queryset = Tags.objects.all()
    pagination_class = None


class RecipesViewSet(ModelViewSet):
    """Вьюсет для модели Recipes, Favorite и Cart"""

    queryset = Recipes.objects.select_related('author').prefetch_related(
        'tags', 'ingredients'
    )
    pagination_class = PageNumberPagination
    permission_classes = [IsOwnerOrReadOnly]
    filterset_class = RecipesFilterSet

    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return RecipesPostSerializer
        return RecipesGetSerializer

    @action(
        methods=['post'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def add_to_favorite(self, request, pk):
        """Функция добавления в избранное."""
        return self.create_entry(FavoriteSerializer, pk, request)

    @action(
        methods=['delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def remove_from_favorite(self, request, pk):
        """Функция удаления из избранного."""
        return self.delete_entry(Favorite, pk, request)

    @action(
        methods=['post'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def add_to_shopping_cart(self, request, pk):
        """Функция добавления рецепта в список покупок."""
        return self.create_entry(CartSerializer, pk, request)

    @action(
        methods=['delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def remove_from_shopping_cart(self, request, pk):
        """Функция удаления рецепта из списка покупок."""
        return self.delete_entry(Cart, pk, request)

    @action(
        methods=['get'], detail=False, permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список покупок в pdf"""
        ingredients = IngredientInRecipe.objects.filter(
            recipe__cart__user=request.user).values_list(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(Sum('amount')).order_by('name')

        if ingredients:
            return download_pdf(request, ingredients)
        return Response(
            {'errors': 'Нет рецептов в списке покупок'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def create_entry(serializer_class, pk, request):
        data = {
            'user': request.user.id,
            'recipe': pk
        }
        serializer = serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def delete_entry(model, pk, request):
        instance = get_object_or_404(model, user=request.user, recipe=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
