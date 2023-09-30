from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from users.models import Subscribe


def check_request_return_boolean(self, obj, model):
    """Проверяем факт запроса"""

    request = self.context.get('request')
    user_id = (
        request.user.id if request and request.user.is_authenticated else None
    )

    if model == Subscribe:
        return model.objects.filter(user_id=user_id, author=obj.id).exists()
    return model.objects.filter(recipe=obj, user_id=user_id).exists()


class FavoriteCart:
    add_model = None
    add_serializer = None

    def favorite_and_cart(self, request, obj_id, model, errors):
        user = request.user
        obj = model.objects.filter(user=user, recipe=obj_id)
        if request.method == 'POST':
            if obj.exists():
                return Response(
                    {'errors': errors.get('if_exists')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj = get_object_or_404(self.add_model, id=obj_id)
            model.objects.create(user=user, recipe=obj)
            return Response(
                self.add_serializer(obj).data, status=status.HTTP_201_CREATED
            )
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': errors.get('if_deleted')},
            status=status.HTTP_400_BAD_REQUEST
        )
