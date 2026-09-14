from django.db import models


class Customer(models.Model):
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="customers",
    )

    name = models.CharField(max_length=255)

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name