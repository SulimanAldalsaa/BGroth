from django.db import IntegrityError

from rest_framework.exceptions import ValidationError

from business.models import Business


class BusinessService:

    @staticmethod
    def create_business(*, owner, name, description=""):
        if Business.objects.filter(owner=owner).exists():
            raise ValidationError(
                {
                    "business": (
                        "This user already has a business."
                    )
                }
            )

        try:
            return Business.objects.create(
                owner=owner,
                name=name,
                description=description,
            )
        except IntegrityError:
            raise ValidationError(
                {
                    "business": (
                        "This user already has a business."
                    )
                }
            )