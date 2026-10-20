import { useState } from 'react';
import { api } from '../api/api';
import { formatMoney } from '../components/TransactionTable';

function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `walletly-${Date.now()}-${Math.random().toString(36).slice(2, 14)}`;
}

export default function TransferPage({ wallet, onBack, onComplete }) {
  const [receiverWalletId, setReceiverWalletId] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [key, setKey] = useState(() => newIdempotencyKey());
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function updateTransferField(setter, value) {
    setter(value);
    if (!submitting) setKey(newIdempotencyKey());
    setError('');
    setSuccess(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSuccess(null);
    const receiverId = receiverWalletId.trim().toUpperCase();
    const numericAmount = Number(amount);
    if (!/^[A-Z0-9]{12}$/.test(receiverId)) {
      setError('Enter a valid 12-character public wallet ID.');
      return;
    }
    if (receiverId === (wallet?.wallet_id || '').toUpperCase()) {
      setError('You cannot transfer money to your own wallet.');
      return;
    }
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError('Enter an amount greater than zero.');
      return;
    }
    if (!/^\d+(?:\.\d{1,2})?$/.test(amount.trim())) {
      setError('Enter a valid amount with no more than two decimal places.');
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.transfer({ receiver_wallet_id: receiverId, amount: numericAmount.toFixed(2),  description: description.trim() || null }, key);
      setSuccess(response);
      await onComplete();
    } catch (err) {
      setError(err.message || 'Transfer failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  function startNewAttempt() {
    setKey(newIdempotencyKey());
    setError('');
    setSuccess(null);
  }

  return (
    <section className="page-content narrow-page">
      <button className="back-link" type="button" onClick={onBack}>← Back to dashboard</button>
      <div className="page-title-row single-title-row"><div><p className="eyebrow">SEND MONEY</p><h1>Transfer money</h1><p className="page-subtitle">Send funds to another Walletly wallet.</p></div></div>
      <div className="operation-layout transfer-layout">
        <section className="panel operation-card">
          <div className="operation-icon icon-transfer">↗</div>
          <form onSubmit={handleSubmit} className="form-stack">
            <div className="field-group"><label htmlFor="receiver-wallet">Receiver's public wallet ID</label><input id="receiver-wallet" type="text" placeholder="e.g. A1B2C3D4E5F6" value={receiverWalletId} onChange={(event) => updateTransferField(setReceiverWalletId, event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 12))} maxLength={12} minLength={12} autoCapitalize="characters" spellCheck="false" required /><small className="field-hint">Ask the receiver for their 12-character wallet ID.</small></div>
            <div className="field-group">
              <label htmlFor="transfer-description">
                Description (optional)
              </label>

              <textarea
                id="transfer-description"
                placeholder="e.g. Dinner payment"
                value={description}
                onChange={(event) =>
                  updateTransferField(setDescription, event.target.value)
                }
                maxLength={255}
                rows={3}
              />

              <small className="field-hint">
                Add a note to help identify this transaction. Maximum 255 characters.
              </small>
          </div>
            <div className="field-group"><label htmlFor="transfer-amount">Amount (INR)</label><div className="amount-input-wrap"><span>₹</span><input id="transfer-amount" type="number" min="0.01" step="0.01" max="9999999999.99" placeholder="0.00" value={amount} onChange={(event) => updateTransferField(setAmount, event.target.value)} required /></div><small className="field-hint">Available balance: {formatMoney(wallet?.balance)}</small></div>
            {error && <div className="alert error" role="alert"><strong>Transfer not completed</strong><p>{error}</p><button type="button" className="inline-button alert-action" onClick={startNewAttempt}>Start a new attempt</button></div>}
            {success && <div className="alert success" role="status"><strong>{success.message || 'Transfer successful.'}</strong><p>Reference: {success.public_transaction_id}</p><p>Amount: {formatMoney(success.amount ?? amount)}</p><p>Status: {success.status || 'SUCCESS'}</p></div>}
            <button className="button button-primary button-full" type="submit" disabled={submitting || Boolean(success)}>{submitting ? <><span className="spinner" /> Processing transfer…</> : success ? 'Transfer completed' : 'Confirm transfer'}</button>
            {success && <button className="button button-secondary button-full" type="button" onClick={onBack}>Return to dashboard</button>}
          </form>
        </section>
        <aside className="operation-side panel"><p className="eyebrow">BEFORE YOU SEND</p><h2>Review your details</h2><ul className="transfer-tips"><li>Double-check the receiver's wallet ID.</li><li>Only send an amount you intend to transfer.</li><li>Retries use the same idempotency key to help prevent duplicate transfers.</li></ul><div className="operation-tip"><span>i</span><p>Your request includes a unique idempotency key. The same key is reused for a retry of this attempt.</p></div></aside>
      </div>
    </section>
  );
}
