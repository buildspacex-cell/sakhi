# TestFlight Publish Process

> Quick reference for building and publishing the Sakhi iOS app to TestFlight with the local Fastlane path.

## Prerequisites (one-time setup, already done)

- Apple Developer account (Team: Ravi Shankar Individual, ID: 47HYXW7V93)
- Fastlane installed locally (`gem install fastlane`)
- CocoaPods installed locally
- `pnpm` available locally
- Bundle ID: `com.buildspacex.sakhi`
- Apple signing credentials available in the local Keychain / Xcode account
- `apps/mobile/.env.local` populated with:
  - `EXPO_PUBLIC_BACKEND_URL`
  - `EXPO_PUBLIC_SUPABASE_URL`
  - `EXPO_PUBLIC_SUPABASE_ANON_KEY`
  - `FASTLANE_USER`
  - `FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD`
- Root workspace uses `pnpm` (the stray root `package-lock.json` was removed so the monorepo does not fall back to `npm`)

## Publish to TestFlight

### Step 1: Build and upload

```bash
./scripts/ios-build.sh
```

- Loads `apps/mobile/.env.local`
- Installs JS deps with `pnpm`
- Runs `pod install`
- Runs `fastlane beta` from `apps/mobile/ios`
- Uploads the archive to TestFlight

### Step 2: Testers get the update

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

## Managing Fastlane Build Environment

Edit `apps/mobile/.env.local` locally before running `./scripts/ios-build.sh`.

Required:
- `EXPO_PUBLIC_BACKEND_URL`
- `EXPO_PUBLIC_SUPABASE_URL`
- `EXPO_PUBLIC_SUPABASE_ANON_KEY`
- `FASTLANE_USER`
- `FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD`

Forbidden in release builds:
- `EXPO_PUBLIC_OPENAI_API_KEY`
- `EXPO_PUBLIC_RELEASE_BYPASS_ENABLED`
- `EXPO_PUBLIC_RELEASE_BYPASS_PERSON_ID`

## Common Issues

| Issue | Fix |
|-------|-----|
| `pnpm not found` | Run `corepack enable && corepack prepare pnpm@10.19.0 --activate` |
| `remove stale EXPO_PUBLIC_OPENAI_API_KEY` | Delete the client OpenAI key from `apps/mobile/.env.local`; mobile no longer uses it |
| `remove stale EXPO_PUBLIC_RELEASE_BYPASS_*` | Delete the old release bypass vars from `apps/mobile/.env.local`; they are no longer part of the runtime |
| `EXPO_PUBLIC_BACKEND_URL is not set` | Add the Railway API URL to `apps/mobile/.env.local` before running the script |
| `bundle identifier not available` | Change `bundleIdentifier` in `app.config.js` |
| `pod install` fails | Open `apps/mobile/ios/Sakhi.xcworkspace` once in Xcode and verify local signing / CocoaPods are healthy |

## File Reference

| File | Purpose |
|------|---------|
| `apps/mobile/app.config.js` | Expo config (bundle ID, version, plugins, env vars) |
| `scripts/ios-build.sh` | Canonical internal TestFlight build script |
| `apps/mobile/ios/fastlane/Fastfile` | Fastlane beta lane (`build_app` + `upload_to_testflight`) |
| `apps/mobile/lib/config.ts` | Runtime config resolution (env vars → app config) |
| `apps/mobile/lib/supabase.ts` | Supabase client initialization |
| `apps/mobile/.env.local` | Local Fastlane/TestFlight env vars |
