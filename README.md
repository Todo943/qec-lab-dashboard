# QEC LAB — shared result uploads (GitHub Pages + Supabase)

**Website:** https://todo943.github.io/qec-lab-dashboard/

This is a compact, dark-mode quantum error correction dashboard for team results, detector diagnostics and guest uploads. It uses your saved Garnet aggregate as an included example. The saved Emerald circuit images are labeled as a separate hardware artifact.

## Features

- Overview: hardware vs. simulation logical failure probabilities, per-round LER fits, uncertainty bars, metadata, CSV export.
- Decoder: shot/detector heatmap, detector firing rates, syndrome weights, decoder failure fraction when predictions and observables are supplied.
- Circuit: two pre-existing reference PNGs for the logical and native Emerald circuit.
- Experiments: public history of shared runs.
- Upload: guest JSON or CSV file uploads, validated in-browser, with publication to Supabase and automatic refresh every 60 seconds.
- Responsive layout: works on desktop and mobile; no npm install, build step or server backend to operate the UI.

**Important:** Running this webpage by itself without database configuration allows file PREVIEW but does **not** store uploads for other viewers. To enable shared submissions, complete the instructions below.

## One-time installation (repository owner)

1. Create a Supabase project at https://supabase.com/. Use the free tier if suitable. The project must have a publicly reachable Data API.
2. In Supabase, open **SQL Editor**, paste the contents of [`supabase_setup.sql`](./supabase_setup.sql), and run it. This creates `public.qec_experiments` with row-level security (RLS). Public browser visitors can read and insert but cannot update or delete rows.
3. Under **Project Settings / Data API or API Keys**, copy the **Project URL** (for example `https://projectref.supabase.co`) and a **Publishable key** beginning `sb_publishable_`.
4. Edit `config.js` in your downloaded dashboard project:

   ```js
   window.QEC_CONFIG = {
     supabaseUrl: "https://YOUR_PROJECT_REF.supabase.co",
     supabasePublishableKey: "sb_publishable_YOUR_PUBLIC_BROWSER_KEY"
   };
   ```

   The publishable key is meant to be included in a public website; it is not a secret. **Never** use an IQM Resonance API token, Supabase secret key, or Supabase `service_role` key in public files. See Supabase's official API-key documentation.
5. Replace your site's existing `index.html` with this version and upload **all** files and folders as shown below, preserving their paths. Commit them to `main`. You can upload with GitHub's website or use Git CLI. The simplest current arrangement is **GitHub Pages → Deploy from a branch → main / (root)**. If you've already enabled GitHub Actions deployment, either switch back to branch deployment or adjust your workflow to publish the new site files; do not use the old catalog-building workflow without adapting it.
6. Reload https://todo943.github.io/qec-lab-dashboard/ . At bottom left it should say **Shared · connected**. Select **Upload result**, load the example JSON, validate, and publish a test run. Open the site in a different browser and verify that the new row appears in Experiments. Refresh manually or wait for the 60-second poll.

### Required repo layout

```
index.html
style.css
app.js
config.js
supabase_setup.sql
assets/
  circuit_logical_d3_Z_r1.png
  circuit_native_d3_Z_r1_emerald.png
examples/
  garnet_d3_z_results.json
  aggregate_rounds.csv
  synthetic_detector_events.json
README.md
TEAM_GUIDE.md
.nojekyll
```

The SQL file and documentation may be public; they contain no credentials. `config.js` exposes ONLY the public publishable key. You should still review every file for private tokens before committing.

### Keeping an existing GitHub Actions workflow

If your repository still contains `.github/workflows/deploy.yml` from the previous dashboard, it may deploy `dist/` instead of the root. **Remove or update that old workflow** before publishing this version, or it may keep serving the old HTML. For the simplest one-off setup, switch Pages to **Deploy from a branch**, and remove `.github/workflows/deploy.yml` if it is not used for anything else. The dashboard pulls results directly from Supabase, so it does not need deployment each time someone uploads data.

## How visitors upload

1. Click **+ Upload result**.
2. Drop or browse a JSON or CSV file. Max 2 MB.
3. Read the validation summary. Set a clear experiment name, device, code distance and X/Z basis. For detector datasets, optionally choose the aggregate experiment they belong to.
4. Click **Publish to dashboard**. The upload is stored in the public `qec_experiments` table. It becomes visible to all visitors, without a GitHub commit or login.
5. Select it in **Overview** or **Decoder**. Click **Refresh** if needed; the app also polls every 60 seconds.

### Supported aggregate JSON

Same structure as your existing Hackathon JSON:

```json
{
  "device": "garnet", "distance": 3, "basis": "Z", "shots": 5000,
  "hardware": {"1": [0.12, 0.0045], "2": [0.19, 0.0055]},
  "simulation": {"1": [0.01, 0.001], "2": [0.02, 0.0015]}
}
```

At least one of `hardware` or `simulation` is required. `round` keys must be positive integers; probabilities are FRACTIONS in [0, 0.5], not percentage numbers. Each round can contain `[p, standard_error]`, `[p]`, or a numeric `p`. For missing uncertainties the dashboard uses a simple binomial standard error if shots are provided. You need at least two distinct round counts to fit a reliable one-parameter LER.

### Supported aggregate CSV

```csv
round,hardware_p,hardware_se,simulation_p,simulation_se
1,0.12,0.0045,0.01,0.001
2,0.19,0.0055,0.02,0.0015
```

A single series with `round,p,se` is treated as hardware. CSV uploads don't contain other experiment metadata: enter those in the upload form. See `examples/aggregate_rounds.csv`.

### Supported detector JSON

```json
{
  "det_events": [[0,1,0],[1,0,0],[0,0,1]],
  "obs_flips": [[0],[1],[0]],
  "predicted_flips": [[0],[0],[0]]
}
```

For real data, use the post-processed arrays from `counts_to_events()` and your decoder. The matrix must be rectangular. If predictions and observations are both present, the dashboard calculates the fraction of shots with at least one differing logical observable bit. If they're absent, the failure probability is shown as unavailable. A bare IQM raw counts file is not enough to compute detector events; the circuit's detector definitions are also needed.

`examples/synthetic_detector_events.json` is explicitly a **synthetic demo**, not a recorded hardware experiment. Do not relabel it as hardware.

## Safety, capacity and limitations

- **Unrestricted guest uploads:** This is what you requested, but **anyone on the internet who obtains the website or publishable key can submit data**; this is not true access control by possession of the link. An attacker can spam uploads or consume database storage. Avoid putting sensitive or private data in this project. If you later need public uploads at scale, place a rate-limited serverless API and spam protection (e.g. Turnstile) in front of Supabase instead of using open anonymous INSERT.
- Visitors can neither edit nor delete existing uploads through the website. A project administrator can moderate/delete records in the Supabase dashboard.
- Browser validation and the SQL table constraints help with malformed files, but the SQL constraints only validate basic structure and size. **Uploaded scientific results are unverified claims.**
- Public API is configured for up to 100 latest rows per refresh. Older records still exist in Supabase but will not appear in the first page. For significantly more data, implement pagination and backend aggregation.
- The detector display shows only 35 shots and the first 50 detectors; the file may have many more shots (up to the size limit). Very large per-shot runs should be exported as summaries, partitioned datasets or saved in a dedicated object storage system.
- Results are **not automatically sent from IQM Resonance**. Teammates upload the saved JSON/CSV output. No quantum circuits are submitted by this page.
- LER per-round fitting assumes the one-parameter model `P_L(r) = (1 - (1 - 2ε)^r)/2`. The code uses a weighted minimum-χ² fit when at least two round points exist, which can disagree with previously saved unweighted estimates. This model may fit poorly; χ²/dof is shown to highlight that limitation.
- Reference circuit PNGs are from Emerald, while the built-in results are labeled Garnet; the dashboard keeps that distinction explicit.

## Local preview

Serve the directory if you want to test URL fetch behavior:

```bash
python -m http.server 8000
# Open http://localhost:8000
```

Directly opening index.html without a local server also displays the bundled sample. Supabase networking requires a browser with normal internet access.

## Relevant documentation

- https://supabase.com/docs/guides/api
- https://supabase.com/docs/guides/getting-started/api-keys
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
