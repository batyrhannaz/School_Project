def role_of(user):
    """teacher / parent / student / staff / None"""
    if not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    if profile:
        return profile.role
    return "staff" if user.is_staff else None


def class_of(user):
    profile = getattr(user, "profile", None)
    return profile.school_class if profile else None
