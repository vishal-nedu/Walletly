import { useState } from 'react';
import { api } from '../api/api';

const passwordRules = [
  { key: 'length', label: 'At least 8 characters', test: (value) => value.length >= 8 },
  { key: 'alphabet', label: 'At least one alphabet', test: (value) => /[A-Za-z]/.test(value) },
  { key: 'number', label: 'At least one number', test: (value) => /\d/.test(value) },
  { key: 'special', label: 'At least one special character', test: (value) => /[^A-Za-z0-9\s]/.test(value) },
];

export default function AuthPage({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('error');
  const [submitting, setSubmitting] = useState(false);

  const isLogin = mode === 'login';
  const checks = Object.fromEntries(passwordRules.map((rule) => [rule.key, rule.test(password)]));
  const passwordIsValid = passwordRules.every((rule) => rule.test(password));

  function switchMode(nextMode) {
    setMode(nextMode);
    setName('');
    setEmail('');
    setPassword('');
    setMessage('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage('');

    if (!isLogin && !passwordIsValid) {
      setMessage('Please satisfy all password requirements before registering.');
      setMessageType('error');
      return;
    }

    setSubmitting(true);
    try {
      if (isLogin) {
        const data = await api.login({ email: email.trim(), password });
        if (!data?.access_token) throw new Error('The login response did not include an access token.');
        sessionStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) sessionStorage.setItem('refresh_token', data.refresh_token);
        else sessionStorage.removeItem('refresh_token');
        onLogin();
      } else {
        const data = await api.register({ name: name.trim(), email: email.trim(), password });
        const successMessage = typeof data === 'string'
          ? data
          : data?.message || 'Account created successfully. Please sign in.';
        setMode('login');
        setName('');
        setPassword('');
        setMessage(successMessage);
        setMessageType('success');
      }
    } catch (error) {
      setMessage(error.message || 'Something went wrong. Please try again.');
      setMessageType('error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-shell">
        <div className="auth-brand">
          <div className="brand-mark">W</div>
          <h1>Walletly</h1>
          <p>Simple, secure money management.</p>
        </div>
        <section className="auth-card panel">
          <div className="auth-heading">
            <p className="eyebrow">YOUR MONEY, MADE SIMPLE</p>
            <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
            <p>{isLogin ? 'Sign in to access your wallet.' : 'A few details and your wallet is ready.'}</p>
          </div>
          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button type="button" role="tab" aria-selected={isLogin} className={isLogin ? 'auth-tab active' : 'auth-tab'} onClick={() => switchMode('login')} disabled={submitting}>Login</button>
            <button type="button" role="tab" aria-selected={!isLogin} className={!isLogin ? 'auth-tab active' : 'auth-tab'} onClick={() => switchMode('register')} disabled={submitting}>Create account</button>
          </div>
          <form onSubmit={handleSubmit} className="form-stack">
            {!isLogin && (
              <div className="field-group">
                <label htmlFor="auth-name">Full name</label>
                <input id="auth-name" name="name" type="text" placeholder="Enter your full name" autoComplete="name" maxLength={100} value={name} onChange={(event) => setName(event.target.value)} required />
              </div>
            )}
            <div className="field-group">
              <label htmlFor="auth-email">Email address</label>
              <input id="auth-email" name="email" type="email" placeholder="you@example.com" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div className="field-group">
              <div className="label-row"><label htmlFor="auth-password">Password</label>{isLogin && <span className="field-side-note">Welcome back</span>}</div>
              <div className="password-input-wrap">
                <input id="auth-password" name="password" type={showPassword ? 'text' : 'password'} placeholder={isLogin ? 'Enter your password' : 'Create a strong password'} autoComplete={isLogin ? 'current-password' : 'new-password'} minLength={isLogin ? undefined : 8} value={password} onChange={(event) => setPassword(event.target.value)} required aria-describedby={isLogin ? undefined : 'password-rules'} />
                <button className="password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
              </div>
              {!isLogin && <ul id="password-rules" className="password-rules">{passwordRules.map((rule) => <li key={rule.key} className={checks[rule.key] ? 'valid' : ''}><span className="rule-check">{checks[rule.key] ? '✓' : '○'}</span>{rule.label}</li>)}</ul>}
            </div>
            {message && <div className={`alert ${messageType}`} role={messageType === 'error' ? 'alert' : 'status'}>{message}</div>}
            <button className="button button-primary button-full" type="submit" disabled={submitting}>{submitting ? <><span className="spinner" /> Please wait…</> : isLogin ? 'Sign in' : 'Create account'}</button>
          </form>
          <p className="auth-switch">{isLogin ? "Don't have an account?" : 'Already have an account?'} <button type="button" className="inline-button" onClick={() => switchMode(isLogin ? 'register' : 'login')} disabled={submitting}>{isLogin ? 'Register' : 'Sign in'}</button></p>
        </section>
        <p className="auth-footnote"><span className="secure-dot" /> Built for clear, everyday money management</p>
      </section>
    </main>
  );
}
