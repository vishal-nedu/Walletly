import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/api';
import TransactionTable from '../components/TransactionTable';

const emptyFilters = {search: '', direction: '', type: '', status: '', min_amount: '', max_amount: '', start_date: '', end_date: '', sort_by: 'created_at', sort_order: 'desc' };

export default function TransactionsPage({ walletId, onTransactionSelect }) {
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [data, setData] = useState({ items: [], total: 0, total_pages: 0, page: 1, limit: 10 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.transactions({ page, limit, ...appliedFilters });
      setData({ items: response.items || [], total: response.total || 0, total_pages: response.total_pages || 0, page: response.page || page, limit: response.limit || limit });
    } catch (err) {
      setError(err.message || 'Unable to load transaction history.');
    } finally {
      setLoading(false);
    }
  }, [page, limit, appliedFilters]);

  useEffect(() => { loadTransactions(); }, [loadTransactions]);

  function updateFilter(key, value) { setFilters((current) => ({ ...current, [key]: value })); }

  function applyFilters(event) {
    event.preventDefault();
    if (filters.min_amount !== '' && filters.max_amount !== '' && Number(filters.min_amount) > Number(filters.max_amount)) {
      setError('Minimum amount cannot exceed maximum amount.');
      return;
    }
    if (filters.start_date && filters.end_date && filters.start_date > filters.end_date) {
      setError('Start date cannot be after end date.');
      return;
    }
    setError('');
    setPage(1);
    setAppliedFilters({ ...filters, search: filters.search.trim(),});
  }

  function clearFilters() {
    setFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
    setPage(1);
    setError('');
  }

  const hasActiveFilters = Object.entries(appliedFilters).some(([key, value]) => value !== emptyFilters[key]);

  return (
    <section className="page-content">
      <div className="page-title-row"><div><p className="eyebrow">YOUR WALLET</p><h1>Transaction history</h1><p className="page-subtitle">Review and filter your wallet activity.</p></div><button type="button" className="button button-secondary" onClick={loadTransactions} disabled={loading}><span className={loading ? 'refresh-symbol spinning' : 'refresh-symbol'}>↻</span> Refresh</button></div>
      <section className="panel filters-panel">
        <div className="filter-panel-heading"><div><h2>Filter transactions</h2><p>Choose the criteria you want to see.</p></div>{hasActiveFilters && <button type="button" className="inline-button" onClick={clearFilters}>Clear filters</button>}</div>
        <form onSubmit={applyFilters}>
          <div className="filter-grid">
            <div className="field-group"><label htmlFor="filter-search">Search transactions</label><input id="filter-search"type="search"placeholder="Transaction ID or wallet ID"value={filters.search}onChange={(event) => updateFilter('search', event.target.value)}maxLength={100}/></div>
            <div className="field-group"><label htmlFor="filter-type">Transaction type</label><select id="filter-type" value={filters.type} onChange={(event) => updateFilter('type', event.target.value)}><option value="">All types</option><option value="DEPOSIT">Deposit</option><option value="WITHDRAWAL">Withdrawal</option><option value="TRANSFER">Transfer</option></select></div>
            <div className="field-group"><label htmlFor="filter-status">Status</label><select id="filter-status" value={filters.status} onChange={(event) => updateFilter('status', event.target.value)}><option value="">All statuses</option><option value="SUCCESS">Success</option><option value="FAILED">Failed</option></select></div>
            <div className="field-group"><label htmlFor="filter-direction">Direction</label><select id="filter-direction" value={filters.direction} onChange={(event) => updateFilter('direction', event.target.value)}><option value="">All directions</option><option value="sent">Sent</option><option value="received">Received</option></select></div>
            <div className="field-group"><label htmlFor="filter-min">Minimum amount (₹)</label><input id="filter-min" type="number" min="0" step="0.01" placeholder="No minimum" value={filters.min_amount} onChange={(event) => updateFilter('min_amount', event.target.value)} /></div>
            <div className="field-group"><label htmlFor="filter-max">Maximum amount (₹)</label><input id="filter-max" type="number" min="0" step="0.01" placeholder="No maximum" value={filters.max_amount} onChange={(event) => updateFilter('max_amount', event.target.value)} /></div>
            <div className="field-group"><label htmlFor="filter-from">From date</label><input id="filter-from" type="date" value={filters.start_date} onChange={(event) => updateFilter('start_date', event.target.value)} /></div>
            <div className="field-group"><label htmlFor="filter-to">To date</label><input id="filter-to" type="date" value={filters.end_date} onChange={(event) => updateFilter('end_date', event.target.value)} /></div>
            <div className="field-group"><label htmlFor="filter-sort">Sort by</label><select id="filter-sort" value={filters.sort_by} onChange={(event) => updateFilter('sort_by', event.target.value)}><option value="created_at">Date</option><option value="amount">Amount</option><option value="public_transaction_id">Transaction ID</option></select></div>
            <div className="field-group"><label htmlFor="filter-order">Sort order</label><select id="filter-order" value={filters.sort_order} onChange={(event) => updateFilter('sort_order', event.target.value)}><option value="desc">Newest / highest first</option><option value="asc">Oldest / lowest first</option></select></div>
          </div>
          <div className="filter-actions"><label className="page-size-control" htmlFor="page-size">Rows <select id="page-size" value={limit} onChange={(event) => { setLimit(Number(event.target.value)); setPage(1); }}><option value={5}>5</option><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select> per page</label><button className="button button-primary" type="submit">Apply filters</button></div>
        </form>
      </section>
      {error && <div className="alert error inline-alert" role="alert">{error}</div>}
      <section className="panel history-panel"><div className="section-title-row history-title-row"><div><h2>All transactions</h2><p>{loading ? 'Loading records…' : `${data.total} transaction${data.total === 1 ? '' : 's'} found`}</p></div></div>
        {loading ? <div className="page-loading"><span className="spinner" /> Loading transactions…</div> : error && !data.items.length ? null : <TransactionTable items={data.items} walletId={walletId} onSelect={onTransactionSelect} />}
        {!loading && !error && data.total > 0 && <div className="pagination-row"><p>Page <strong>{page}</strong> of <strong>{Math.max(1, data.total_pages)}</strong></p><div className="pagination-buttons"><button type="button" className="button button-secondary button-small" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>← Previous</button><button type="button" className="button button-secondary button-small" onClick={() => setPage((current) => Math.min(data.total_pages, current + 1))} disabled={page >= data.total_pages}>Next →</button></div></div>}
      </section>
    </section>
  );
}
