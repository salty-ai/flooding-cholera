import { useState, useEffect, useMemo } from 'react';
import { useAgentStore } from '../../store/agentStore';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

// Custom SVG Marker Icon for Leaflet
const dataPinIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzEzOTJlYyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIj48cGF0aCBkPSJNMTIgMmMtMy44NyAwLTcgMy4xMy03IDcgMCA1LjI1IDcgMTMgNyAxM3M3LTcuNzUgNy0xM2MwLTMuODctMy4xMy03LTctN3ptMCA5LjVjLTEuMzggMC0yLjUtMS4xMi0yLjUtMi41cyEuMTItMi41IDIuNS0yLjUgMi41IDEuMTIgMi41IDIuNS0xLjEyIDIuNS0yLjUgMi41eiIvPjwvc3ZnPg==',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
  popupAnchor: [0, -30],
});

export default function AgentExplorerView() {
  const { generatedUiSpec, uploadedDataset, setGeneratedUiSpec, setUploadedDataset } = useAgentStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const itemsPerPage = 8;

  // Restore spec and dataset on mount if it exists on the backend
  useEffect(() => {
    if (!generatedUiSpec) {
      fetch('/api/agent/active-spec')
        .then((res) => {
          if (res.ok) return res.json();
          return null;
        })
        .then((specData) => {
          if (specData && specData.config) {
            setGeneratedUiSpec(specData.config);
            if (specData.file_path) {
              fetch(`/api/agent/data?file_path=${encodeURIComponent(specData.file_path)}`)
                .then((res) => {
                  if (res.ok) return res.json();
                  throw new Error('Failed to load dataset');
                })
                .then((dataset) => {
                  setUploadedDataset(dataset);
                })
                .catch((err) => {
                  console.error('Error fetching dynamic dataset:', err);
                });
            }
          }
        })
        .catch((err) => console.error('Error restoring dashboard:', err));
    }
  }, []);

  // Generate Mock Data for Demo
  const handleLoadDemo = () => {
    const mockSpec = {
      title: "Outbreak Analysis Dashboard (Demo)",
      description: "AI-generated dashboard mapping spatial risk factors and cases from the uploaded file.",
      widgets: [
        {
          type: "kpi",
          title: "Total Outbreak Cases",
          gridSpan: 4,
          config: {
            valueKey: "cases",
            aggType: "sum",
            icon: "coronavirus",
            color: "red"
          }
        },
        {
          type: "kpi",
          title: "Average Flooding Risk Score",
          gridSpan: 4,
          config: {
            valueKey: "risk_score",
            aggType: "avg",
            icon: "water_drop",
            color: "blue"
          }
        },
        {
          type: "kpi",
          title: "Records Count",
          gridSpan: 4,
          config: {
            valueKey: "cases",
            aggType: "count",
            icon: "monitoring",
            color: "green"
          }
        },
        {
          type: "map",
          title: "Spatial Risk Mapping",
          gridSpan: 12,
          config: {
            latKey: "latitude",
            lngKey: "longitude",
            labelKey: "lga",
            valueKeyForMarker: "risk_score"
          }
        },
        {
          type: "chart",
          title: "Outbreak Cases by Region",
          gridSpan: 6,
          config: {
            chartType: "bar",
            xAxisKey: "lga",
            series: [
              { key: "cases", color: "#fa6238" }
            ]
          }
        },
        {
          type: "chart",
          title: "Precipitation vs Cases Correlation",
          gridSpan: 6,
          config: {
            chartType: "composed",
            xAxisKey: "date",
            series: [
              { key: "cases", color: "#fa6238", type: "line" },
              { key: "precipitation", color: "#1392ec", type: "area" }
            ]
          }
        },
        {
          type: "table",
          title: "Uploaded Dataset Table Viewer",
          gridSpan: 12,
          config: {}
        }
      ]
    };

    const mockData = [
      { lga: "Calabar Municipal", cases: 24, risk_score: 85, latitude: 4.9757, longitude: 8.3417, date: "05-28", precipitation: 45.2 },
      { lga: "Odukpani", cases: 12, risk_score: 60, latitude: 5.1319, longitude: 8.3431, date: "05-29", precipitation: 30.1 },
      { lga: "Akpabuyo", cases: 18, risk_score: 75, latitude: 4.8879, longitude: 8.4414, date: "05-30", precipitation: 55.4 },
      { lga: "Ogoja", cases: 35, risk_score: 90, latitude: 6.6547, longitude: 8.7981, date: "05-31", precipitation: 72.8 },
      { lga: "Obudu", cases: 5, risk_score: 40, latitude: 6.6667, longitude: 9.1667, date: "06-01", precipitation: 20.0 },
      { lga: "Ikom", cases: 21, risk_score: 80, latitude: 5.9617, longitude: 8.7208, date: "06-02", precipitation: 61.2 }
    ];

    setGeneratedUiSpec(mockSpec);
    setUploadedDataset(mockData);
  };

  // Auto-detect categorical columns for filters
  const filterOptions = useMemo(() => {
    if (!uploadedDataset || uploadedDataset.length === 0) return [];
    
    const sampleKeys = Object.keys(uploadedDataset[0]);
    const optionsList: { key: string; label: string; values: string[] }[] = [];
    
    sampleKeys.forEach((key) => {
      const keyLower = key.toLowerCase();
      if (
        keyLower.includes('latitude') || 
        keyLower.includes('longitude') || 
        keyLower.includes('lat') || 
        keyLower.includes('lng') || 
        keyLower.includes('lon') ||
        keyLower === 'sn' ||
        keyLower === 'id' ||
        keyLower.includes('date')
      ) {
        return;
      }
      
      const uniqueVals = Array.from(
        new Set(
          uploadedDataset
            .map((row) => row[key])
            .filter((val) => val !== null && val !== undefined && val !== '')
        )
      ).map((val) => String(val));
      
      // Allow filters with unique values between 2 and 25
      if (uniqueVals.length > 1 && uniqueVals.length < 25) {
        optionsList.push({
          key,
          label: key.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
          values: uniqueVals.sort(),
        });
      }
    });
    
    return optionsList;
  }, [uploadedDataset]);

  // Apply filters dynamically
  const filteredDataset = useMemo(() => {
    if (!uploadedDataset) return [];
    return uploadedDataset.filter((row) => {
      return Object.entries(filters).every(([col, val]) => {
        if (!val) return true;
        return String(row[col]) === String(val);
      });
    });
  }, [uploadedDataset, filters]);

  // ── Render Landing State ───────────────────────────────────────────────
  if (!generatedUiSpec || !uploadedDataset || uploadedDataset.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] p-8">
        <div className="max-w-2xl bg-white border border-[#e6e8eb] rounded-2xl p-8 shadow-sm text-center">
          <div className="size-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="material-symbols-outlined text-primary" style={{ fontSize: '36px' }}>
              extension
            </span>
          </div>
          <h2 className="text-xl font-bold text-[#111518] mb-3">Agent Explorer</h2>
          <p className="text-sm text-[#637588] leading-relaxed mb-6">
            Upload custom surveillance data (CSV or Excel) and have the AI Copilot dynamically design an interactive dashboard. The layout will adapt in real-time based on the geographical, temporal, or numerical data detected in your file.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left mb-8">
            <div className="bg-[#f8f9fb] border border-[#e6e8eb] rounded-xl p-4">
              <span className="material-symbols-outlined text-primary mb-2">upload_file</span>
              <h4 className="text-xs font-bold text-[#111518] mb-1">1. Attach File</h4>
              <p className="text-[10px] text-[#637588]">Drop a CSV/Excel file into the AI Copilot chat.</p>
            </div>
            <div className="bg-[#f8f9fb] border border-[#e6e8eb] rounded-xl p-4">
              <span className="material-symbols-outlined text-primary mb-2">assistant</span>
              <h4 className="text-xs font-bold text-[#111518] mb-1">2. Prompt Agent</h4>
              <p className="text-[10px] text-[#637588]">Ask: "Build a custom UI layout to analyze this data."</p>
            </div>
            <div className="bg-[#f8f9fb] border border-[#e6e8eb] rounded-xl p-4">
              <span className="material-symbols-outlined text-primary mb-2">dashboard</span>
              <h4 className="text-xs font-bold text-[#111518] mb-1">3. Interact</h4>
              <p className="text-[10px] text-[#637588]">Explore maps, charts, and computed metrics here.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={handleLoadDemo}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-br from-primary to-blue-600 text-white font-semibold text-xs shadow-md shadow-primary/20 hover:opacity-90 active:scale-95 transition-all"
            >
              Load Demo Dashboard
            </button>
            <span className="text-xs text-[#94a3b8] font-medium">or upload a file in the Copilot sidebar.</span>
          </div>
        </div>
      </div>
    );
  }

  // ── Render Generated Dashboard ──────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border border-[#e6e8eb] rounded-xl p-5 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-lg font-bold text-[#111518]">{generatedUiSpec.title}</h2>
          <p className="text-xs text-[#637588] mt-1">{generatedUiSpec.description}</p>
        </div>
        <button
          onClick={() => {
            setGeneratedUiSpec(null);
            setUploadedDataset([]);
            setFilters({});
          }}
          className="px-3.5 py-2 border border-[#e6e8eb] text-xs font-semibold text-[#637588] hover:bg-slate-50 rounded-xl transition-colors active:scale-95"
        >
          Reset Explorer
        </button>
      </div>

      {/* Global Interactive Filters */}
      {filterOptions.length > 0 && (
        <div className="bg-white border border-[#e6e8eb] rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '18px' }}>
              filter_list
            </span>
            <span className="text-xs font-bold text-[#111518] uppercase tracking-wider">
              Interactive Global Filters
            </span>
            {Object.values(filters).some(Boolean) && (
              <button
                onClick={() => setFilters({})}
                className="ml-auto text-[10px] font-bold text-primary hover:underline cursor-pointer"
              >
                Clear Filters
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {filterOptions.map((opt) => (
              <div key={opt.key} className="space-y-1">
                <label className="text-[10px] font-bold text-[#637588] block truncate">
                  {opt.label}
                </label>
                <select
                  value={filters[opt.key] || ''}
                  onChange={(e) => {
                    setFilters((prev) => ({
                      ...prev,
                      [opt.key]: e.target.value,
                    }));
                    setCurrentPage(1);
                  }}
                  className="w-full px-2 py-1.5 border border-[#e6e8eb] rounded-lg text-xs bg-slate-50 hover:bg-slate-100 transition-colors focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
                >
                  <option value="">All {opt.label}s</option>
                  {opt.values.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Widgets Grid */}
      <div className="grid grid-cols-12 gap-6">
        {generatedUiSpec.widgets.map((widget: any, idx: number) => {
          const span = widget.gridSpan || 6;
          const key = `widget-${idx}`;

          // ── KPI Card Widget ────────────────────────────────────────────────
          if (widget.type === 'kpi') {
            const { valueKey, aggType, icon, color } = widget.config;
            const numericValues = filteredDataset
              .map((row) => Number(row[valueKey]))
              .filter((val) => !isNaN(val));

            let val: number | string = 0;
            if (aggType === 'sum') {
              val = numericValues.reduce((acc, curr) => acc + curr, 0);
            } else if (aggType === 'avg') {
              val = numericValues.length ? (numericValues.reduce((acc, curr) => acc + curr, 0) / numericValues.length).toFixed(1) : 0;
            } else {
              val = filteredDataset.length;
            }

            const formattedVal = typeof val === 'number' ? val.toLocaleString() : val;
            const colorClass = color === 'red' ? 'bg-red-50 text-red-600 border-red-200' :
              color === 'blue' ? 'bg-blue-50 text-blue-600 border-blue-200' :
                'bg-green-50 text-green-600 border-green-200';

            return (
              <div key={key} className={`col-span-12 md:col-span-${span} bg-white border border-[#e6e8eb] rounded-xl p-5 shadow-sm`}>
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[#637588] text-xs font-semibold uppercase tracking-wider block mb-1">
                      {widget.title}
                    </span>
                    <span className="text-3xl font-bold text-[#111518] tracking-tight">
                      {formattedVal}
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-xl border ${colorClass}`}>
                    <span className="material-symbols-outlined flex items-center justify-center" style={{ fontSize: '20px' }}>
                      {icon || 'trending_up'}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] text-[#94a3b8] mt-2 font-medium">
                  Aggregated via <span className="font-mono text-primary">{aggType}</span> on {valueKey.replace('_', ' ')}
                </p>
              </div>
            );
          }

          // ── Map Widget ───────────────────────────────────────────────────
          if (widget.type === 'map') {
            const { latKey, lngKey, labelKey, valueKeyForMarker } = widget.config;

            // Extract valid points with fallback to backend geocoded coordinates
            const points = filteredDataset
              .map((row, index) => {
                let lat = Number(row[latKey]);
                let lng = Number(row[lngKey]);
                if (isNaN(lat) || lat === 0 || isNaN(lng) || lng === 0) {
                  // Fallback to backend-injected coordinates
                  lat = Number(row["latitude"]);
                  lng = Number(row["longitude"]);
                }
                return {
                  id: index,
                  lat,
                  lng,
                  label: String(row[labelKey] || 'Location'),
                  val: row[valueKeyForMarker] !== undefined ? Number(row[valueKeyForMarker]) : null,
                  details: row,
                };
              })
              .filter((p) => !isNaN(p.lat) && !isNaN(p.lng) && p.lat !== 0 && p.lng !== 0);

            if (points.length === 0) {
              return (
                <div key={key} className={`col-span-12 lg:col-span-${span} bg-white border border-[#e6e8eb] rounded-xl p-5 shadow-sm flex items-center justify-center min-h-[350px]`}>
                  <div className="text-center">
                    <span className="material-symbols-outlined text-slate-300 mb-2" style={{ fontSize: '36px' }}>pin_drop</span>
                    <p className="text-xs font-semibold text-[#637588]">No valid coordinates found in the dataset</p>
                  </div>
                </div>
              );
            }

            // Calculate center
            const avgLat = points.reduce((acc, curr) => acc + curr.lat, 0) / points.length;
            const avgLng = points.reduce((acc, curr) => acc + curr.lng, 0) / points.length;

            return (
              <div key={key} className={`col-span-12 lg:col-span-${span} bg-white border border-[#e6e8eb] rounded-xl overflow-hidden shadow-sm`}>
                <div className="p-4 border-b border-[#e6e8eb] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[#637588]" style={{ fontSize: '18px' }}>explore</span>
                  <h3 className="font-bold text-[#111518] text-sm">{widget.title}</h3>
                </div>
                <div className="h-[350px] relative z-0">
                  <MapContainer center={[avgLat, avgLng]} zoom={8} className="w-full h-full">
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    {points.map((p) => (
                      <Marker key={p.id} position={[p.lat, p.lng]} icon={dataPinIcon}>
                        <Popup>
                          <div className="p-1 font-display">
                            <strong className="block text-sm border-b pb-1 mb-1.5 text-[#111518]">{p.label}</strong>
                            <div className="space-y-1 text-xs">
                              {p.val !== null && (
                                <p className="text-[#637588]">
                                  <span className="font-semibold text-slate-700 capitalize">{valueKeyForMarker.replace('_', ' ')}:</span> {p.val}
                                </p>
                              )}
                              <p className="text-[10px] text-[#94a3b8]">Coordinates: {p.lat.toFixed(4)}, {p.lng.toFixed(4)}</p>
                            </div>
                          </div>
                        </Popup>
                      </Marker>
                    ))}
                  </MapContainer>
                </div>
              </div>
            );
          }

          // ── Chart Widget ─────────────────────────────────────────────────
          if (widget.type === 'chart') {
            const { chartType, xAxisKey, series } = widget.config;

            // Group and aggregate data dynamically to prevent duplicate x-axis labels
            const chartData = useMemo(() => {
              const groups: Record<string, any> = {};
              filteredDataset.forEach((row) => {
                const groupVal = String(row[xAxisKey] || 'N/A');
                if (!groups[groupVal]) {
                  groups[groupVal] = { [xAxisKey]: groupVal };
                  series.forEach((s: any) => {
                    const plotKey = s.key === xAxisKey ? `${s.key}_count` : s.key;
                    groups[groupVal][plotKey] = 0;
                  });
                  groups[groupVal]._count = 0;
                }
                groups[groupVal]._count += 1;
                
                series.forEach((s: any) => {
                  const plotKey = s.key === xAxisKey ? `${s.key}_count` : s.key;
                  const val = row[s.key];
                  const numVal = Number(val);
                  
                  if (s.key === xAxisKey || isNaN(numVal)) {
                    groups[groupVal][plotKey] += 1;
                  } else {
                    groups[groupVal][plotKey] += numVal;
                  }
                });
              });

              // Apply average aggregation logic for risk/score numeric series
              return Object.values(groups).map((group: any) => {
                series.forEach((s: any) => {
                  const plotKey = s.key === xAxisKey ? `${s.key}_count` : s.key;
                  const isAverageVariable = 
                    s.key.toLowerCase().includes('risk') || 
                    s.key.toLowerCase().includes('score') || 
                    s.key.toLowerCase().includes('avg') ||
                    s.key.toLowerCase().includes('dehydration') ||
                    s.key.toLowerCase().includes('age');
                    
                  if (s.key !== xAxisKey && isAverageVariable && typeof group[plotKey] === 'number') {
                    group[plotKey] = Number((group[plotKey] / group._count).toFixed(1));
                  }
                });
                return group;
              }).sort((a: any, b: any) => {
                const valA = a[xAxisKey];
                const valB = b[xAxisKey];
                const numA = Number(valA);
                const numB = Number(valB);
                if (!isNaN(numA) && !isNaN(numB)) {
                  return numA - numB;
                }
                return String(valA).localeCompare(String(valB), undefined, { numeric: true, sensitivity: 'base' });
              });
            }, [filteredDataset, xAxisKey, series]);

            return (
              <div key={key} className={`col-span-12 lg:col-span-${span} bg-white border border-[#e6e8eb] rounded-xl p-5 shadow-sm flex flex-col`}>
                <div className="flex justify-between items-center mb-5 border-b border-[#f0f2f5] pb-3">
                  <h3 className="font-bold text-[#111518] text-sm">{widget.title}</h3>
                  <div className="flex gap-3 text-[10px] font-semibold text-[#637588]">
                    {series.map((s: any) => {
                      const labelName = s.key === xAxisKey ? 'Total Cases' : s.key.replace('_', ' ');
                      return (
                        <div key={s.key} className="flex items-center gap-1.5 capitalize">
                          <span className="size-2 rounded-full" style={{ backgroundColor: s.color }} />
                          {labelName}
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="h-[260px] w-full flex-none">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
                      <XAxis
                        dataKey={xAxisKey}
                        tick={{ fontSize: 10, fill: '#637588' }}
                        axisLine={{ stroke: '#e6e8eb' }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fontSize: 10, fill: '#637588' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #e6e8eb',
                          borderRadius: '8px',
                          fontSize: '11px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }} />
                      {series.map((s: any) => {
                        const plotKey = s.key === xAxisKey ? `${s.key}_count` : s.key;
                        const labelName = s.key === xAxisKey ? 'Count' : s.key.replace('_', ' ');
                        const type = s.type || chartType;
                        if (type === 'bar') {
                          return (
                            <Bar
                              key={s.key}
                              dataKey={plotKey}
                              fill={s.color}
                              name={labelName}
                              radius={[4, 4, 0, 0]}
                            />
                          );
                        } else if (type === 'area') {
                          return (
                            <Area
                              key={s.key}
                              type="monotone"
                              dataKey={plotKey}
                              fill={`${s.color}25`}
                              stroke={s.color}
                              strokeWidth={2}
                              name={labelName}
                            />
                          );
                        } else {
                          return (
                            <Line
                              key={s.key}
                              type="monotone"
                              dataKey={plotKey}
                              stroke={s.color}
                              strokeWidth={2.5}
                              dot={{ fill: s.color, strokeWidth: 0, r: 3 }}
                              name={labelName}
                            />
                          );
                        }
                      })}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            );
          }

          // ── Data Table Widget ─────────────────────────────────────────────
          if (widget.type === 'table') {
            const columns = Object.keys(filteredDataset[0] || {}).filter(c => c !== 'latitude' && c !== 'longitude');
            
            // Search filter
            const filteredRows = filteredDataset.filter((row) =>
              columns.some((col) =>
                String(row[col] || '')
                  .toLowerCase()
                  .includes(searchTerm.toLowerCase())
              )
            );

            // Pagination
            const totalPages = Math.ceil(filteredRows.length / itemsPerPage);
            const paginatedRows = filteredRows.slice(
              (currentPage - 1) * itemsPerPage,
              currentPage * itemsPerPage
            );

            return (
              <div key={key} className="col-span-12 bg-white border border-[#e6e8eb] rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-[#e6e8eb] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <h3 className="font-bold text-[#111518] text-sm">{widget.title}</h3>
                    <p className="text-[10px] text-[#637588] mt-0.5">Records count: {filteredRows.length}</p>
                  </div>
                  <div className="relative w-full sm:w-64">
                    <span className="material-symbols-outlined text-[#94a3b8] absolute left-3 top-1/2 -translate-y-1/2" style={{ fontSize: '16px' }}>
                      search
                    </span>
                    <input
                      type="text"
                      placeholder="Search dataset..."
                      value={searchTerm}
                      onChange={(e) => {
                        setSearchTerm(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full pl-9 pr-4 py-2 border border-[#e6e8eb] rounded-xl text-xs focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all bg-slate-50"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                     <thead>
                      <tr className="bg-[#f8f9fb] border-b border-[#e6e8eb]">
                        {columns.map((col) => (
                          <th key={col} className="px-4 py-2.5 text-[10px] font-bold text-[#637588] uppercase tracking-wider sanitize-col">
                            {col.replace('_', ' ')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#f0f2f5] text-xs">
                      {paginatedRows.length > 0 ? (
                        paginatedRows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-50/50">
                            {columns.map((col) => (
                              <td key={col} className="px-4 py-2.5 font-medium text-[#111518]">
                                {row[col] !== null ? String(row[col]) : <span className="text-[#94a3b8] font-light italic">null</span>}
                              </td>
                            ))}
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={columns.length} className="text-center py-8 text-[#94a3b8] font-medium">
                            No matching records found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="p-4 border-t border-[#e6e8eb] flex justify-between items-center bg-[#f8f9fb]">
                    <span className="text-[10px] text-[#637588] font-medium">
                      Page {currentPage} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setCurrentPage((c) => Math.max(1, c - 1))}
                        disabled={currentPage === 1}
                        className="px-2.5 py-1 border border-[#e6e8eb] bg-white rounded-lg text-xs font-semibold text-[#637588] hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95"
                      >
                        Prev
                      </button>
                      <button
                        onClick={() => setCurrentPage((c) => Math.min(totalPages, c + 1))}
                        disabled={currentPage === totalPages}
                        className="px-2.5 py-1 border border-[#e6e8eb] bg-white rounded-lg text-xs font-semibold text-[#637588] hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-95"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          }

          // ── Text Widget ──────────────────────────────────────────────────
          if (widget.type === 'text') {
            return (
              <div key={key} className={`col-span-12 lg:col-span-${span} bg-white border border-[#e6e8eb] rounded-xl p-5 shadow-sm flex flex-col`}>
                <h3 className="font-bold text-[#111518] text-sm mb-3 border-b border-[#f0f2f5] pb-2">
                  {widget.title}
                </h3>
                <p className="text-xs text-[#637588] leading-relaxed whitespace-pre-wrap font-medium">
                  {widget.config.text}
                </p>
              </div>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}
