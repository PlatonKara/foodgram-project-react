from django.contrib.auth.models import AbstractUser
from django.db import models

from api.const import EMAIL_LENGTH, NAMES_PASSWORD_LENGTH

from .validators import ValidateUsername


class User(AbstractUser, ValidateUsername):
    """Кастомная модель User для приложения."""

    email = models.EmailField(
        verbose_name='Почта',
        max_length=EMAIL_LENGTH,
        unique=True
    )
    username = models.CharField(
        verbose_name='Username',
        max_length=NAMES_PASSWORD_LENGTH,
        unique=True
    )
    first_name = models.CharField(verbose_name='Имя',
                                  max_length=NAMES_PASSWORD_LENGTH)
    last_name = models.CharField(verbose_name='Фамилия',
                                 max_length=NAMES_PASSWORD_LENGTH)
    password = models.CharField(verbose_name='Пароль',
                                max_length=NAMES_PASSWORD_LENGTH)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'username', 'password',)

    class Meta:
        ordering = ('username',)
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return self.username


class Subscribe(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор'
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'подписчик'
        verbose_name_plural = 'подписчики'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique subscribe'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='cant subscribe to yourself',
            ),
        ]

    def __str__(self):
        return (
            f'Подписчик: {self.user.username}, Автор: {self.author.username}'
        )
