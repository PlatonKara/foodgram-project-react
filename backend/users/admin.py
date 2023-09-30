from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Subscribe, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'id', 'username', 'email', 'first_name', 'last_name',
        'get_recipes_count', 'get_subscriptions_count'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('username', 'email', 'first_name', 'last_name', )

    @admin.display(description='Количество рецептов')
    def get_recipes_count(self, obj):
        return obj.recipe_author.count()

    @admin.display(description='Количество подписчиков')
    def get_subscriptions_count(self, obj):
        return obj.following.count()


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user', 'author')
    autocomplete_fields = ('user', 'author')
