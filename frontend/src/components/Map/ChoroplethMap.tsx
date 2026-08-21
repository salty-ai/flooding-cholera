import React, { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import HealthFacilitiesLayer from './HealthFacilitiesLayer';
import TimeSlider from './TimeSlider';
import type { Layer, PathOptions } from 'leaflet';
import { renderToString } from 'react-dom/server';
import type { GeoJSONFeatureCollection, LGAProperties, RiskLevel } from '../../types';
import { useGeojson } from '../../hooks/useApi';
import { useAppStore } from '../../store/appStore';
import LGATooltip from './LGATooltip';

const RISK_COLORS: Record<RiskLevel, string> = {
  green: '#22c55e',
  yellow: '#eab308',
  red: '#ef4444',
  unknown: '#6b7280',
};

const NIGERIA_NATIONAL_CENTER: [number, number] = [9.082, 8.675];
const DEFAULT_ZOOM = 6;

function getStyle(riskLevel: RiskLevel): PathOptions {
  const color = RISK_COLORS[riskLevel] || RISK_COLORS.unknown;
  return {
    fillColor: color,
    fillOpacity: 0.6,
    color: color,
    weight: 2,
    opacity: 1,
  };
}

function getHighlightStyle(riskLevel: RiskLevel): PathOptions {
  const color = RISK_COLORS[riskLevel] || RISK_COLORS.unknown;
  return {
    fillColor: color,
    fillOpacity: 0.8,
    color: '#1e3a8a',
    weight: 3,
    opacity: 1,
  };
}

function getHiddenStyle(): PathOptions {
  return {
    fillOpacity: 0,
    opacity: 0,
  };
}

interface MapControllerProps {
  selectedLGAId: number | null;
  geojson: GeoJSONFeatureCollection | null;
}

function MapController({ selectedLGAId, geojson }: MapControllerProps) {
  const map = useMap();

  useEffect(() => {
    if (selectedLGAId && geojson) {
      const feature = geojson.features.find(f => f.properties.id === selectedLGAId);
      if (feature && feature.geometry) {
        // Calculate bounds from geometry
        const coords = feature.geometry.coordinates;
        if (coords && coords.length > 0) {
          try {
            // For MultiPolygon or Polygon, get all coordinates
            const allCoords: [number, number][] = [];

            if (feature.geometry.type === 'MultiPolygon') {
              (coords as number[][][][]).forEach(polygon => {
                polygon.forEach(ring => {
                  ring.forEach(coord => {
                    allCoords.push([coord[1], coord[0]]);
                  });
                });
              });
            } else if (feature.geometry.type === 'Polygon') {
              (coords as number[][][]).forEach(ring => {
                ring.forEach(coord => {
                  allCoords.push([coord[1], coord[0]]);
                });
              });
            }

            if (allCoords.length > 0) {
              const bounds = allCoords.reduce(
                (acc, coord) => {
                  return [
                    [Math.min(acc[0][0], coord[0]), Math.min(acc[0][1], coord[1])],
                    [Math.max(acc[1][0], coord[0]), Math.max(acc[1][1], coord[1])],
                  ] as [[number, number], [number, number]];
                },
                [[90, 180], [-90, -180]] as [[number, number], [number, number]]
              );
              map.fitBounds(bounds, { padding: [50, 50], maxZoom: 11 });
            }
          } catch {
            // Fallback to centroid
            if (feature.properties.centroid_lat && feature.properties.centroid_lon) {
              map.setView(
                [feature.properties.centroid_lat, feature.properties.centroid_lon],
                10
              );
            }
          }
        }
      }
    }
  }, [selectedLGAId, geojson, map]);

  return null;
}


interface ChoroplethLayerProps {
  geojson: GeoJSONFeatureCollection;
  onLGAClick: (lgaId: number) => void;
  selectedLGAId: number | null;
  visibleRiskLevels: Set<RiskLevel>;
}

function ChoroplethLayer({ geojson, onLGAClick, selectedLGAId, visibleRiskLevels }: ChoroplethLayerProps) {
  const geoJsonRef = useRef<L.GeoJSON | null>(null);

  const onEachFeature = (feature: GeoJSON.Feature, layer: Layer) => {
    const properties = feature.properties as LGAProperties;
    const isVisible = visibleRiskLevels.has(properties.risk_level);

    layer.on({
      click: () => {
        if (isVisible) {
          onLGAClick(properties.id);
        }
      },
      mouseover: (e) => {
        if (isVisible) {
          const target = e.target as L.Path;
          target.setStyle(getHighlightStyle(properties.risk_level));
          target.bringToFront();
        }
      },
      mouseout: (e) => {
        if (isVisible) {
          const target = e.target as L.Path;
          if (properties.id !== selectedLGAId) {
            target.setStyle(getStyle(properties.risk_level));
          }
        }
      },
    });

    // Bind tooltip using the LGATooltip React component
    if (isVisible) {
      const tooltipContent = renderToString(
        <LGATooltip
          name={properties.name}
          riskLevel={properties.risk_level}
          riskScore={properties.risk_score}
          recentCases={properties.recent_cases}
          recentDeaths={properties.recent_deaths}
        />
      );
      layer.bindTooltip(tooltipContent, {
        sticky: true,
        className: 'lga-tooltip-container',
        direction: 'top',
        offset: [0, -10],
      });
    }
  };

  const style = (feature: GeoJSON.Feature | undefined) => {
    if (!feature) return {};
    const properties = feature.properties as LGAProperties;
    const isVisible = visibleRiskLevels.has(properties.risk_level);

    if (!isVisible) {
      return getHiddenStyle();
    }

    if (properties.id === selectedLGAId) {
      return getHighlightStyle(properties.risk_level);
    }
    return getStyle(properties.risk_level);
  };

  return (
    <GeoJSON
      key={Array.from(visibleRiskLevels).join('-')} // Force re-render when filters change
      ref={geoJsonRef}
      data={geojson}
      style={style}
      onEachFeature={onEachFeature}
    />
  );
}

interface FloodLayerProps {
  selectedLGAId: number | null;
}

/**
 * Layer component that fetches and renders SAR flood tiles from Google Earth Engine.
 * Overlays a blue tile layer representing water extent on top of the base map.
 * 
 * @param selectedLGAId - The ID of the currently selected LGA.
 */
function FloodLayer({ selectedLGAId }: FloodLayerProps) {
  const [tileUrl, setTileUrl] = React.useState<string | null>(null);
  const { selectedDate } = useAppStore();

  useEffect(() => {
    if (!selectedLGAId) {
      setTileUrl(null);
      return;
    }

    const controller = new AbortController();

    // Fetch tile URL for the selected LGA
    const fetchTiles = async () => {
      try {
        const dateParam = selectedDate ? `?date=${selectedDate}` : '';
        const response = await fetch(
          `/api/satellite/tiles/flood/${selectedLGAId}${dateParam}`,
          { signal: controller.signal }
        );
        if (response.ok && !controller.signal.aborted) {
          const data = await response.json();
          setTileUrl(data.url);
        } else if (!controller.signal.aborted) {
          setTileUrl(null);
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error("Failed to fetch flood tiles:", error);
          setTileUrl(null);
        }
      }
    };

    fetchTiles();

    return () => controller.abort();
  }, [selectedLGAId, selectedDate]);

  if (!tileUrl) return null;

  return (
    <TileLayer
      url={tileUrl}
      opacity={0.8}
      zIndex={100} // Ensure it sits on top of the base map but below tooltips
    />
  );
}

export default function ChoroplethMap() {
  const { selectedLGAId, setSelectedLGAId, setSelectedLGA, filters, selectedDate } = useAppStore();
  const { data: geojson, isLoading: loading, error } = useGeojson(selectedDate || undefined);

  // Calculate visible risk levels based on filters
  const visibleRiskLevels = useMemo(() => {
    const levels = new Set<RiskLevel>();
    if (filters.showHighRisk) levels.add('red');
    if (filters.showMediumRisk) levels.add('yellow');
    if (filters.showLowRisk) {
      levels.add('green');
      levels.add('unknown');
    }
    return levels;
  }, [filters.showHighRisk, filters.showMediumRisk, filters.showLowRisk]);

  const handleLGAClick = (lgaId: number) => {
    setSelectedLGAId(lgaId);
    // Find LGA details from geojson
    if (geojson) {
      const feature = geojson.features.find(f => f.properties.id === lgaId);
      if (feature) {
        setSelectedLGA({
          id: feature.properties.id,
          name: feature.properties.name,
          code: feature.properties.code,
          population: feature.properties.population,
          centroid_lat: feature.properties.centroid_lat,
          centroid_lon: feature.properties.centroid_lon,
          created_at: '',
          updated_at: '',
        });
      }
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-100 rounded-lg" role="status" aria-label="Loading map">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" aria-hidden="true"></div>
          <p className="mt-4 text-gray-600">Loading map data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-100 rounded-lg" role="alert">
        <div className="text-center text-red-600">
          <p>Error loading map: {error instanceof Error ? error.message : 'Unknown error'}</p>
          <p className="text-sm text-gray-500 mt-2">Please ensure the backend is running.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full absolute inset-0">
      <MapContainer
        center={NIGERIA_NATIONAL_CENTER}
        zoom={DEFAULT_ZOOM}
        className="h-full w-full"
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
        aria-label="Cholera risk map of Nigeria (774 LGAs)"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geojson && (
          <>
            <ChoroplethLayer
              geojson={geojson}
              onLGAClick={handleLGAClick}
              selectedLGAId={selectedLGAId}
              visibleRiskLevels={visibleRiskLevels}
            />
            <FloodLayer selectedLGAId={selectedLGAId} />
            <HealthFacilitiesLayer />
            <MapController selectedLGAId={selectedLGAId} geojson={geojson} />
          </>
        )}
      </MapContainer>
      
      <TimeSlider />

      {/* Legend */}
      <div
        className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-[1000]"
        role="region"
        aria-label="Map legend"
      >
        <h4 className="text-sm font-semibold mb-2">Risk Level</h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: RISK_COLORS.green }}
              aria-hidden="true"
            ></div>
            <span className="text-xs">Low Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: RISK_COLORS.yellow }}
              aria-hidden="true"
            ></div>
            <span className="text-xs">Medium Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: RISK_COLORS.red }}
              aria-hidden="true"
            ></div>
            <span className="text-xs">High Risk</span>
          </div>
        </div>
      </div>
    </div>
  );
}
