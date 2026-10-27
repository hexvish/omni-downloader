# Omni Downloader — Oracle Cloud Deployment Checklist

**Purpose:** Host the existing Omni Downloader web interface on Oracle Cloud so it can be used from a phone or desktop anywhere, with occasional private sharing with a few friends.

**Access model:** No login or password. The site is internet-accessible, so anyone who discovers the URL may be able to use it. Session monitoring and rate limits help identify or reduce abuse; they do not provide access control.

**Domain:** `omnidl.duckdns.org`

**How to use this checklist**
- **CODE** means changes or tests in the Omni Downloader repository.
- **MANUAL / SERVER** means Oracle Cloud, DNS, Linux, firewall, or service configuration.
- Complete the code-readiness gate before exposing the app publicly.
- Check items off only after doing and verifying them. Values below are starting settings, not performance guarantees.

---

## Phase 0 — Code-readiness gate (CODE)

Do these before opening the website to the public.

- [ ] Review the web routes and confirm which ones are required for the hosted version.
- [ ] Disable Flask debug mode for production.
- [ ] Confirm the app is run by Gunicorn, not Flask's development server.
- [ ] Bind Gunicorn to `127.0.0.1:8000`, not `0.0.0.0`.
- [ ] Validate URLs in every route that accepts a URL, including both format extraction and download creation.
- [ ] Allow only supported HTTP/HTTPS URLs and reject unsafe schemes and localhost/private/link-local/internal-network targets. Protect against redirects to internal destinations; do not rely on a regular expression alone.
- [ ] Validate all client-supplied options server-side (download type, format, resolution, playlist flag and item limits).
- [ ] Enforce a configurable per-video size cap: **500 MB default**, with an operator-configurable maximum of **2 GB or 5 GB** when needed.
- [ ] Enforce a small playlist item limit and a maximum number of queued jobs.
- [ ] Start with **one active download at a time**. Extra requests should be queued or rejected clearly.
- [ ] Add request rate limits to expensive endpoints such as format extraction and download creation.
- [ ] Ensure task IDs are unpredictable and each task can only retrieve its own output through the corresponding valid task/file mapping.
- [ ] Return generic errors to the browser; keep detailed diagnostics in server logs without secrets or cookie contents.
- [ ] Separate server paths from desktop paths. Use a fixed absolute server download directory outside the Git checkout.
- [ ] Disable or remove desktop-only routes/actions that launch files, open folders, or use native file dialogs.
- [ ] Ensure download jobs do not depend on a long-running synchronous HTTP request. Return a task ID and let the client poll for progress, then retrieve the result.
- [ ] Review task state and background threads. Start with a single Gunicorn worker; do not use multiple workers until in-memory task tracking and cleanup behavior are made process-safe.
- [ ] Make cleanup job-aware: never delete files while yt-dlp/FFmpeg is writing them or while a client is downloading them.
- [ ] Expire completed files after a configurable retention period (initial suggestion: **1–2 hours after completion**).
- [ ] Remove abandoned `.part` / `.ytdl` files only after confirming their jobs are no longer active and a safe timeout has passed.
- [ ] Check available disk space before starting a job; reject new work when free space approaches the configured reserve (initial suggestion: **10 GB**, if the selected disk size permits).
- [ ] Add lightweight session/activity tracking (details in Phase 1).
- [ ] Test server behavior and existing desktop functionality so server changes do not break the Windows app or Android APK.

### Phase 0 verification

- [ ] Invalid URLs and unsafe destinations are rejected.
- [ ] Oversized videos and excessive playlist requests are rejected.
- [ ] A second job is queued/rejected safely while one job is active.
- [ ] Cancelling a job stops its process and does not leave it permanently marked as running.
- [ ] Cleanup does not remove active downloads or files being transferred.
- [ ] A service restart does not leave jobs permanently stuck in an active state.
- [ ] Desktop app and Android APK functionality remains intact.

---

## Phase 1 — Session monitoring and abuse signals (CODE)

This is **monitoring, not authentication**. It cannot reliably count people or stop someone from sharing the URL.

- [ ] Assign each browser a random opaque session ID using a cookie; do not use IP addresses as the session identity.
- [ ] Record first-seen time, last-seen time, observed IP history and download/request counts.
- [ ] Record a new IP for an existing session without alerting or blocking solely because the IP changed.
- [ ] Flag more than **5 distinct browser sessions observed in a rolling 7-day window** for manual review.
- [ ] Flag unusually frequent extraction/download requests or repeated failures for review and/or temporary rate limiting.
- [ ] Expire inactive session records after a configurable retention period (initial suggestion: 30 days).
- [ ] Keep activity logs private, restrict file permissions, and avoid storing full download URLs if they may contain sensitive query parameters.
- [ ] Provide a simple way to inspect activity in server logs or a private admin-only view; do not expose session/IP logs on the public page.
- [ ] Document that cookie deletion, private browsing and multiple browsers can create extra sessions; multiple people can also share one IP.

---

## Phase 2 — Oracle Cloud provisioning (MANUAL / SERVER)

### A. Compute

- [ ] Create an OCI Compute instance using `VM.Standard.A1.Flex` (Ampere ARM64), if available in the chosen region.
- [ ] Start with **1–2 OCPUs and 6–12 GB RAM**, staying within the actual Always Free allowance shown for the tenancy.
- [ ] Do not assume 4 OCPUs / 24 GB is Always Free. Check the current OCI Free Tier resource page and the tenancy's usage.
- [ ] Choose Ubuntu 22.04 LTS or 24.04 LTS ARM64.
- [ ] Assign a public IPv4 address.
- [ ] Keep SSH access restricted to your own IP where practical; do not expose password-based SSH login.
- [ ] Choose a **50–100 GB boot volume** initially, accounting for all boot/block volumes and backups within the tenancy's shared storage allowance.
- [ ] Record the instance public IP and SSH connection details securely.

### B. Cost and resource monitoring

- [ ] Create an OCI budget and low-threshold email alerts.
- [ ] Treat budget alerts as notifications, not a hard spending cap or guarantee of zero charges.
- [ ] Confirm which compute, storage, IP and networking resources are eligible for Always Free in this tenancy and region before provisioning.
- [ ] Monitor disk usage and outbound bandwidth if usage grows.
- [ ] Do not run synthetic CPU-burning keepalive jobs. They cannot guarantee protection against OCI idle-instance reclamation.

---

## Phase 3 — Domain and network perimeter (MANUAL / SERVER)

### A. DuckDNS

- [ ] Update the DuckDNS `omnidl` record to the Oracle instance's public IPv4 address.
- [ ] If the public IP may change, configure a trusted DuckDNS updater and protect its token.
- [ ] Verify `omnidl.duckdns.org` resolves to the correct public IP before setting up HTTPS.

### B. OCI network rules

- [ ] In the VCN security list or network security group, allow inbound TCP **80 and 443** from the internet as required for HTTP redirection and HTTPS certificate issuance/access.
- [ ] Do **not** open ports 5000 or 8000 publicly.
- [ ] Keep SSH (TCP 22) restricted to trusted source IPs where practical.

### C. Host firewall

- [ ] Inspect the Ubuntu image's existing firewall rules before changing them.
- [ ] Configure the host firewall consistently with OCI rules, allowing the required web ports and preserving SSH access.
- [ ] Do not blindly apply `iptables -I INPUT 6` commands or assume `netfilter-persistent` is installed.
- [ ] Verify from outside the VM that ports 5000 and 8000 are not reachable.

---

## Phase 4 — Install and configure the server (MANUAL / SERVER)

- [ ] Install system updates.
- [ ] Install Python and the required system packages for the app.
- [ ] Install FFmpeg and verify it runs on ARM64.
- [ ] Create a dedicated non-root service account for Omni Downloader.
- [ ] Clone the repository to a fixed location, e.g. `/opt/omni-downloader`.
- [ ] Create a Python virtual environment and install pinned project dependencies plus Gunicorn.
- [ ] Create a runtime directory outside the repository, e.g. `/var/lib/omni-downloader/downloads`.
- [ ] Set ownership and restrictive permissions for runtime files.
- [ ] Configure environment variables in a root-owned or service-readable protected environment file; never commit secrets to Git.
- [ ] Test yt-dlp without cookies first against the intended sources.
- [ ] If a source requires cookies, store the cookie file outside the repository and web root, restrict permissions, and ensure it is not logged or served to clients.
- [ ] Test a normal video, audio extraction and a small playlist before public launch.

---

## Phase 5 — Production process and HTTPS (MANUAL / SERVER)

### A. Gunicorn and systemd

- [ ] Configure Gunicorn to run the correct Flask application object from the virtual environment.
- [ ] Bind to `127.0.0.1:8000`.
- [ ] Start with **one worker** until task state and background cleanup are process-safe.
- [ ] Configure systemd to run as the dedicated non-root service account, use the correct working directory and environment file, restart after failure, and start at boot.
- [ ] Verify the service starts successfully after reboot.
- [ ] Configure log rotation and ensure logs do not contain secrets, cookie contents or unnecessary sensitive URL data.

### B. Caddy and HTTPS

- [ ] Install Caddy using its current official installation instructions for Ubuntu.
- [ ] Configure `/etc/caddy/Caddyfile` with `omnidl.duckdns.org` reverse-proxying to `127.0.0.1:8000`.
- [ ] Validate the Caddy configuration before reloading.
- [ ] Confirm DNS points to the instance and inbound ports 80/443 work.
- [ ] Verify HTTPS certificate issuance, HTTP-to-HTTPS redirection and automatic renewal.
- [ ] Ensure the application trusts forwarded headers only from the local reverse proxy and does not accept spoofed client IP headers from arbitrary clients.

---

## Phase 6 — Storage and operational safety (CODE + MANUAL / SERVER)

### Code tasks

- [ ] Confirm the configured 500 MB default and the operator-controlled 2–5 GB upper setting behave as intended.
- [ ] Ensure the size limit is enforced by the server, not only the browser UI.
- [ ] Confirm active jobs and active file transfers are protected from cleanup.
- [ ] Ensure temporary files are cleaned after failures, cancellations and restarts.
- [ ] Ensure a low-disk-space condition prevents new jobs rather than filling the boot volume.

### Server tasks

- [ ] Monitor filesystem usage and set an alert or periodic check for low free space.
- [ ] Confirm the download directory is on the intended volume.
- [ ] Review retained files and logs periodically.
- [ ] Avoid a blanket cron command that deletes all files older than a fixed age without checking whether they are active.

---

## Phase 7 — Pre-launch acceptance tests (CODE + MANUAL / SERVER)

### Application tests

- [ ] The homepage and supported API routes work without an application login.
- [ ] Invalid URLs, unsupported protocols and internal-network targets are rejected.
- [ ] YouTube video, audio extraction and a supported social-media video/Reel work where the source permits downloading.
- [ ] A file below 500 MB downloads successfully.
- [ ] A file above 500 MB is allowed only when the higher limit is explicitly configured, and is rejected above that limit.
- [ ] A small playlist works within the configured item and resource limits.
- [ ] A second concurrent request is queued or rejected as designed.
- [ ] Session tracking records browser sessions and IP history; IP changes alone do not alert or block.
- [ ] More than five distinct sessions within seven days creates a review flag.
- [ ] Rate limits activate under repeated requests.
- [ ] Cleanup preserves active downloads and transfers.
- [ ] Errors are useful in private logs but do not expose secrets or internal tracebacks to users.

### Infrastructure tests

- [ ] `https://omnidl.duckdns.org` loads with a valid TLS certificate.
- [ ] HTTP redirects to HTTPS.
- [ ] External connections to ports 5000 and 8000 fail.
- [ ] The service recovers after a systemd restart and a VM reboot.
- [ ] DNS still points to the correct IP.
- [ ] Budget alerts are active.
- [ ] Disk usage, service logs and basic health can be checked without exposing private logs publicly.
- [ ] Test from both Wi-Fi and mobile data.

---

## Important operational notes

- No login means the URL is accessible to anyone who discovers it. Session tracking and rate limiting can help identify or reduce abuse, but they are not access control.
- A browser session is not a person. The five-session threshold is a review signal, not proof of unauthorized use.
- IP addresses can change legitimately; never alert or block solely on an IP change.
- Always Free availability and eligibility can depend on tenancy, region and current Oracle terms. Verify in the OCI Console before creating resources.
- Download only media you have permission to download and follow the relevant platform terms and copyright rules.
