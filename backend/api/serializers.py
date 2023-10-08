from django.core import validators
from django.contrib.auth.hashers import make_password
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.const import MAX_AMOUNT, MAX_COOKING_TIME, MIN_AMOUNT
from api.mixins import check_request_return_boolean
from recipes.models import (Cart, Favorite, IngredientInRecipe, Ingredients,
                            Recipes, Tags)
from users.models import Subscribe, User


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор на модель User"""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        return check_request_return_boolean(obj, self.context, Subscribe)

    def create(self, validated_data):
        validated_data['password'] = (
            make_password(validated_data.pop('password'))
        )
        return super().create(validated_data)


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
                'На самого себя нельзя подписаться'
            )
        if data['user'].filter(author=data['author']).exists():
            raise serializers.ValidationError(
                'Подписка уже существует'
            )
        return data

    def to_representation(self, author):
        return super().to_representation(author)


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
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT, max_value=MAX_AMOUNT
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipesPostSerializer(serializers.ModelSerializer):
    """Сериализатор для создания, обновления и удаления рецептов (POST)."""

    tags = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = SimpleIngredientInRecipeSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        required=True, validators=[
            validators.MaxValueValidator(MAX_COOKING_TIME)
        ]
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
        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужен хотя бы один тэг для рецепта'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги в рецепте не должны повторяться'}
            )

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError('Изображение обязательно.')
        return value

    @staticmethod
    def create_ingredients(ingredients, recipe):
        ingredient_objects = []
        for ingredient_item in ingredients:
            ingredient = IngredientInRecipe(
                ingredient_id=ingredient_item['id'],
                recipe=recipe,
                amount=ingredient_item['amount']
            )
            ingredient_objects.append(ingredient)

        IngredientInRecipe.objects.bulk_create(ingredient_objects)

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


class RecipesGetSerializer(serializers.ModelSerializer):
    """Сериализатор (GET запросы)."""

    tags = TagsSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='ingredientinrecipe_set', many=True, read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipes
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time', 'is_faforited',
            'is_in_shoping_cart'
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


class CartSerializer(FavoriteSerializer):
    class Meta(FavoriteSerializer.Meta):
        model = Cart
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(

                'Этот рецепт уже в корзине пользователя.'
            )
        return data
