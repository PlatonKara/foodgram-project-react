from colorfield.fields import ColorField
from django.core import validators
from django.db import models

from users.models import User


class Ingredients(models.Model):
    """Модель ингредиентов"""

    name = models.CharField(
        'Название', max_length=200, db_index=True
    )
    measurement_unit = models.CharField(
        'Ед. измерения', max_length=200
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'ингредиенты'
        verbose_name_plural = 'ингредиент'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'], name='unique ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Tags(models.Model):
    """Модель тэгов"""

    name = models.CharField(
        'Название тега', max_length=200, unique=True
    )
    color = ColorField(
        'Цвет', format='hex', max_length=7, unique=True
    )
    slug = models.SlugField(
        'Ссылка', max_length=200,
        unique=True
    )

    REQUIRED_FIELDS = ['name', 'color', 'slug']

    class Meta:
        ordering = ('id',)
        verbose_name = 'тэг'
        verbose_name_plural = 'теги'

    def __str__(self):
        return self.name


class Recipes(models.Model):
    """Модель рецептов"""

    name = models.CharField(
        'Название рецепта', max_length=200
    )
    text = models.TextField('Описание')
    image = models.ImageField('Картинка', upload_to='recipes/%Y/%m/%d/')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления', validators=[validators.MaxValueValidator]
    )
    pub_date = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tags, verbose_name='теги')
    ingredients = models.ManyToManyField(
        Ingredients, through='IngredientInRecipe', verbose_name='Ингредиенты'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='recipe_author', verbose_name='Автор'
    )

    REQUIRED_FIELDS = [
        'name', 'text', 'image', 'cooking_time',
        'tags', 'ingredients', 'author'
    ]

    class Meta:
        ordering = ('pub_date',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'рецепты'

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Модель ингредиентов в рецепте"""

    ingredient = models.ForeignKey(
        Ingredients, on_delete=models.CASCADE, verbose_name='Ингредиент'
    )
    recipe = models.ForeignKey(
        Recipes, on_delete=models.CASCADE, verbose_name='Рецепт'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество', validators=[validators.MaxValueValidator]
    )

    class Meta:
        ordering = ('-id',)
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique ingredient in recipe'
            )
        ]

    def __str__(self):
        return f'{self.ingredient}'


class FavoriteInCart(models.Model):
    """Абстрактная модель для избранного и списка покупок."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='пользователь'
    )
    recipe = models.ForeignKey(
        Recipes, on_delete=models.CASCADE, verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        ordering = ('-id',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'], name='%(class)s_unique'
            )
        ]

    def __str__(self):
        return f'Пользователь:{self.user.username}, рецепт: {self.recipe.name}'


class Favorite(FavoriteInCart):
    """Модель избранного"""

    class Meta(FavoriteInCart.Meta):
        default_related_name = 'favorite'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class Cart(FavoriteInCart):
    """Модель списка покупок"""

    class Meta(FavoriteInCart.Meta):
        default_related_name = 'cart'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
