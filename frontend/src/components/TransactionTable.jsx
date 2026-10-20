export function formatMoney(value) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number.isFinite(amount) ? amount : 0);
}

export function formatDate(value) {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date);
}

export function transactionTitle(transaction, walletId) {
  if (transaction.transaction_type === 'DEPOSIT') return 'Deposit';
  if (transaction.transaction_type === 'WITHDRAWAL') return 'Withdrawal';
  if (transaction.transaction_type === 'TRANSFER' && transaction.sender_wallet_id === walletId) return 'Transfer sent';
  if (transaction.transaction_type === 'TRANSFER' && transaction.receiver_wallet_id === walletId) return 'Transfer received';
  return transaction.transaction_type || 'Transaction';
}

export function transactionDirection(transaction, walletId) {
  if (transaction.transaction_type === 'WITHDRAWAL') return 'debit';
  if (transaction.transaction_type === 'TRANSFER' && transaction.sender_wallet_id === walletId) return 'debit';
  return 'credit';
}

export function StatusBadge({ status }) {
  const success = status === 'SUCCESS';
  return <span className={`status-pill ${success ? 'status-success' : 'status-failed'}`}><span className="status-dot" />{status || 'UNKNOWN'}</span>;
}

export default function TransactionTable({ items, walletId, onSelect, compact = false }) {
  if (!items?.length) {
    return <div className="empty-state"><div className="empty-state-icon">↔</div><h3>No transactions found</h3><p>When you use your wallet, transactions will appear here.</p></div>;
  }

  return (
    <div className={`transaction-table-wrap ${compact ? 'compact' : ''}`}>
      <table className="transaction-table">
        <thead><tr><th>Transaction</th><th>Date</th><th>Amount</th><th>Status</th><th><span className="sr-only">Details</span></th></tr></thead>
        <tbody>{items.map((transaction) => {
          const direction = transactionDirection(transaction, walletId);
          return (
            <tr key={transaction.public_transaction_id}>
              <td><button type="button" className="transaction-name-button" onClick={() => onSelect(transaction.public_transaction_id)}><span className={`transaction-symbol ${direction}`}>{direction === 'debit' ? '↗' : '↙'}</span><span className="transaction-name-text"><strong>{transactionTitle(transaction, walletId)}</strong> {transaction.description?.trim() && (<small className="transaction-description">{transaction.description}</small>)}<small>{transaction.public_transaction_id}</small></span></button></td>
              <td className="transaction-date-cell">{formatDate(transaction.created_at)}</td>
              <td className={`amount-cell ${direction}`}>{direction === 'debit' ? '−' : '+'}{formatMoney(transaction.amount)}</td>
              <td><StatusBadge status={transaction.status} /></td>
              <td><button type="button" className="icon-button detail-arrow" aria-label={`View ${transaction.public_transaction_id}`} onClick={() => onSelect(transaction.public_transaction_id)}>↗</button></td>
            </tr>
          );
        })}</tbody>
      </table>
      <div className="mobile-transactions">{items.map((transaction) => {
        const direction = transactionDirection(transaction, walletId);
        return <button key={transaction.public_transaction_id} className="mobile-transaction" type="button" onClick={() => onSelect(transaction.public_transaction_id)}><span className={`transaction-symbol ${direction}`}>{direction === 'debit' ? '↗' : '↙'}</span><span className="mobile-transaction-main"><strong>{transactionTitle(transaction, walletId)}</strong><small>{formatDate(transaction.created_at)}</small><small>{transaction.public_transaction_id}</small></span><span className="mobile-transaction-right"><strong className={`amount-cell ${direction}`}>{direction === 'debit' ? '−' : '+'}{formatMoney(transaction.amount)}</strong><StatusBadge status={transaction.status} /></span></button>;
      })}</div>
    </div>
  );
}
