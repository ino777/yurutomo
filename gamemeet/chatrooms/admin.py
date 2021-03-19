from django.contrib import admin


from .models import Room, MatchingRecord


# Register your models here.
admin.site.register(Room)
admin.site.register(MatchingRecord)