# Walletly — React + Vite frontend

A simple responsive React/JavaScript frontend for the FastAPI digital wallet backend.

## Included features

- Register and log in using `/auth/register` and `/auth/login`
- Frontend password checks during registration (8+ characters, alphabet, number, special character)
- Stores access/refresh tokens in `sessionStorage`
- Attempts access-token refresh via `/auth/refresh` after a protected request returns 401
- Dashboard profile, wallet balance, public wallet ID, recent transactions
- Deposit and withdrawal forms
- Transfer form with receiver wallet ID validation and an `Idempotency-Key` header
- Transaction history filters, sorting, page size, and pagination
- Transaction details modal
- Responsive CSS with no UI library required

## Run locally

Requirements: Node.js 18+ (Node.js 20+ recommended) and your FastAPI backend running.

1. Extract this folder.
2. Copy `.env.example` to `.env`.
3. Set `VITE_API_BASE_URL` to your FastAPI base URL, for example:

   ```env
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

4. Install packages and start Vite:

   ```bash
   npm install
   npm run dev
   ```

5. Open the URL printed by Vite, usually `http://localhost:5173`.

The backend's CORS configuration must allow the frontend origin. The provided backend snippet already allowed `http://localhost:5173` and `http://127.0.0.1:5173`.

## API contract used

- `POST /auth/register` — `{name, email, password}`
- `POST /auth/login` — `{email, password}` → `{access_token, refresh_token, token_type}`
- `POST /auth/refresh` — `{refresh_token}` → `{access_token, token_type}`
- `GET /users/me`
- `GET /wallet`
- `POST /wallet/deposit` — `{amount}`
- `POST /wallet/withdraw` — `{amount}`
- `POST /transfers` — `{receiver_wallet_id, amount}`, with `Idempotency-Key` header
- `GET /transactions` — supports `page`, `limit`, `min_amount`, `max_amount`, `direction`, `type`, `status`, `start_date`, `end_date`, `sort_by`, and `sort_order`
- `GET /transactions/{public_transaction_id}`

## Notes

- This frontend is matched to the endpoints and schemas supplied in this conversation. If the backend changes its routes or response fields, update `src/api/api.js` and the relevant page.
- Frontend password checks improve user experience but are not a security boundary. Enforce all password rules on the backend too.
- Tokens in `sessionStorage` are a simple MVP choice. JavaScript running on the page can access them, so production deployments should review token handling and XSS protections.
- Deposits are simulated according to the supplied backend; this is not connected to a real payment provider.
- A transfer request's idempotency key is reused for a retry of the same unchanged attempt. If transfer details change, a fresh key is generated.
