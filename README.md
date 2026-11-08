# Gyftr Web Test App (Vercel)

A small web UI with OTP login, profile/balance, campaign play and logout. It is intended for testing an authorized Gyftr integration. Use only accounts you own/are authorized to test, and respect campaign terms and limits.

## Deploy
1. Import this project into Vercel.
2. Add environment variables:
   - `GYFTR_SESSION_KEY`: Fernet key, generate with:
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - `GYFTR_PASSPHRASE`: Optional; defaults to the value in the original script.
3. Deploy. Vercel uses `public/index.html` as the site and `api/*.py` as serverless functions.

## Local test
`pip install -r requirements.txt`
Set the two environment variables, then run with Vercel CLI:
`vercel dev`

## Security notes
- Browser auth tokens are kept in an encrypted, HttpOnly cookie; JavaScript cannot read them.
- Set the Fernet key to a strong private value and never commit it.
- Use HTTPS (Vercel does this in production).
- Serverless functions are stateless; this demo carries short-lived OTP-flow state in an encrypted cookie.
- For a production multi-user app, add persistent database-backed sessions, rate limiting, audit logging, a privacy notice, and official Gyftr API authorization.
