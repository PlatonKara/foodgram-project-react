from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .validators import ValidateUsername


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, ValidateUsername):
    email = models.EmailField('Почта', max_length=254, unique=True)
    username = models.CharField('Username', max_length=150, unique=True)
    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name', 'username')

    class Meta:
        ordering = ['username']
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
