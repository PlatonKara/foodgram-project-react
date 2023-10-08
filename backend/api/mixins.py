from users.models import Subscribe


def check_request_return_boolean(obj, context, model_class):
    """Проверяем факт запроса"""

    request = context.get('request')
    user_id = (
        request.user.id if request and request.user.is_authenticated else None
    )
    filter_criteria = {
        'user_id': user_id, 'author': obj.id
    } if model_class == Subscribe else {'recipe': obj, 'user_id': user_id}
    return model_class.objects.filter(**filter_criteria).exists()
