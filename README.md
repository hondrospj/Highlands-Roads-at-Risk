# Highlands Roads at Risk

Static GitHub Pages app for drawing road and cross-section profiles through the Highlands municipal DEM.

The interface follows the North Wildwood Roads at Risk reference: threshold presets, NAVD88/MLLW conversion, terrain and hillshade views, saved multi-line cross sections, flood-history and future-frequency charts, and CSV/Shapefile exports.

Municipal constants:

- Observations: USGS 01407600, Sea Bright
- PETSS / NOAA station: 8531804
- NAVD88 thresholds: 3.07 ft minor, 4.07 ft moderate, 5.07 ft major
- MLLW thresholds: 5.2 ft minor, 6.2 ft moderate, 7.2 ft major
- MLLW = NAVD88 + 2.13 ft

Terrain source: USGS 3DEP Bare Earth DEM Dynamic ImageServer, clipped to the Highlands Borough boundary at 5-foot resolution.
