import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "../api";

// Basemap: OpenFreeMap (OpenStreetMap data, no key). ADR 0015's own PMTiles replace it in SPEC-020.
const STYLE = import.meta.env.VITE_MAP_STYLE ?? "https://tiles.openfreemap.org/styles/positron";
// If the basemap cannot be reached, the chosen road or ward is drawn on a plain background instead.
const PLAIN: maplibregl.StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "#eef2ef" } }],
};
const MUMBAI: [number, number] = [72.86, 19.07];

export function MapView({ placeId }: { placeId: string | null }) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map>();
  const feature = useRef<GeoJSON.Feature | null>(null);
  // Set on the style's own load event. Not map.isStyleLoaded(): that stays false while basemap tiles download,
  // which dropped a shape that arrived in the meantime.
  const ready = useRef(false);

  const draw = () => {
    const m = map.current;
    const f = feature.current;
    if (!m || !f || !ready.current) return;
    const source = m.getSource("place") as maplibregl.GeoJSONSource | undefined;
    if (source) source.setData(f);
    else {
      m.addSource("place", { type: "geojson", data: f });
      m.addLayer({ id: "place-fill", type: "fill", source: "place", filter: ["==", "$type", "Polygon"], paint: { "fill-color": "#0f5c4c", "fill-opacity": 0.12 } });
      m.addLayer({ id: "place-line", type: "line", source: "place", layout: { "line-cap": "round" }, paint: { "line-color": "#d9480f", "line-width": ["case", ["==", ["geometry-type"], "Polygon"], 2, 6] } });
    }
    const bounds = new maplibregl.LngLatBounds();
    const walk = (c: unknown): void => {
      if (Array.isArray(c) && typeof c[0] === "number") bounds.extend(c as [number, number]);
      else if (Array.isArray(c)) c.forEach(walk);
    };
    walk((f.geometry as { coordinates: unknown }).coordinates);
    if (!bounds.isEmpty()) m.fitBounds(bounds, { padding: 40, maxZoom: 15, duration: 500 });
  };

  useEffect(() => {
    if (!box.current) return;
    const m = new maplibregl.Map({ container: box.current, style: STYLE, center: MUMBAI, zoom: 10.5, attributionControl: { compact: true } });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("style.load", () => {
      ready.current = true;
      draw();
    });
    m.on("error", () => undefined); // a missing tile must not break the page
    const fallback = window.setTimeout(() => {
      if (!ready.current) m.setStyle(PLAIN);
    }, 6000);
    map.current = m;
    return () => {
      window.clearTimeout(fallback);
      m.remove();
    };
  }, []);

  useEffect(() => {
    if (!placeId) return;
    let cancelled = false;
    api
      .shape(placeId)
      .then((f) => {
        if (cancelled) return;
        feature.current = f;
        draw();
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [placeId]);

  return <div ref={box} className="map" role="img" aria-label="Map" />;
}
