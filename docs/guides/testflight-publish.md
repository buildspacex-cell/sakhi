# TestFlight Publish Process

> Quick reference for building and publishing the Sakhi iOS app to TestFlight.

## Prerequisites (one-time setup, already done)

- Apple Developer account (Team: Ravi Shankar Individual, ID: 47HYXW7V93)
- EAS account logged in as `buildspacex`
- Bundle ID: `com.buildspacex.sakhi`
- EAS Project ID: `065334a1-741a-47fe-8796-63b9d91faa66`
- EAS production env vars set: `EXPO_PUBLIC_BACKEND_URL`, `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- Apple signing credentials stored on EAS (auto-generated on first build)

## Publish to TestFlight

### Step 1: Build

```bash
cd apps/mobile
npx eas-cli build --platform ios --profile production
```

- Builds in EAS cloud (~15-20 min)
- Uses credentials stored from first build (no Apple ID prompt after first time)
- Check build status: `npx eas-cli build:list --platform ios --limit 1`

### Step 2: Submit to TestFlight

```bash
npx eas-cli submit --platform ios --latest
```

- Uploads the latest build to App Store Connect
- First submission: Apple reviews (~1-2 hours, automated)
- Subsequent submissions: usually available within minutes

### Step 3: Testers get the update

- Internal testers (added in App Store Connect) get a push notification
- They open TestFlight app → tap "Update" → done

## Adding a New Tester

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. **Users and Access** → add their Apple ID
3. **Apps** → Sakhi → **TestFlight** → **Internal Testing** → add to group

## Bump Version (when needed)

Edit `apps/mobile/app.config.js`:
```js
version: "1.0.1",  // User-facing version (semver)
```

For iOS build number (required to be unique per TestFlight upload), add to `ios` section:
```js
ios: {
  buildNumber: "2",  // Increment for each TestFlight upload
  ...
}
```

## Managing EAS Environment Variables

```bash
# List current production env vars
npx eas-cli env:list --environment production

# Update a variable
npx eas-cli env:update --name EXPO_PUBLIC_BACKEND_URL --value "https://new-url.com" --environment production

# Add a new variable
npx eas-cli env:create --name NEW_VAR --value "value" --visibility plaintext --environment production --non-interactive
```

## Common Issues

| Issue | Fix |
|-------|-----|
| `bundle identifier not available` | Change `bundleIdentifier` in `app.config.js` |
| `autoIncrement not supported` | Remove `autoIncrement` from `eas.json` (not compatible with `app.config.js`) |
| `No environment variables found` | Set vars with `eas env:create --environment production`; release builds now fail fast if `EXPO_PUBLIC_BACKEND_URL` is missing |
| App crashes on launch | Check env vars are set on EAS; `config.ts` now logs errors instead of throwing |
| `EACCES` installing eas-cli | Use `npx eas-cli` instead of global install |

## File Reference

| File | Purpose |
|------|---------|
| `apps/mobile/app.config.js` | Expo config (bundle ID, version, plugins, env vars) |
| `apps/mobile/eas.json` | EAS build profiles (development, preview, production) |
| `apps/mobile/lib/config.ts` | Runtime config resolution (env vars → app config) |
| `apps/mobile/lib/supabase.ts` | Supabase client initialization |
| `apps/mobile/.env` | Local dev env vars (NOT used in EAS builds) |
