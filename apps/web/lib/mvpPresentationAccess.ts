export const MVP_PRESENTATION_ACCESS_COOKIE = "sakhi-mvp-release-access";
const MVP_PRESENTATION_PASSWORD = "sakhi@27";

function normalizedPassword() {
  return MVP_PRESENTATION_PASSWORD;
}

function buildAccessToken(password: string) {
  let hash = 5381;
  const input = `sakhi-mvp-release:${password}`;

  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 33) ^ input.charCodeAt(index);
  }

  return `mvp-${(hash >>> 0).toString(16)}`;
}

export function getMvpPresentationAccessToken() {
  const password = normalizedPassword();
  return buildAccessToken(password);
}

export function isValidMvpPresentationAccessToken(value?: string | null) {
  const password = normalizedPassword();
  if (!value) {
    return false;
  }

  return value === buildAccessToken(password);
}

export function matchesMvpPresentationPassword(candidate: string) {
  return candidate === normalizedPassword();
}
