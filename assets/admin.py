
from django.contrib import admin
from .models import Department, Asset, AssetRequest

admin.site.register(Department)
admin.site.register(Asset)
admin.site.register(AssetRequest)
