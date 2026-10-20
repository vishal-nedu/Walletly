import { useEffect, useState } from 'react';
import { api } from '../api/api';
import { formatDate, formatMoney, StatusBadge, transactionTitle } from './TransactionTable';

export default function TransactionDetails({ transactionId, walletId, onClose }) {
  const [transaction, setTransaction] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.transaction(transactionId).then((data) => {
      if (!cancelled) setTransaction(data);
    }).catch((err) => {
      if (!cancelled) setError(err.message || 'Could not load transaction details.');
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [transactionId]);

  useEffect(() => {
    function onKeyDown(event) { if (event.key === 'Escape') onClose(); }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="transaction-detail-title">
        <div className="modal-header"><div><p className="eyebrow">TRANSACTION DETAILS</p><h2 id="transaction-detail-title">Transaction receipt</h2></div><button className="icon-button" onClick={onClose} type="button" aria-label="Close details">×</button></div>
        {loading ? <div className="modal-content"><div className="loading-line"><span className="spinner" /> Loading details…</div></div> : error ? <div className="modal-content"><div className="alert error">{error}</div></div> : transaction && <div className="modal-content">
          <div className="receipt-amount"><span>{transactionTitle(transaction, walletId)}</span><strong>{formatMoney(transaction.amount)}</strong><StatusBadge status={transaction.status} /></div>
          {transaction.failure_reason && <div className="alert error">{transaction.failure_reason}</div>}
          <dl className="detail-list">
            <div><dt>Transaction ID</dt><dd>{transaction.public_transaction_id}</dd></div>
            <div><dt>Type</dt><dd>{transaction.transaction_type}</dd></div>
            <div><dt>Date and time</dt><dd>{formatDate(transaction.created_at)}</dd></div>
            <div><dt>From wallet</dt><dd>{transaction.sender_wallet_id || 'External source'}</dd></div>
            <div><dt>To wallet</dt><dd>{transaction.receiver_wallet_id || 'External destination'}</dd></div>
            <div><dt>Description</dt><dd>{transaction.description?.trim() || "No description provided"}</dd></div>
          </dl>
          <button className="button button-secondary button-full" type="button" onClick={onClose}>Close receipt</button>
        </div>}
      </section>
    </div>
  );
}
