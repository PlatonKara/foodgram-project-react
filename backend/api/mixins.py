from users.models import Subscribe


def check_request_return_boolean(obj, model, context):
    """Проверяем факт запроса"""

    request = context.get('request')
    user_id = (
        request.user.id if request and request.user.is_authenticated else None
    )

    if model == Subscribe:
        return model.objects.filter(user_id=user_id, author=obj.id).exists()
    return model.objects.filter(recipe=obj, user_id=user_id).exists()
