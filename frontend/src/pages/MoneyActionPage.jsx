import { useState } from 'react';
import { api } from '../api/api';
import { formatMoney } from '../components/TransactionTable';

const config = {
  deposit: { title: 'Deposit money', subtitle: 'Add funds to your wallet balance.', button: 'Deposit money', note: 'This simulates adding funds to your wallet.' },
  withdraw: { title: 'Withdraw money', subtitle: 'Withdraw available funds from your wallet.', button: 'Withdraw money', note: 'You can withdraw up to your available balance.' },
};

export default function MoneyActionPage({ mode, wallet, onBack, onComplete }) {
  const settings = config[mode];
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSuccess(null);
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError('Enter an amount greater than zero.');
      return;
    }
    if (!/^\d+(?:\.\d{1,2})?$/.test(amount.trim())) {
      setError('Enter a valid amount with no more than two decimal places.');
      return;
    }
    if (mode === 'withdraw' && numericAmount > Number(wallet?.balance ?? 0)) {
      setError('The amount exceeds your available balance.');
      return;
    }

    setSubmitting(true);
    try {
      const response = mode === 'deposit' ? await api.deposit(numericAmount.toFixed(2)) : await api.withdraw(numericAmount.toFixed(2));
      setSuccess({ message: response?.message || `${settings.button} successful.`, balance: response?.balance, transactionId: response?.public_transaction_id });
      setAmount('');
      await onComplete();
    } catch (err) {
      setError(err.message || `${settings.title} failed. Please try again.`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-content narrow-page">
      <button className="back-link" type="button" onClick={onBack}>← Back to dashboard</button>
      <div className="page-title-row single-title-row"><div><p className="eyebrow">WALLET ACTION</p><h1>{settings.title}</h1><p className="page-subtitle">{settings.subtitle}</p></div></div>
      <div className="operation-layout">
        <section className="panel operation-card">
          <div className={`operation-icon ${mode === 'deposit' ? 'icon-deposit' : 'icon-withdraw'}`}>{mode === 'deposit' ? '↓' : '↑'}</div>
          <form onSubmit={handleSubmit} className="form-stack">
            <div className="field-group"><label htmlFor="operation-amount">Amount (INR)</label><div className="amount-input-wrap"><span>₹</span><input id="operation-amount" type="number" min="0.01" step="0.01" max="9999999999.99" placeholder="0.00" value={amount} onChange={(event) => setAmount(event.target.value)} required /></div><small className="field-hint">{settings.note}</small></div>
            {error && <div className="alert error" role="alert">{error}</div>}
            {success && <div className="alert success" role="status"><strong>{success.message}</strong>{success.balance !== undefined && <p>New balance: {formatMoney(success.balance)}</p>}{success.transactionId && <p className="small-break">Reference: {success.transactionId}</p>}</div>}
            <button className="button button-primary button-full" type="submit" disabled={submitting}>{submitting ? <><span className="spinner" /> Processing…</> : settings.button}</button>
            {success && <button className="button button-secondary button-full" type="button" onClick={onBack}>Return to dashboard</button>}
          </form>
        </section>
        <aside className="operation-side panel"><p className="eyebrow">CURRENT BALANCE</p><h2>{formatMoney(wallet?.balance)}</h2><p>Your available wallet balance before this operation.</p><div className="operation-tip"><span>i</span><p>Amounts are processed by your wallet backend. A successful operation updates the balance and creates a transaction record.</p></div></aside>
      </div>
    </section>
  );
}
