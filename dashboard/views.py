from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from stocks.models import Stock, Watchlist, Portfolio, StockNews, StockPrediction, TradeSignal
from django.core.paginator import Paginator
from django.db.models import F, ExpressionWrapper, DecimalField, Sum
from decimal import Decimal
from api.angel_api import AngelBrokingAPI
from api.prediction import predict_stock_price
from api.strategy import enhanced_pullback_strategy
import json

def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, 'dashboard/home.html')
        
    # Get user's watchlists
    watchlists = Watchlist.objects.filter(user=request.user)
    
    # Get user's portfolio
    portfolio_items = Portfolio.objects.filter(user=request.user)
    
    # Calculate portfolio summary
    total_investment = sum(item.quantity * item.buy_price for item in portfolio_items)
    current_value = sum(item.quantity * item.stock.current_price for item in portfolio_items if item.stock.current_price)
    profit_loss = current_value - total_investment
    profit_loss_percent = (profit_loss / total_investment * 100) if total_investment > 0 else 0
    
    # Get latest news
    latest_news = StockNews.objects.order_by('-published_at')[:5]
    
    # Get trending stocks (simplified for demo)
    trending_stocks = Stock.objects.filter(current_price__isnull=False).order_by('-change_percent')[:5]
    
    context = {
        'watchlists': watchlists,
        'portfolio_items': portfolio_items,
        'total_investment': total_investment,
        'current_value': current_value,
        'profit_loss': profit_loss,
        'profit_loss_percent': profit_loss_percent,
        'latest_news': latest_news,
        'trending_stocks': trending_stocks
    }
    
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def portfolio(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'add':
            symbol = data.get('symbol')
            quantity = Decimal(data.get('quantity'))
            buy_price = Decimal(data.get('buy_price'))
            
            stock = get_object_or_404(Stock, symbol=symbol)
            
            portfolio_item, created = Portfolio.objects.get_or_create(
                user=request.user,
                stock=stock,
                defaults={'quantity': quantity, 'buy_price': buy_price}
            )
            
            if not created:
                # Update existing position
                avg_price = ((portfolio_item.quantity * portfolio_item.buy_price) + (quantity * buy_price)) / (portfolio_item.quantity + quantity)
                portfolio_item.quantity += quantity
                portfolio_item.buy_price = avg_price
                portfolio_item.save()
            
            return JsonResponse({'status': 'success'})
            
        elif action == 'edit':
            item_id = data.get('id')
            quantity = Decimal(data.get('quantity'))
            buy_price = Decimal(data.get('buy_price'))
            
            portfolio_item = get_object_or_404(Portfolio, id=item_id, user=request.user)
            portfolio_item.quantity = quantity
            portfolio_item.buy_price = buy_price
            portfolio_item.save()
            
            return JsonResponse({'status': 'success'})
            
        elif action == 'delete':
            item_id = data.get('id')
            portfolio_item = get_object_or_404(Portfolio, id=item_id, user=request.user)
            portfolio_item.delete()
            
            return JsonResponse({'status': 'success'})
    
    portfolio_items = Portfolio.objects.filter(user=request.user)
    
    # Calculate portfolio summary
    total_investment = sum(item.quantity * item.buy_price for item in portfolio_items)
    current_value = sum(item.quantity * item.stock.current_price for item in portfolio_items if item.stock.current_price)
    profit_loss = current_value - total_investment
    profit_loss_percent = (profit_loss / total_investment * 100) if total_investment > 0 else 0
    
    context = {
        'portfolio_items': portfolio_items,
        'total_investment': total_investment,
        'current_value': current_value,
        'profit_loss': profit_loss,
        'profit_loss_percent': profit_loss_percent
    }
    
    return render(request, 'dashboard/portfolio.html', context)

@login_required
def stock_detail(request, symbol):
    stock = get_object_or_404(Stock, symbol=symbol)
    
    # Check if stock is in user's watchlist
    in_watchlist = False
    for watchlist in Watchlist.objects.filter(user=request.user):
        if stock in watchlist.stocks.all():
            in_watchlist = True
            break
    
    # Check if stock is in user's portfolio
    in_portfolio = Portfolio.objects.filter(user=request.user, stock=stock).exists()
    
    # Get stock news
    stock_news = StockNews.objects.filter(stock=stock).order_by('-published_at')[:10]
    
    context = {
        'stock': stock,
        'in_watchlist': in_watchlist,
        'in_portfolio': in_portfolio,
        'stock_news': stock_news
    }
    
    return render(request, 'dashboard/stock_detail.html', context)

@login_required
def watchlist_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        
        if action == 'create':
            name = data.get('name')
            watchlist = Watchlist.objects.create(user=request.user, name=name)
            return JsonResponse({'status': 'success', 'id': watchlist.id})
            
        elif action == 'add':
            watchlist_id = data.get('watchlist_id')
            symbol = data.get('symbol')
            
            watchlist = get_object_or_404(Watchlist, id=watchlist_id, user=request.user)
            stock = get_object_or_404(Stock, symbol=symbol)
            
            watchlist.stocks.add(stock)
            return JsonResponse({'status': 'success'})
            
        elif action == 'remove':
            watchlist_id = data.get('watchlist_id')
            symbol = data.get('symbol')
            
            watchlist = get_object_or_404(Watchlist, id=watchlist_id, user=request.user)
            stock = get_object_or_404(Stock, symbol=symbol)
            
            watchlist.stocks.remove(stock)
            return JsonResponse({'status': 'success'})
            
        elif action == 'delete':
            watchlist_id = data.get('id')
            watchlist = get_object_or_404(Watchlist, id=watchlist_id, user=request.user)
            watchlist.delete()
            return JsonResponse({'status': 'success'})
    
    watchlists = Watchlist.objects.filter(user=request.user)
    
    context = {
        'watchlists': watchlists
    }
    
    return render(request, 'dashboard/watchlist.html', context)

@login_required
def portfolio_view(request):
    portfolio_items = Portfolio.objects.filter(user=request.user)
    
    # Calculate portfolio summary
    total_investment = sum(item.quantity * item.buy_price for item in portfolio_items)
    current_value = sum(item.quantity * item.stock.current_price for item in portfolio_items if item.stock.current_price)
    profit_loss = current_value - total_investment
    profit_loss_percent = (profit_loss / total_investment * 100) if total_investment > 0 else 0
    
    context = {
        'portfolio_items': portfolio_items,
        'total_investment': total_investment,
        'current_value': current_value,
        'profit_loss': profit_loss,
        'profit_loss_percent': profit_loss_percent
    }
    
    return render(request, 'dashboard/portfolio.html', context)

@login_required
def add_to_portfolio(request):
    if request.method == 'POST':
        try:
            symbol = request.POST.get('symbol')
            quantity = Decimal(request.POST.get('quantity'))
            buy_price = Decimal(request.POST.get('buy_price'))
            buy_date = request.POST.get('buy_date')
            
            stock = get_object_or_404(Stock, symbol=symbol)
            
            portfolio_item, created = Portfolio.objects.get_or_create(
                user=request.user,
                stock=stock,
                defaults={
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'buy_date': buy_date
                }
            )
            
            if not created:
                # Update existing position
                avg_price = ((portfolio_item.quantity * portfolio_item.buy_price) + (quantity * buy_price)) / (portfolio_item.quantity + quantity)
                portfolio_item.quantity += quantity
                portfolio_item.buy_price = avg_price
                portfolio_item.save()
            
            return JsonResponse({'status': 'success'})
            
        except (ValueError, TypeError) as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
        except Stock.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'Stock not found'}, status=404)
    
    return JsonResponse({'status': 'error', 'error': 'Invalid request method'}, status=405)

@login_required
def edit_portfolio_item(request, stock_id):
    portfolio_item = get_object_or_404(Portfolio, id=stock_id, user=request.user)
    
    if request.method == 'POST':
        try:
            quantity = Decimal(request.POST.get('quantity'))
            buy_price = Decimal(request.POST.get('buy_price'))
            
            portfolio_item.quantity = quantity
            portfolio_item.buy_price = buy_price
            portfolio_item.save()
            
            return JsonResponse({'status': 'success'})
            
        except (ValueError, TypeError) as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'error': 'Invalid request method'}, status=405)

@login_required
def delete_portfolio_item(request, stock_id):
    portfolio_item = get_object_or_404(Portfolio, id=stock_id, user=request.user)
    
    if request.method == 'POST':
        portfolio_item.delete()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'error': 'Invalid request method'}, status=405)
    
    return render(request, 'dashboard/portfolio.html', context)

@login_required
def news_view(request):
    search_query = request.GET.get('search', '')
    
    if search_query:
        news_list = StockNews.objects.filter(title__icontains=search_query).order_by('-published_at')
    else:
        news_list = StockNews.objects.all().order_by('-published_at')
    
    paginator = Paginator(news_list, 10)  # Show 10 news items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'news_list': page_obj,
        'search_query': search_query
    }
    
    return render(request, 'dashboard/news.html', context)

@login_required
def prediction_view(request, symbol=None):
    stock = None
    if symbol:
        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            pass
    
    context = {
        'stock': stock
    }
    
    return render(request, 'dashboard/prediction.html', context)

@login_required
def strategy_view(request, symbol=None):
    stock = None
    if symbol:
        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            pass
    
    context = {
        'stock': stock
    }
    
    return render(request, 'dashboard/strategy.html', context)
