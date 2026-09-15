from rest_framework.exceptions import NotFound


def get_user_business(user):
    business = getattr(user, "business", None)
    if business is None:
        raise NotFound(detail="Business not found. Please create a business first.")
    return business