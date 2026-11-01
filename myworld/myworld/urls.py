"""URL configuration of the line-selection project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('line.urls')),
    path('line/', include('line.urls')),
    path('line/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('', include('user_sessions.urls', 'user_sessions')),
]
