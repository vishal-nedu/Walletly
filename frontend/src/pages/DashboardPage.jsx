import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/api';
import TransactionTable, { formatMoney } from '../components/TransactionTable';

export default function DashboardPage({ onNavigate, onTransactionSelect, refreshSignal = 0 }) {
  const [profile, setProfile] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadData = useCallback(async (showMainLoader = true) => {
    if (showMainLoader) setLoading(true);
    else setRefreshing(true);
    setError('');
    try {
      const [profileData, walletData, transactionData] = await Promise.all([
        api.me(), api.wallet(), api.transactions({ page: 1, limit: 5, sort_by: 'created_at', sort_order: 'desc' }),
      ]);
      setProfile(profileData);
      setWallet(walletData);
      setTransactions(Array.isArray(transactionData?.items) ? transactionData.items : []);
    } catch (err) {
      setError(err.message || 'Unable to load your wallet dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadData(true); }, [loadData, refreshSignal]);

  if (loading) return <section className="page-content"><div className="page-loading"><span className="spinner" /> Loading your wallet…</div></section>;
  if (error && !wallet) return <section className="page-content"><div className="panel page-error"><div className="error-icon">!</div><h2>We couldn't load your wallet</h2><p>{error}</p><button className="button button-primary" onClick={() => loadData(true)}>Try again</button></div></section>;

  const walletId = wallet?.wallet_id || profile?.public_wallet_id;

  return (
    <section className="page-content">
      <div className="page-title-row"><div><p className="eyebrow">OVERVIEW</p><h1>Good day, {profile?.name?.split(' ')[0] || 'there'} <span className="wave">✦</span></h1><p className="page-subtitle">Here is a summary of your wallet today.</p></div><button className="button button-secondary refresh-button" onClick={() => loadData(false)} disabled={refreshing}><span className={refreshing ? 'refresh-symbol spinning' : 'refresh-symbol'}>↻</span> Refresh</button></div>
      {error && <div className="alert error inline-alert">{error}</div>}
      <div className="dashboard-grid">
        <section className="balance-panel">
          <div className="balance-panel-top"><div><p className="balance-label">Total available balance</p><h2>{formatMoney(wallet?.balance)}</h2></div><div className="balance-visual" aria-hidden="true"><span>₹</span></div></div>
          <div className="balance-divider" />
          <div className="wallet-id-line"><div><span className="balance-label">PUBLIC WALLET ID</span><strong>{walletId || 'Unavailable'}</strong></div><button className="copy-wallet-button" type="button" disabled={!walletId} onClick={async () => { try { await navigator.clipboard.writeText(walletId); } catch { window.prompt('Copy your wallet ID', walletId); } }}>Copy ID</button></div>
          <p className="balance-footnote"><span className="tiny-check">✓</span> Your wallet is ready to use</p>
        </section>
        <section className="profile-panel panel"><div className="profile-avatar">{(profile?.name || 'U').trim().charAt(0).toUpperCase()}</div><div className="profile-copy"><p className="eyebrow">YOUR ACCOUNT</p><h3>{profile?.name || 'Wallet user'}</h3><p>{profile?.email || ''}</p></div><div className="profile-divider" /><div className="profile-stat"><span>Account status</span><strong><span className="status-dot status-dot-green" /> Active</strong></div><div className="profile-stat"><span>Wallet currency</span><strong>INR · ₹</strong></div></section>
      </div>
      <section className="section-block"><div className="section-title-row"><div><h2>Quick actions</h2><p>What would you like to do?</p></div></div><div className="quick-action-grid">
        <button className="quick-action-card" onClick={() => onNavigate('deposit')} type="button"><span className="quick-action-icon icon-deposit">↓</span><span className="quick-action-copy"><strong>Deposit money</strong><small>Add funds to your wallet</small></span><span className="quick-action-chevron">›</span></button>
        <button className="quick-action-card" onClick={() => onNavigate('withdraw')} type="button"><span className="quick-action-icon icon-withdraw">↑</span><span className="quick-action-copy"><strong>Withdraw money</strong><small>Move funds out</small></span><span className="quick-action-chevron">›</span></button>
        <button className="quick-action-card" onClick={() => onNavigate('transfer')} type="button"><span className="quick-action-icon icon-transfer">↗</span><span className="quick-action-copy"><strong>Transfer money</strong><small>Send money to a wallet</small></span><span className="quick-action-chevron">›</span></button>
      </div></section>
      <section className="section-block panel recent-panel"><div className="section-title-row recent-title-row"><div><h2>Recent transactions</h2><p>Your latest wallet activity</p></div><button type="button" className="inline-button" onClick={() => onNavigate('transactions')}>View all <span aria-hidden="true">→</span></button></div><TransactionTable items={transactions} walletId={walletId} onSelect={onTransactionSelect} compact /></section>
    </section>
  );
}
