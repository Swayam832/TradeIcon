// Stock search and watchlist management functionality

class WatchlistManager {
    constructor() {
        this.initializeEventListeners();
        this.searchDebounceTimer = null;
    }

    initializeEventListeners() {
        // Stock search
        document.querySelectorAll('.stock-search').forEach(input => {
            input.addEventListener('input', (e) => this.handleStockSearch(e));
        });

        // Create watchlist
        document.getElementById('confirmCreateWatchlist')?.addEventListener('click', () => this.createWatchlist());

        // Edit watchlist
        document.querySelectorAll('.edit-watchlist').forEach(button => {
            button.addEventListener('click', (e) => this.showEditWatchlistModal(e));
        });

        // Delete watchlist
        document.querySelectorAll('.delete-watchlist').forEach(button => {
            button.addEventListener('click', (e) => this.showDeleteWatchlistModal(e));
        });

        // Remove stock from watchlist
        document.querySelectorAll('.remove-stock').forEach(button => {
            button.addEventListener('click', (e) => this.removeStockFromWatchlist(e));
        });

        // Confirm edit watchlist
        document.getElementById('confirmEditWatchlist')?.addEventListener('click', () => this.editWatchlist());

        // Confirm delete watchlist
        document.getElementById('confirmDeleteWatchlist')?.addEventListener('click', () => this.deleteWatchlist());
    }

    handleStockSearch(event) {
        const input = event.target;
        const watchlistId = input.dataset.watchlist;
        const query = input.value.trim();
        const resultsContainer = document.getElementById(`search-results-${watchlistId}`);

        clearTimeout(this.searchDebounceTimer);

        if (query.length < 2) {
            resultsContainer.innerHTML = '';
            return;
        }

        this.searchDebounceTimer = setTimeout(() => {
            fetch(`/api/stocks/search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    resultsContainer.innerHTML = this.renderSearchResults(data, watchlistId);
                    this.initializeAddStockButtons();
                })
                .catch(error => {
                    console.error('Error searching stocks:', error);
                    resultsContainer.innerHTML = '<p class="text-danger">Error searching stocks. Please try again.</p>';
                });
        }, 300);
    }

    renderSearchResults(data, watchlistId) {
        if (!data.length) {
            return '<p>No stocks found. Try a different search term.</p>';
        }

        return `
            <div class="list-group mt-2">
                ${data.map(stock => `
                    <div class="list-group-item d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${stock.symbol}</strong> - ${stock.name}
                            <small class="d-block text-muted">${stock.exchange}</small>
                        </div>
                        <button class="btn btn-sm btn-primary add-stock" 
                                data-symbol="${stock.symbol}" 
                                data-watchlist="${watchlistId}">
                            <i class="fas fa-plus"></i> Add
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }

    initializeAddStockButtons() {
        document.querySelectorAll('.add-stock').forEach(button => {
            button.addEventListener('click', (e) => this.addStockToWatchlist(e));
        });
    }

    createWatchlist() {
        const nameInput = document.getElementById('watchlistName');
        const name = nameInput.value.trim();

        if (!name) {
            alert('Please enter a watchlist name');
            return;
        }

        fetch('/api/watchlist/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                throw new Error(data.error || 'Failed to create watchlist');
            }
        })
        .catch(error => {
            console.error('Error creating watchlist:', error);
            alert(error.message);
        });
    }

    addStockToWatchlist(event) {
        const button = event.target.closest('.add-stock');
        const symbol = button.dataset.symbol;
        const watchlistId = button.dataset.watchlist;

        fetch('/api/watchlist/add-stock/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                watchlist_id: watchlistId,
                symbol: symbol
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                throw new Error(data.error || 'Failed to add stock');
            }
        })
        .catch(error => {
            console.error('Error adding stock:', error);
            alert(error.message);
        });
    }

    removeStockFromWatchlist(event) {
        const button = event.target.closest('.remove-stock');
        const symbol = button.dataset.symbol;
        const watchlistId = button.dataset.watchlist;

        if (!confirm('Are you sure you want to remove this stock from the watchlist?')) {
            return;
        }

        fetch('/api/watchlist/remove-stock/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                watchlist_id: watchlistId,
                symbol: symbol
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                throw new Error(data.error || 'Failed to remove stock');
            }
        })
        .catch(error => {
            console.error('Error removing stock:', error);
            alert(error.message);
        });
    }

    showEditWatchlistModal(event) {
        const button = event.target.closest('.edit-watchlist');
        const id = button.dataset.id;
        const name = button.dataset.name;

        document.getElementById('editWatchlistId').value = id;
        document.getElementById('editWatchlistName').value = name;

        new bootstrap.Modal(document.getElementById('editWatchlistModal')).show();
    }

    showDeleteWatchlistModal(event) {
        const button = event.target.closest('.delete-watchlist');
        const id = button.dataset.id;

        document.getElementById('deleteWatchlistId').value = id;

        new bootstrap.Modal(document.getElementById('deleteWatchlistModal')).show();
    }

    editWatchlist() {
        const id = document.getElementById('editWatchlistId').value;
        const name = document.getElementById('editWatchlistName').value.trim();

        if (!name) {
            alert('Please enter a watchlist name');
            return;
        }

        fetch('/api/watchlist/edit/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ id, name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                throw new Error(data.error || 'Failed to edit watchlist');
            }
        })
        .catch(error => {
            console.error('Error editing watchlist:', error);
            alert(error.message);
        });
    }

    deleteWatchlist() {
        const id = document.getElementById('deleteWatchlistId').value;

        fetch('/api/watchlist/delete/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ id })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else {
                throw new Error(data.error || 'Failed to delete watchlist');
            }
        })
        .catch(error => {
            console.error('Error deleting watchlist:', error);
            alert(error.message);
        });
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
}

// Initialize watchlist manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WatchlistManager();
});