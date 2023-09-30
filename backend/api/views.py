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
from api.mixins import FavoriteCart
from api.permissions import IsAdminAuthorOrReadOnly
from api.serializers import (UserSerializer, IngredientsSerializer,
                             RecipesPostSerializer, RecipesGetSerializer,
                             ShortSerializer, SubscribePostSerializer,
                             SubscribeGetSerializer, TagsSerializer,
                             FavoriteSerializer, CartSerializer)
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
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Получить данные текущего пользователя"""
        return Response(
            UserSerializer(
                get_object_or_404(User, id=request.user.id)).data,
            status=status.HTTP_200_OK
        )

    @action(
        methods=['get'], detail=False,
        permission_classes=[IsAuthenticated],
        pagination_class=PageNumberPagination
    )
    def subscriptions(self, request):
        """Получить подписки пользователя"""

        serializer = SubscribeGetSerializer(
            self.paginate_queryset(
                Subscribe.objects.filter(author=request.user)
            ), many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=['post', 'delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        """Функция подписки и отписки."""

        user = request.user
        obj = Subscribe.objects.filter(user=user, author_id=id)

        if request.method == 'POST':
            if obj.exists():
                return Response(
                    {'errors': f'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = {
                'user': user.id,
                'author': id
            }
            serializer = SubscribeGetSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == 'DELETE':
            return self.delete_subscription(request, obj)
        
    def delete_subscription(self, request, obj):
        """Метод для удаления подписки."""
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': f'Вы уже отписались от этого пользователя'},
            status=status.HTTP_400_BAD_REQUEST
        )


class IngredientsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели Ingredients"""

    serializer_class = IngredientsSerializer
    queryset = Ingredients.objects.all()
    pagination_class = None
    filter_backends = [IngredientsFilter,]
    search_fields = ('^name',)


class TagsViewSet(ReadOnlyModelViewSet):
    """Вьюсет для модели Tags"""

    serializer_class = TagsSerializer
    queryset = Tags.objects.all()
    pagination_class = None


class RecipesViewSet(ModelViewSet, FavoriteCart):
    """Вьюсет для модели Recipes, Favorite и Cart"""

    queryset = Recipes.objects.select_related('author').prefetch_related(
        'tags', 'ingredients'
        )
    pagination_class = PageNumberPagination
    permission_classes = [IsAdminAuthorOrReadOnly]
    filterset_class = RecipesFilterSet
    add_serializer = ShortSerializer
    add_model = Recipes

    def get_serializer_class(self):
        if self.request.method in ['POST', 'PUT', 'PATCH']:
            return RecipesPostSerializer
        return RecipesGetSerializer

    @action(
        methods=['post', 'delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        """Функция добавления и удаления избранного."""

        if request.method == 'POST':
            return self.create_entry(FavoriteSerializer, pk, request)
        if request.method == 'DELETE':
            return self.delete_entry(Favorite, pk, request)

    @action(
        methods=['post', 'delete'],
        detail=True, permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        """Функция добавления и удаления рецептов в/из списка покупок."""
        if request.method == 'POST':
            return self.create_entry(CartSerializer, pk, request)
        if request.method == 'DELETE':
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
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @staticmethod
    def delete_entry(model, pk, request):
        obj = model.objects.filter(user=request.user, recipe=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Объект не найден.'},
            status=status.HTTP_400_BAD_REQUEST
        )
