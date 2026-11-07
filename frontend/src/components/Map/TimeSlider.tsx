import React, { useState, useEffect, useMemo } from 'react';
import { useAppStore } from '../../store/appStore';

export default function TimeSlider() {
  const { selectedDate, setSelectedDate } = useAppStore();
  const [isPlaying, setIsPlaying] = useState(false);
  
  // Generate date range (last 90 days) - memoized to avoid recalculation on every render
  const dates = useMemo(() => {
    const today = new Date();
    return Array.from({ length: 91 }, (_, i) => {
      const d = new Date(today);
      d.setDate(d.getDate() - (90 - i));
      return d.toISOString().split('T')[0];
    });
  }, []);

  const currentIndex = selectedDate 
    ? dates.indexOf(selectedDate) 
    : dates.length - 1;

  // Auto-play logic
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isPlaying) {
      interval = setInterval(() => {
        const nextIndex = (dates.indexOf(selectedDate || dates[dates.length - 1]) + 1) % dates.length;
        setSelectedDate(dates[nextIndex]);
      }, 1000); // 1 second per day
    }
    return () => clearInterval(interval);
  }, [isPlaying, selectedDate, dates, setSelectedDate]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const index = parseInt(e.target.value);
    setSelectedDate(dates[index]);
    setIsPlaying(false); // Stop playing if user drags
  };

  return (
    <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 bg-white p-4 rounded-lg shadow-lg z-[1000] w-96 flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-bold text-gray-700">Time-Lapse Mode</span>
        <span className="text-sm font-mono text-blue-600">
          {selectedDate || dates[dates.length - 1]}
        </span>
      </div>
      
      <div className="flex items-center gap-4">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-2 rounded-full ${isPlaying ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'} hover:opacity-80`}
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
          ) : (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>
        
        <input
          type="range"
          min="0"
          max={dates.length - 1}
          value={currentIndex}
          onChange={handleSliderChange}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
      </div>
      
      <div className="flex justify-between text-xs text-gray-400">
        <span>3 Months Ago</span>
        <span>Today</span>
      </div>
    </div>
  );
}
