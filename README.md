# Gold Drop Registration — Vercel

## Deploy
1. Push this folder to a GitHub repository and import it into Vercel.
2. Add these Environment Variables in Vercel → Project Settings → Environment Variables:
   - `MASTER_KEY` — your service master key
   - `IP_API_KEY` — your IP-API Pro key
   - `REFERRAL_CODE` — valid campaign/referral code (optional; defaults to the value from your script)
   - `STATE_FERNET_KEY` — encryption key used to protect the temporary OTP session
3. Generate the Fernet key locally:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
4. Redeploy after adding the variables.

## API routes
- `POST /api/request_otp`: accepts `name`, `mobile`, `email`, `pincode`, and `photo` (base64 JPEG).
- `POST /api/verify_otp`: accepts `sessionToken` and `otp`.

## Important
- Your uploaded Python file contains hard-coded credentials. Rotate the master key and IP-API key before deployment; do not reuse exposed values.
- Each registrant enters their own details and uploads their own selfie. This version does not generate random names/emails or reuse the embedded photo.
- The backend follows the endpoints and signing format in the supplied script. The external service can change its API or reject requests.
- Before public launch, add service-owner-approved rate limiting, CAPTCHA, consent/privacy notice, and a data-retention/deletion policy. Test with your own number first.
- The service's eligibility rules and terms still apply.
