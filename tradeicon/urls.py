from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('stocks/', include('stocks.urls')),
    path('users/', include('users.urls', namespace='users')),
    path('api/', include('api.urls')),
]
