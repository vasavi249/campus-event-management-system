from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.views.static import serve
from django.urls import re_path

from events.views import safe_media_serve

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', safe_media_serve),
    path('admin/', admin.site.urls),
    path('', include('events.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = 'events.views.custom_404_view'
