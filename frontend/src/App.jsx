import { useCallback, useEffect, useState } from 'react';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import MoneyActionPage from './pages/MoneyActionPage';
import TransferPage from './pages/TransferPage';
import TransactionsPage from './pages/TransactionsPage';
import TransactionDetails from './components/TransactionDetails';
import { api } from './api/api';
import './App.css';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: '⌂' },
  { id: 'transactions', label: 'Transactions', icon: '↔' },
];

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(sessionStorage.getItem('access_token')));
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [profile, setProfile] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sessionChecking, setSessionChecking] = useState(() => Boolean(sessionStorage.getItem('access_token')));

  const logout = useCallback(() => {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    setAuthenticated(false);
    setCurrentPage('dashboard');
    setProfile(null);
    setWallet(null);
    setSelectedTransaction(null);
    setSessionChecking(false);
  }, []);

  useEffect(() => {
    function handleExpiredSession() { logout(); }
    window.addEventListener('walletly:session-expired', handleExpiredSession);
    return () => window.removeEventListener('walletly:session-expired', handleExpiredSession);
  }, [logout]);

  useEffect(() => {
    let cancelled = false;
    async function verifySession() {
      if (!sessionStorage.getItem('access_token')) {
        setSessionChecking(false);
        return;
      }
      try {
        const [me, myWallet] = await Promise.all([api.me(), api.wallet()]);
        if (!cancelled) {
          setProfile(me);
          setWallet(myWallet);
          setAuthenticated(true);
        }
      } catch {
        if (!cancelled) logout();
      } finally {
        if (!cancelled) setSessionChecking(false);
      }
    }
    verifySession();
    return () => { cancelled = true; };
  }, [logout]);

  const handleLogin = useCallback(() => {
    setAuthenticated(true);
    setCurrentPage('dashboard');
    setRefreshSignal((value) => value + 1);
  }, []);

  const refreshShellData = useCallback(async () => {
    try {
      const [me, myWallet] = await Promise.all([api.me(), api.wallet()]);
      setProfile(me);
      setWallet(myWallet);
    } catch {
      // The page will surface endpoint errors; don't hide the current UI here.
    }
  }, []);

  useEffect(() => {
    if (authenticated) refreshShellData();
  }, [authenticated, refreshSignal, refreshShellData]);

  function navigate(page) {
    setCurrentPage(page);
    setMobileNavOpen(false);
  }

  function completeOperation() {
    setRefreshSignal((value) => value + 1);
  }

  if (!authenticated) {
    if (sessionChecking) return <main className="auth-page"><div className="page-loading"><span className="spinner" /> Checking your session…</div></main>;
    return <AuthPage onLogin={handleLogin} />;
  }

  const titleByPage = {
    dashboard: 'Dashboard',
    transactions: 'Transactions',
    deposit: 'Deposit',
    withdraw: 'Withdraw',
    transfer: 'Transfer',
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <button className="sidebar-brand" type="button" onClick={() => navigate('dashboard')}><span className="brand-mark small-mark">W</span><span><strong>Walletly</strong><small>Digital wallet</small></span></button>
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map((item) => <button key={item.id} type="button" className={`nav-item ${currentPage === item.id ? 'nav-item-active' : ''}`} onClick={() => navigate(item.id)}><span className="nav-icon">{item.icon}</span><span>{item.label}</span>{item.id === 'transactions' && <span className="nav-chevron">›</span>}</button>)}
        </nav>
        <div className="sidebar-bottom"><div className="sidebar-help"><span className="help-icon">i</span><strong>Your wallet, your control</strong><p>Keep your wallet ID handy when receiving transfers.</p></div><button className="sidebar-logout" type="button" onClick={logout}><span>↪</span> Sign out</button></div>
      </aside>
      {mobileNavOpen && <button className="mobile-nav-backdrop" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
      <div className="main-shell">
        <header className="topbar"><div className="topbar-left"><button className="mobile-menu-button" type="button" onClick={() => setMobileNavOpen((open) => !open)} aria-label="Toggle navigation">☰</button><span className="breadcrumb-muted">Workspace</span><span className="breadcrumb-divider">/</span><strong>{titleByPage[currentPage] || 'Dashboard'}</strong></div><div className="topbar-right"><span className="topbar-status"><span className="status-dot status-dot-green" /> Wallet active</span><div className="topbar-avatar" title={profile?.name || 'Account'}>{(profile?.name || 'U').trim().charAt(0).toUpperCase()}</div></div></header>
        <main className="main-content">
          {currentPage === 'dashboard' && <DashboardPage onNavigate={navigate} onTransactionSelect={setSelectedTransaction} refreshSignal={refreshSignal} />}
          {(currentPage === 'deposit' || currentPage === 'withdraw') && <MoneyActionPage key={currentPage} mode={currentPage} wallet={wallet} onBack={() => navigate('dashboard')} onComplete={completeOperation} />}
          {currentPage === 'transfer' && <TransferPage wallet={wallet} onBack={() => navigate('dashboard')} onComplete={completeOperation} />}
          {currentPage === 'transactions' && <TransactionsPage walletId={wallet?.wallet_id || profile?.public_wallet_id} onTransactionSelect={setSelectedTransaction} />}
        </main>
        <footer className="app-footer"><span>© {new Date().getFullYear()} Walletly</span><span>Simple, secure money management</span></footer>
      </div>
      {selectedTransaction && <TransactionDetails transactionId={selectedTransaction} walletId={wallet?.wallet_id || profile?.public_wallet_id} onClose={() => setSelectedTransaction(null)} />}
    </div>
  );
}
