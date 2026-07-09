import { useMemo } from 'react';
import { format } from 'date-fns';
import { useRiskScores, useSatelliteData } from './useApi';

export function useSatelliteFeedLogic() {
  const { data: satelliteData, isLoading } = useSatelliteData();

  const feedItems = useMemo(() => {
    if (!satelliteData || satelliteData.length === 0) return [];

    // Sort by NDWI (water index) and take top 3
    return [...satelliteData]
      .sort((a, b) => (b.ndwi || 0) - (a.ndwi || 0))
      .slice(0, 3)
      .map(item => ({
        label: item.lga_name,
        time: format(new Date(item.observation_date), 'h:mm a'),
        color: item.flood_observed ? 'red' : (item.ndwi || 0) > 0.15 ? 'yellow' : 'green',
        ndwi: item.ndwi || 0,
        rainfall: item.rainfall_mm || 0,
      }));
  }, [satelliteData]);

  return { feedItems, isLoading };
}

export function useRiskChartLogic() {
  const { data: riskScores, isLoading } = useRiskScores();

  // Get top 5 LGAs by flood risk
  const regions = useMemo(() => {
    if (!riskScores || riskScores.length === 0) return [];

    return riskScores
      .slice() // Clone to avoid mutation
      .sort((a, b) => b.score - a.score)
      .slice(0, 5)
      .map(score => ({
        name: score.lga_name || `LGA ${score.lga_id}`,
        risk: Math.round(score.score * 100),
        color: score.level === 'red' ? '#fa6238' : score.level === 'yellow' ? '#eab308' : '#22c55e',
      }));
  }, [riskScores]);

  const maxRisk = Math.max(...regions.map(r => r.risk));
  const criticalCount = regions.filter(r => r.risk > 70).length;

  return { regions, maxRisk, criticalCount, isLoading };
}
