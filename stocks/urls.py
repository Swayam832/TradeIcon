from django.urls import path
from . import views

app_name = 'stocks'

urlpatterns = [
    # These will be implemented later as needed
    path('search/', views.search_stocks, name='search'),
]