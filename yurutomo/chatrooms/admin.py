from django.contrib import admin


from .models import Room, MatchingRecord, Topic, Tag


# Register your models here.
admin.site.register(Room)
admin.site.register(MatchingRecord)
admin.site.register(Topic)
admin.site.register(Tag)