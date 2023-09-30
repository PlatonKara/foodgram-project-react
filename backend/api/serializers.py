from django.core import validators
from django.db import transaction
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.mixins import check_request_return_boolean
from recipes.models import (Cart, Favorite, IngredientInRecipe, Ingredients,
                            Recipes, Tags)
from users.models import Subscribe, User


class UserSerializer(DjoserUserSerializer):
    """Сериализатор на модель User"""
    password = serializers.CharField(write_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'password'
        )

    def get_is_subscribed(self, obj):
        return check_request_return_boolean(self, obj, Subscribe)


class ShortSerializer(serializers.ModelSerializer):
    """Сериализатор короткого ответа рецептов для подписок и избранного"""

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribePostSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscribe
        fields = ('user', 'author')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                "На самого себя нельзя подписаться"
            )
        return data

    def to_representation(self, instance):
        return super().to_representation(instance)


class SubscribeGetSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, obj):
        queryset = Recipes.objects.filter(author__in=obj.following.all())
        recipes_limit = self.context.get('request').GET.get('recipes_limit')
        if recipes_limit:
            try:
                limit = int(recipes_limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        return ShortSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipe_author.count()


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор на тэги"""

    class Meta:
        model = Tags
        fields = '__all__'


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор на ингредиенты"""

    class Meta:
        model = Ingredients
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор связанной модели ингредиентов и рецептов"""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class SimpleIngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор простой связанной модели ингредиентов и рецептов."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredients.objects.all())
    amount = serializers.IntegerField(validators=[
        validators.MinValueValidator(1),
        validators.MaxValueValidator(1000)
    ])

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipesPostSerializer(serializers.ModelSerializer):
    """Сериализатор для создания, обновления и удаления рецептов (POST)."""

    tags = TagsSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = SimpleIngredientInRecipeSerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    name = serializers.CharField(required=True, max_length=200)
    image = Base64ImageField(
        max_length=None, required=True,
        allow_null=False, allow_empty_file=False
    )
    text = serializers.CharField(required=True)
    cooking_time = serializers.IntegerField(
        required=True, validators=[validators.MaxValueValidator(240)]
    )

    class Meta:
        model = Recipes
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def validate(self, data):
        ingredients = data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужен хотя бы один ингредиент для рецепта'}
            )
        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться'}
            )

        existing_ingredient_ids = set(
            Ingredients.objects.filter(id__in=ingredient_ids).values_list(
                'id', flat=True
            )
        )
        if set(ingredient_ids) != existing_ingredient_ids:
            raise serializers.ValidationError(
                {'ingredients': 'Один или несколько ингредиентов не найдены'}
            )

        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужен хотя бы один тэг для рецепта'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги в рецепте не должны повторяться'}
            )

        existing_tag_ids = set(
            Tags.objects.filter(id__in=tags).values_list('id', flat=True)
        )
        if set(tags) != existing_tag_ids:
            raise serializers.ValidationError(
                {'tags': 'Один или несколько тегов не найдены'}
            )
        return data

    def create_ingredients(self, ingredients, recipe):
        for ingredient_item in ingredients:
            IngredientInRecipe.objects.create(
                ingredient_id=ingredient_item['id'],
                recipe=recipe,
                amount=ingredient_item['amount']
            )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(
            author=self.context['request'].user, **validated_data
        )
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        recipe.save()
        return recipe

    @transaction.atomic
    def update(self, recipe, validated_data):
        recipe.ingredients.clear()
        self.create_ingredients(validated_data.pop('ingredients'), recipe)
        tags = validated_data.pop('tags')
        recipe.tags.set(tags)
        return super().update(recipe, validated_data)

    def get_is_favorited(self, obj):
        return check_request_return_boolean(self, obj, Favorite)

    def get_is_in_shopping_cart(self, obj):
        return check_request_return_boolean(self, obj, Cart)


class RecipesGetSerializer(serializers.ModelSerializer):
    """Сериализатор (GET запросы)."""

    tags = TagsSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredientinrecipe_set', many=True, read_only=True
    )

    class Meta:
        model = Recipes
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time'
        )


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже добавлен в избранное.'
            )

        return data


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if Cart.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже в корзине пользователя.'
            )

        return data
