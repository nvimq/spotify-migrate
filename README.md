# Spotify Migrate

Transfer your Spotify liked songs and playlists between two accounts.

---

### Русский

Переносит музыку (лайки + плейлисты) между двумя аккаунтами Spotify.

**Как использовать:**

1. Установите зависимости — `pip install requests`
2. Настройте `.env`:
   ```bash
   cp .env.example .env
   ```
   Откройте [Spotify Dashboard](https://developer.spotify.com/dashboard), создайте приложение и скопируйте Client ID и Client Secret в `.env`.

3. Запустите — `python spotify_transfer_ready.py`

4. Следуйте инструкциям в терминале:
   - Сначала авторизуйте **Account 1** (откуда переносить)
   - Затем **Account 2** (куда переносить) — используйте **инкогнито**
   - Скрипт сам перенесёт лайки и плейлисты

**Важно:**
- `.env` и `spotify_tokens.json` в `.gitignore` — секреты не утекают
- Токены живут 1 час, скрипт запросит авторизацию заново если надо
- Для второго аккаунта обязательно инкогнито

---

### English

Migrate your liked songs and playlists from one Spotify account to another.

**Usage:**

1. Install dependencies — `pip install requests`
2. Set up `.env`:
   ```bash
   cp .env.example .env
   ```
   Go to [Spotify Dashboard](https://developer.spotify.com/dashboard), create an app, and paste its Client ID and Client Secret into `.env`.

3. Run — `python spotify_transfer_ready.py`

4. Follow the terminal prompts:
   - Authorize **Account 1** (source) in your browser
   - Authorize **Account 2** (destination) in an **incognito window**
   - The script transfers likes and playlists automatically

**Notes:**
- `.env` and `spotify_tokens.json` are in `.gitignore` — secrets stay local
- Tokens expire after 1 hour; the script will re-prompt auth if needed
- Always use incognito/private browsing for the second account

---

### How it works

1. OAuth authorization for both accounts via Spotify Web API
2. Reads all liked tracks from Account 1, adds them to Account 2
3. Reads all playlists (names + descriptions) from Account 1
4. Creates matching playlists in Account 2 with all tracks
