# Number OSINT Bot

An aiogram 3.x Telegram bot that sends values supplied to `/num` and `/tg` to a configured lookup API and displays selected returned fields. It has no database or API-key dependency.

## Project structure

```text
api/webhook.py       Vercel webhook entrypoint
bot/                 Shared configuration, handlers, messages, keyboards, and API client
main.py              Local polling entrypoint
```

## Install

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

## Environment

Put these values in `.env.local` for local development (and configure the same values in Vercel):

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=123456789
ALT_TG_ID=987654321
NUMBER_API_URL=https://provider.example/lookup/{number}
TG_API_URL=https://provider.example/tg/{telegram_id}
ACTIVE_USER_HOURS=24
NUM_RATE_LIMIT_SECONDS=10
```

`NUMBER_API_URL` supports two request forms for `/num`:

`TG_API_URL` is used only by `/tg`. It may contain `{telegram_id}`, which is replaced with only the validated Telegram user ID, or an empty query parameter whose name identifies the API input.

- With `{number}`, for example `https://provider.example/lookup/{number}`, the placeholder is replaced with only the validated value from the command.
- Without `{number}`, the client sends only the validated value as `number` by default. GET requests use a query parameter; non-GET requests use form data.

Optional request-shape settings are `NUMBER_API_METHOD` (default `GET`), `NUMBER_API_NUMBER_PARAM` (default `number`), and `NUMBER_API_PAYLOAD_FORMAT` (`query` or `form`). They are not required. No API-key header or query parameter is sent.

## Run locally

```bash
python main.py
```

Polling and Vercel use the same dispatcher, handlers, configuration, and API client.

## Deploy to Vercel

1. Push the project to a repository and import it into Vercel.
2. Add the environment values above.
3. Deploy. The webhook endpoint is `/api/webhook`.
4. Set `WEBHOOK_URL` in Vercel to the full endpoint URL, for example
	`https://<your-project>.vercel.app/api/webhook`. If it is omitted, the
	handler derives the URL from Vercel's `VERCEL_URL` value.
5. Open `https://<your-project>.vercel.app/api/webhook` once after deployment
	to register the Telegram webhook. It returns a JSON confirmation.

You can also set the Telegram webhook directly:

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<your-project>.vercel.app/api/webhook
```

Do not run polling and the webhook for the same bot at the same time.

## Commands and limitations

- `/num 1234567890` sends only `1234567890` to the configured endpoint; it does not add a country code.
- `/tg 7290081245` sends only `7290081245` to the configured endpoint after validating it as a Telegram user ID.
- `/help` includes a **Create Ticket** button. It immediately sends an alert to `ADMIN_ID` with a Telegram contact link; tickets are not stored.
- `/stat` is admin-only and reports only temporary, current-instance activity. It does not claim persistent Vercel totals.
- `/broadcast <message>` is admin-only and sends a formatted message to user IDs stored locally in `recipients.txt`.
- `ALT_TG_ID` is optional. When valid, it receives an audit log for each incoming user message or command; invalid or missing values disable audit delivery without stopping the bot.
