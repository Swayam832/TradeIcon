from django.urls import path
from . import views
from . import stock_api
from . import watchlist_api

app_name = 'api'

urlpatterns = [
    path('stocks/search/', stock_api.search_stocks, name='stock_search'),
    path('stocks/<str:symbol>/', stock_api.get_stock_data, name='stock_data'),
    path('watchlist/', watchlist_api.WatchlistAPIView.as_view(), name='watchlist'),
    path('watchlist/add-stock/', watchlist_api.add_stock_to_watchlist, name='add_stock_to_watchlist'),
    path('watchlist/remove-stock/', watchlist_api.remove_stock_from_watchlist, name='remove_stock_from_watchlist'),
    path('watchlist/edit/', watchlist_api.edit_watchlist, name='edit_watchlist'),
    path('watchlist/delete/', watchlist_api.delete_watchlist, name='delete_watchlist'),
    path('strategy/<str:symbol>/', views.StrategyAPIView.as_view(), name='strategy'),
    path('prediction/<str:symbol>/', views.PredictionAPIView.as_view(), name='prediction'),
]