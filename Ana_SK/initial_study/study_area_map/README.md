# Alabama study-location map

The map highlights Baldwin, Clay, DeKalb, Etowah, Jefferson, Mobile, Montgomery, Morgan, Sumter and Tuscaloosa using actual 2025 US Census county boundaries. All 67 Alabama counties are drawn; the 57 outside this study are gray. Highlighting represents study inclusion, not concentration or model performance.

Boundary source: [US Census Bureau 2025 Cartographic Boundary Files](https://www.census.gov/geographies/mapping-files/2025/geo/carto-boundary-file.html), national county KML at 1:500,000, downloaded October 11, 2026. These are generalized geographic boundaries suitable for a study-location figure, not cadastral boundaries. The archive and its SHA-256 are retained for reproduction.

`Alabama_study_counties.png` is a high-resolution image; `Alabama_study_counties.svg` is an editable vector figure. `Alabama_counties_2025.geojson` contains all Alabama county polygons with a `study_county` attribute for reuse in GIS. `map_metadata.json` records the boundary source and projection.

Install numpy and matplotlib, then run `python create_map.py` in this folder. Use `--output` to select a destination. The script validates the expected 67 county boundaries and the ten study names before saving. It uses an equirectangular projection with standard parallel 32.5°N and central meridian 86.8°W. The scale bar is approximate away from that standard parallel.

Geographic interpretation: Morgan and DeKalb are in northern Alabama; Etowah lies south of DeKalb; Jefferson, Tuscaloosa and Clay are in the central part of the state; Sumter is along the western border; Montgomery lies farther south; Mobile and Baldwin are coastal counties. The monitoring and weather station locations are not shown on this county-location map. Highlighted county areas must not be interpreted as the geographic coverage of a single monitor's measurements.
