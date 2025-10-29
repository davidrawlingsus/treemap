// Client Dashboard Manager
class DashboardManager {
    constructor() {
        this.clientId = null;
        this.ideas = [];
        this.stats = null;
        this.dataSources = new Set();
        this.init();
    }

    init() {
        // Get client ID from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.clientId = urlParams.get('client_id');

        if (!this.clientId) {
            alert('No client ID provided');
            window.location.href = '/index.html';
            return;
        }

        // Set up event listeners
        document.getElementById('statusFilter').addEventListener('change', () => this.applyFilters());
        document.getElementById('dataSourceFilter').addEventListener('change', () => this.applyFilters());
        document.getElementById('sortBy').addEventListener('change', () => this.applyFilters());

        // Load data
        this.loadData();
    }

    async loadData() {
        this.showLoading();
        try {
            await Promise.all([
                this.fetchClientInfo(),
                this.fetchStats(),
                this.fetchIdeas()
            ]);
            this.populateDataSourceFilter();
            this.renderIdeas();
        } catch (error) {
            console.error('Error loading dashboard:', error);
            alert('Error loading dashboard data');
        }
    }

    async fetchClientInfo() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/clients/${this.clientId}`);
            if (!response.ok) throw new Error('Failed to fetch client info');
            const client = await response.json();
            document.getElementById('clientName').textContent = `${client.name} - Growth Ideas`;
            document.title = `${client.name} - Growth Ideas Dashboard`;
        } catch (error) {
            console.error('Error fetching client info:', error);
        }
    }

    async fetchStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/clients/${this.clientId}/growth-ideas/stats`);
            if (!response.ok) throw new Error('Failed to fetch stats');
            this.stats = await response.json();
            this.updateStats();
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    async fetchIdeas() {
        const statusFilter = document.getElementById('statusFilter').value;
        const dataSourceFilter = document.getElementById('dataSourceFilter').value;
        const sortBy = document.getElementById('sortBy').value;

        let url = `${API_BASE_URL}/api/clients/${this.clientId}/growth-ideas?sort_by=${sortBy}`;
        if (statusFilter) url += `&status=${statusFilter}`;
        if (dataSourceFilter) url += `&data_source_id=${dataSourceFilter}`;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch ideas');
            this.ideas = await response.json();
            
            // Collect unique data sources
            this.dataSources = new Set();
            this.ideas.forEach(idea => {
                if (idea.data_source_id && idea.data_source_name) {
                    this.dataSources.add(JSON.stringify({
                        id: idea.data_source_id,
                        name: idea.data_source_name
                    }));
                }
            });
        } catch (error) {
            console.error('Error fetching ideas:', error);
            throw error;
        }
    }

    populateDataSourceFilter() {
        const select = document.getElementById('dataSourceFilter');
        // Keep the "All Data Sources" option
        select.innerHTML = '<option value="">All Data Sources</option>';
        
        // Add data source options
        const sources = Array.from(this.dataSources).map(s => JSON.parse(s));
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source.id;
            option.textContent = source.name;
            select.appendChild(option);
        });
    }

    updateStats() {
        if (!this.stats) return;

        document.getElementById('statTotal').textContent = this.stats.total_ideas;
        document.getElementById('statAccepted').textContent = this.stats.accepted_count;
        document.getElementById('statPending').textContent = this.stats.pending_count;
        document.getElementById('statRejected').textContent = this.stats.rejected_count;
    }

    showLoading() {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('ideasList').style.display = 'none';
    }

    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
    }

    renderIdeas() {
        this.hideLoading();
        const container = document.getElementById('ideasList');

        if (this.ideas.length === 0) {
            document.getElementById('emptyState').style.display = 'block';
            container.style.display = 'none';
            return;
        }

        document.getElementById('emptyState').style.display = 'none';
        container.style.display = 'grid';
        container.innerHTML = '';

        this.ideas.forEach(idea => {
            container.appendChild(this.createIdeaCard(idea));
        });
    }

    createIdeaCard(idea) {
        const card = document.createElement('div');
        card.className = 'idea-card';
        card.dataset.ideaId = idea.id;

        const priorityText = this.getPriorityText(idea.priority);
        const priorityClass = idea.priority ? `priority-${idea.priority}` : '';

        const date = new Date(idea.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });

        card.innerHTML = `
            <div class="idea-header">
                <div class="idea-meta">
                    <span class="badge ${idea.status}">${idea.status}</span>
                    ${idea.priority ? `<span class="badge ${priorityClass}">${priorityText}</span>` : ''}
                </div>
            </div>
            <div class="idea-text">${this.escapeHtml(idea.idea_text)}</div>
            <div class="idea-details">
                <div class="idea-detail">
                    <strong>Dimension:</strong> ${this.escapeHtml(idea.dimension_name || idea.dimension_ref_key)}
                </div>
                <div class="idea-detail">
                    <strong>Data Source:</strong> ${this.escapeHtml(idea.data_source_name || 'Unknown')}
                </div>
                <div class="idea-detail">
                    <strong>Created:</strong> ${date}
                </div>
            </div>
            <div class="idea-actions">
                ${this.renderActionButtons(idea)}
                <select class="priority-selector" data-idea-id="${idea.id}">
                    <option value="">Set Priority</option>
                    <option value="1" ${idea.priority === 1 ? 'selected' : ''}>High</option>
                    <option value="2" ${idea.priority === 2 ? 'selected' : ''}>Medium</option>
                    <option value="3" ${idea.priority === 3 ? 'selected' : ''}>Low</option>
                </select>
                <button class="btn btn-delete" data-action="delete" data-idea-id="${idea.id}">Delete</button>
            </div>
        `;

        // Add event listeners
        card.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleAction(e));
        });

        card.querySelector('.priority-selector').addEventListener('change', (e) => {
            this.updatePriority(idea.id, parseInt(e.target.value) || null);
        });

        return card;
    }

    renderActionButtons(idea) {
        if (idea.status === 'pending') {
            return `
                <button class="btn btn-accept" data-action="accept" data-idea-id="${idea.id}">Accept</button>
                <button class="btn btn-reject" data-action="reject" data-idea-id="${idea.id}">Reject</button>
            `;
        } else if (idea.status === 'accepted') {
            return `
                <button class="btn btn-reject" data-action="reject" data-idea-id="${idea.id}">Reject</button>
                <button class="btn btn-pending" data-action="pending" data-idea-id="${idea.id}">Mark Pending</button>
            `;
        } else { // rejected
            return `
                <button class="btn btn-accept" data-action="accept" data-idea-id="${idea.id}">Accept</button>
                <button class="btn btn-pending" data-action="pending" data-idea-id="${idea.id}">Mark Pending</button>
            `;
        }
    }

    async handleAction(e) {
        const action = e.target.dataset.action;
        const ideaId = e.target.dataset.ideaId;

        if (action === 'delete') {
            if (!confirm('Are you sure you want to delete this idea?')) return;
            await this.deleteIdea(ideaId);
        } else {
            await this.updateStatus(ideaId, action);
        }
    }

    async updateStatus(ideaId, status) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/growth-ideas/${ideaId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });

            if (!response.ok) throw new Error('Failed to update idea');

            // Reload data
            await this.loadData();
        } catch (error) {
            console.error('Error updating idea:', error);
            alert('Error updating idea status');
        }
    }

    async updatePriority(ideaId, priority) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/growth-ideas/${ideaId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ priority })
            });

            if (!response.ok) throw new Error('Failed to update priority');

            // Reload data
            await this.loadData();
        } catch (error) {
            console.error('Error updating priority:', error);
            alert('Error updating idea priority');
        }
    }

    async deleteIdea(ideaId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/growth-ideas/${ideaId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete idea');

            // Reload data
            await this.loadData();
        } catch (error) {
            console.error('Error deleting idea:', error);
            alert('Error deleting idea');
        }
    }

    async applyFilters() {
        this.showLoading();
        try {
            await this.fetchIdeas();
            this.renderIdeas();
        } catch (error) {
            console.error('Error applying filters:', error);
            this.hideLoading();
        }
    }

    getPriorityText(priority) {
        switch (priority) {
            case 1: return 'High Priority';
            case 2: return 'Medium Priority';
            case 3: return 'Low Priority';
            default: return '';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});

