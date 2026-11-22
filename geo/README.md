# Geography

`bw_kreise.geojson` holds the 44 districts (Land- und Stadtkreise) of Baden-Württemberg with their official
district keys. The outlines come from [isellsoap/deutschlandGeoJSON](https://github.com/isellsoap/deutschlandGeoJSON)
(`4_kreise/3_mittel.geo.json`), which derives them from GADM via DIVA-GIS. GADM data is free for academic and other
non-commercial use. The outlines were simplified with `scripts/prepare_kreise.py`.

The 1,101 municipalities inside them are simulated (`src/world`): their names, positions, outlines and numbers are
not real. A newsroom would swap in the official VG250 municipal boundaries from the BKG.
