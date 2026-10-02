### YouTube

Create a Google Cloud project, enable YouTube Data API v3, configure the consent screen, add yourself as a test user and download an OAuth **Desktop app** client JSON. Save it in Accounts, choose Connect YouTube, open the login link and finish connecting. No API key is needed for publishing.

YouTube uses a local loopback callback and PKCE. Upload and read-only scopes allow publishing, channel identification and processing checks. Access tokens, refresh tokens, client configuration and upload-session addresses are stored in macOS Keychain. Test-mode credentials may expire and need reconnecting. Google may require app verification/audit for broader use or public uploads. New unaudited projects have private-only upload restrictions.

[Google Desktop OAuth](https://developers.google.com/identity/protocols/oauth2/native-app) · [YouTube uploads and restrictions](https://developers.google.com/youtube/v3/docs/videos/insert)

### Instagram

This version uses **Instagram API with Facebook Login**, so local MP4 bytes can go straight to Meta without putting your video on a public hosting site. You need a Creator/Business Instagram account connected to a Facebook Page you manage. Personal Instagram accounts are not supported by this API.

Create a Business Meta app, add Instagram API with Facebook Login and Facebook Login for Business, and create a **User access token** configuration. Include instagram_basic, instagram_content_publish, pages_show_list and pages_read_engagement. Grant access to the linked Page. Some Business Manager arrangements require additional permissions; use Meta's setup checks. App roles can test; other accounts need appropriate access/review.

Register an HTTPS OAuth redirect URL you control. Use a simple callback page without analytics or third-party scripts that preserves the query string and does not exchange the code. Enter the App ID, secret, configuration ID and callback URL in Accounts. After the Facebook login, copy the complete redirected URL into Clipping to finish connecting. The address includes a short-lived code: keep it private. This manual return avoids running a public server on your Mac. A hosted automatic callback can be added later.

[Meta publishing requirements and local uploads](https://developers.facebook.com/docs/instagram-platform/content-publishing/) · [Facebook Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/)

### Publishing and recovery

Open a finished clip → Publish to social media → choose account → save draft → review the exact video, caption and visibility → check the confirmation → Publish. Drafts do not upload anything. YouTube title limit is 100 characters; Instagram uses its caption field. Hashtags are optional manual text. Scheduling and custom covers are not included in this release.

Uploads run one at a time with small YouTube chunks or streaming Instagram file data; no AI model runs to post. Keep Clipping open during upload. Processing status may need a manual Check status. Closing the app preserves the attempt. YouTube can continue the same saved resumable session. Instagram never blindly repeats an uncertain publish request: check its destination before making another draft.

Published means the platform confirmed processing/publication; it does not mean a private YouTube video is publicly visible. The actual returned YouTube privacy setting is displayed. The original clip is marked Used only after confirmation. Disconnect deletes local account credentials; revoke platform permissions separately through your Google account or Facebook Business Integrations.
