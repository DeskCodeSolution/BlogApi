from django.contrib import admin
# from django.contrib.auth.models import User
from .models import *
admin.site.register(Post)
admin.site.register(Category)
admin.site.register(Comment)

# Register your models here.
