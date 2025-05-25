from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('stock/<str:symbol>/', views.stock_detail, name='stock_detail'),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('portfolio/add/', views.add_to_portfolio, name='add_to_portfolio'),
    path('portfolio/<int:stock_id>/edit/', views.edit_portfolio_item, name='edit_portfolio_item'),
    path('portfolio/<int:stock_id>/delete/', views.delete_portfolio_item, name='delete_portfolio_item'),
    path('news/', views.news_view, name='news'),
    path('prediction/', views.prediction_view, name='prediction'),
    path('prediction/<str:symbol>/', views.prediction_view, name='prediction_with_symbol'),
    path('strategy/', views.strategy_view, name='strategy'),
    path('strategy/<str:symbol>/', views.strategy_view, name='strategy_with_symbol'),
]