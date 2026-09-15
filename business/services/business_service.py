from django.db import transaction

from business.models import Business


def get_user_business(user):
    return Business.objects.filter(owner=user).first()


def require_user_business(user):
    business = get_user_business(user)

    if business is None:
        raise ValueError("Business has not been created yet.")

    return business


@transaction.atomic
def create_business(user, validated_data):
    if Business.objects.filter(owner=user).exists():
        raise ValueError("You already have a business.")

    return Business.objects.create(
        owner=user,
        **validated_data,
    )