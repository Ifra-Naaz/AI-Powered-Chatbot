
from django.contrib import admin
from django.urls import path
from chat import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("conversations/", views.conversation_list, name="conversation_list"),
    path("conversations/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path(
    "conversations/<int:conversation_id>/delete/",
    views.delete_conversation,
    name="delete_conversation"
),
]
