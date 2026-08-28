import { useState, useEffect } from 'react';

interface Facility {
  id: number;
  global_id: string;
  name: string;
  type: string;
  category: string;
  functional_status: string;
  state_name: string;
  lga_name: string;
  latitude: number | null;
  longitude: number | null;
}

interface FacilityStats {
  total_facilities: number;
  functional_rate_pct: number;
  functional_status_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
}

const STATES = [
  'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno',
  'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'FCT', 'Gombe',
  'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara',
  'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau',
  'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
];

export default function FacilitiesView() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [stats, setStats] = useState<FacilityStats | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [selectedState, setSelectedState] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const limit = 50;

  // Fetch Stats
  useEffect(() => {
    let url = '/api/facilities/stats';
    if (selectedState) {
      url += `?state=${encodeURIComponent(selectedState)}`;
    }
    fetch(url)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error('Failed to load facility stats:', err));
  }, [selectedState]);

  // Fetch Facilities List
  useEffect(() => {
    setLoading(true);
    let url = `/api/facilities/?skip=${page * limit}&limit=${limit}`;
    if (selectedState) url += `&state=${encodeURIComponent(selectedState)}`;
    if (selectedType) url += `&type=${encodeURIComponent(selectedType)}`;
    if (selectedStatus) url += `&functional_status=${encodeURIComponent(selectedStatus)}`;
    if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;

    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        setFacilities(data.facilities || []);
        setTotal(data.total || 0);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load facilities:', err);
        setLoading(false);
      });
  }, [selectedState, selectedType, selectedStatus, searchQuery, page]);

  return (
    <div className="flex flex-col gap-4 sm:gap-6 p-2 sm:p-6 bg-[#f8fafc] min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 sm:p-6 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">FMOH Health Facility Registry</h1>
          <p className="text-xs sm:text-sm text-gray-500 mt-1">
            Official Federal Ministry of Health registry covering 46,146 facilities across all 36 states & FCT
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] sm:text-xs font-semibold bg-blue-100 text-blue-800">
            Validated Official Dataset
          </span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="bg-white p-3 sm:p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[10px] sm:text-xs font-medium text-gray-500 uppercase tracking-wider">Total Facilities</div>
          <div className="text-lg sm:text-2xl font-bold text-gray-900 mt-1 sm:mt-2">
            {stats?.total_facilities?.toLocaleString() ?? '46,146'}
          </div>
          <div className="text-[10px] sm:text-xs text-blue-600 font-medium mt-0.5">Nationwide</div>
        </div>

        <div className="bg-white p-3 sm:p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[10px] sm:text-xs font-medium text-gray-500 uppercase tracking-wider">Functional Rate</div>
          <div className="text-lg sm:text-2xl font-bold text-emerald-600 mt-1 sm:mt-2">
            {stats?.functional_rate_pct ?? '—'}%
          </div>
          <div className="text-[10px] sm:text-xs text-gray-500 mt-0.5">
            {stats?.functional_status_breakdown?.['Functional']?.toLocaleString() ?? '—'} Functional
          </div>
        </div>

        <div className="bg-white p-3 sm:p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[10px] sm:text-xs font-medium text-gray-500 uppercase tracking-wider">Primary Health</div>
          <div className="text-lg sm:text-2xl font-bold text-gray-900 mt-1 sm:mt-2">
            {stats?.type_breakdown?.['Primary']?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[10px] sm:text-xs text-gray-500 mt-0.5">PHCs & Clinics</div>
        </div>

        <div className="bg-white p-3 sm:p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[10px] sm:text-xs font-medium text-gray-500 uppercase tracking-wider">Secondary & Referral</div>
          <div className="text-lg sm:text-2xl font-bold text-gray-900 mt-1 sm:mt-2">
            {((stats?.type_breakdown?.['Secondary'] ?? 0) + (stats?.type_breakdown?.['Tertiary'] ?? 0))?.toLocaleString() ?? '—'}
          </div>
          <div className="text-[10px] sm:text-xs text-gray-500 mt-0.5">Hospitals</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3 sm:p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-2 sm:gap-4">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Search facility name..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(0);
            }}
            className="w-full px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* State Select */}
        <select
          value={selectedState}
          onChange={(e) => {
            setSelectedState(e.target.value);
            setPage(0);
          }}
          className="px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">All States (36 + FCT)</option>
          {STATES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Type Select */}
        <select
          value={selectedType}
          onChange={(e) => {
            setSelectedType(e.target.value);
            setPage(0);
          }}
          className="px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">All Care Types</option>
          <option value="Primary">Primary</option>
          <option value="Secondary">Secondary</option>
          <option value="Tertiary">Tertiary</option>
        </select>

        {/* Functional Status Select */}
        <select
          value={selectedStatus}
          onChange={(e) => {
            setSelectedStatus(e.target.value);
            setPage(0);
          }}
          className="px-3 py-2 text-xs sm:text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="">All Statuses</option>
          <option value="Functional">Functional</option>
          <option value="Partially Functional">Partially Functional</option>
          <option value="Not Functional">Not Functional</option>
        </select>

        {/* Reset button */}
        {(selectedState || selectedType || selectedStatus || searchQuery) && (
          <button
            onClick={() => {
              setSelectedState('');
              setSelectedType('');
              setSelectedStatus('');
              setSearchQuery('');
              setPage(0);
            }}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 py-1"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Facilities Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-3 sm:p-4 border-b border-gray-200 flex flex-row items-center justify-between">
          <div className="text-xs sm:text-sm font-bold text-gray-900">
            Facilities ({total.toLocaleString()})
          </div>
          <div className="text-[10px] sm:text-xs text-gray-500">
            {page * limit + 1} - {Math.min((page + 1) * limit, total)}
          </div>
        </div>

        {loading ? (
          <div className="p-8 sm:p-12 text-center text-gray-500 text-xs sm:text-sm">
            <div className="animate-spin rounded-full h-6 w-6 sm:h-8 sm:w-8 border-b-2 border-blue-600 mx-auto mb-2 sm:mb-3"></div>
            Loading FMOH registry...
          </div>
        ) : facilities.length === 0 ? (
          <div className="p-8 sm:p-12 text-center text-gray-500 text-xs sm:text-sm">
            No health facilities match your filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm text-gray-600 min-w-[600px]">
              <thead className="bg-gray-50 text-[10px] sm:text-xs font-semibold uppercase text-gray-500 border-b border-gray-200">
                <tr>
                  <th className="px-3 sm:px-4 py-2.5">Facility Name</th>
                  <th className="px-3 sm:px-4 py-2.5">Type</th>
                  <th className="px-3 sm:px-4 py-2.5">Status</th>
                  <th className="px-3 sm:px-4 py-2.5">LGA</th>
                  <th className="px-3 sm:px-4 py-2.5">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {facilities.map((fac) => (
                  <tr key={fac.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-3 sm:px-4 py-2.5 font-semibold text-gray-900">{fac.name}</td>
                    <td className="px-3 sm:px-4 py-2.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium ${
                          fac.type === 'Primary'
                            ? 'bg-blue-100 text-blue-800'
                            : fac.type === 'Secondary'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {fac.type || 'Primary'}
                      </span>
                    </td>
                    <td className="px-3 sm:px-4 py-2.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium ${
                          fac.functional_status === 'Functional'
                            ? 'bg-emerald-100 text-emerald-800'
                            : fac.functional_status === 'Partially Functional'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {fac.functional_status || 'Functional'}
                      </span>
                    </td>
                    <td className="px-3 sm:px-4 py-2.5">{fac.lga_name || '—'}</td>
                    <td className="px-3 sm:px-4 py-2.5">{fac.state_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="p-3 sm:p-4 border-t border-gray-200 flex items-center justify-between">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="px-2.5 py-1 sm:px-3 sm:py-1.5 border border-gray-300 rounded text-[10px] sm:text-xs font-medium text-gray-700 disabled:opacity-50 hover:bg-gray-50"
          >
            Prev
          </button>
          <span className="text-[10px] sm:text-xs text-gray-500">
            Page {page + 1} of {Math.ceil(total / limit) || 1}
          </span>
          <button
            disabled={(page + 1) * limit >= total}
            onClick={() => setPage((p) => p + 1)}
            className="px-2.5 py-1 sm:px-3 sm:py-1.5 border border-gray-300 rounded text-[10px] sm:text-xs font-medium text-gray-700 disabled:opacity-50 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
