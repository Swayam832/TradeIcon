from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Stock, Watchlist
from api.angel_api import AngelBrokingAPI
from django.core.paginator import Paginator
from django.db.models import Q
import json

@login_required
def search_stocks(request):
    query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    stocks = []
    
    if query:
        # Search in local database first
        stocks = Stock.objects.filter(
            Q(symbol__icontains=query) | 
            Q(name__icontains=query)
        )
        
        # If no results or less than 5 results, search via API
        if len(stocks) < 5:
            api = AngelBrokingAPI()
            api_results = api.search_stocks(query)
            
            # Update or create stock records
            for stock_data in api_results:
                stock, created = Stock.objects.update_or_create(
                    symbol=stock_data['symbol'],
                    defaults={
                        'name': stock_data['name'],
                        'current_price': stock_data.get('current_price'),
                        'previous_close': stock_data.get('previous_close'),
                        'change': stock_data.get('change'),
                        'change_percent': stock_data.get('change_percent')
                    }
                )
                
            # Refresh queryset with new data
            stocks = Stock.objects.filter(
                Q(symbol__icontains=query) | 
                Q(name__icontains=query)
            )
    
    # Pagination
    paginator = Paginator(stocks, 10)
    stocks_page = paginator.get_page(page)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        stock_list = [{
            'symbol': stock.symbol,
            'name': stock.name,
            'current_price': float(stock.current_price) if stock.current_price else None,
            'change': float(stock.change) if stock.change else None,
            'change_percent': float(stock.change_percent) if stock.change_percent else None,
            'in_watchlist': Watchlist.objects.filter(user=request.user, stocks=stock).exists()
        } for stock in stocks_page]
        
        return JsonResponse({
            'stocks': stock_list,
            'has_next': stocks_page.has_next(),
            'has_previous': stocks_page.has_previous(),
            'total_pages': paginator.num_pages
        })
    
    context = {
        'query': query,
        'stocks': stocks_page
    }
    
    return render(request, 'stocks/search.html', context)
