# 6. One SQL for DuckDB and Postgres/PostGIS; SvelteKit for the newsroom app

**Status:** accepted

**Context:** Reporters query releases on a laptop. The newsroom server runs Postgres. The lab needs speed.

**Decision:**
- A `Store` contract with three implementations: memory for the lab, DuckDB as the default, and Postgres with PostGIS for the server, where neighbours are found by outline.
- The same SQL runs on both databases.
- A test plays a season through each store and requires identical decisions.
- The app is a static SvelteKit build (Svelte 5, D3, MapLibre without tiles), served from S3 next to its data files.

**Consequences:** Swapping the store changes nothing the newsroom sees. The app needs no server; its data files are the published reports.
