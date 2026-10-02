import { useState, useEffect, useMemo } from 'react';
import { useAppStore } from '../../store/appStore';

export default function TimeSlider() {
  const { selectedDate, setSelectedDate } = useAppStore();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  // Generate monthly dates from 2020-01-01 to 2025-12-01
  const dates = useMemo(() => {
    const list: string[] = [];
    for (let year = 2020; year <= 2025; year++) {
      for (let month = 1; month <= 12; month++) {
        const mStr = month < 10 ? `0${month}` : `${month}`;
        list.push(`${year}-${mStr}-01`);
      }
    }
    return list;
  }, []);

  const currentIndex = selectedDate && dates.includes(selectedDate)
    ? dates.indexOf(selectedDate)
    : dates.length - 1;

  // Auto-play logic (advance month every 1.2s)
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isPlaying) {
      interval = setInterval(() => {
        const currIdx = selectedDate ? dates.indexOf(selectedDate) : dates.length - 1;
        const nextIndex = (currIdx + 1) % dates.length;
        setSelectedDate(dates[nextIndex]);
      }, 1200);
    }
    return () => clearInterval(interval);
  }, [isPlaying, selectedDate, dates, setSelectedDate]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const index = parseInt(e.target.value, 10);
    setSelectedDate(dates[index]);
    setIsPlaying(false);
  };

  if (!isExpanded) {
    return (
      <div className="absolute bottom-4 left-4 z-[1000]">
        <button
          onClick={() => setIsExpanded(true)}
          className="bg-white/95 backdrop-blur hover:bg-white text-gray-800 font-semibold px-3 py-1.5 rounded-lg shadow-md border border-gray-200 text-xs flex items-center gap-2 transition-all hover:shadow-lg"
          title="Open Time-Lapse Player"
        >
          <span className="material-symbols-outlined text-blue-600" style={{ fontSize: '16px' }}>play_circle</span>
          <span>Time-Lapse Animation</span>
        </button>
      </div>
    );
  }

  return (
    <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur p-3 rounded-xl shadow-xl border border-gray-200 z-[1000] w-80 sm:w-96 flex flex-col gap-2 transition-all">
      <div className="flex justify-between items-center pb-1 border-b border-gray-100">
        <div className="flex items-center gap-1.5">
          <span className="material-symbols-outlined text-blue-600" style={{ fontSize: '18px' }}>timeline</span>
          <span className="text-xs font-bold text-gray-800">Time-Lapse Surveillance Player</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
            {selectedDate || dates[dates.length - 1]}
          </span>
          <button
            onClick={() => {
              setIsPlaying(false);
              setIsExpanded(false);
            }}
            className="text-gray-400 hover:text-gray-600 text-xs font-bold p-0.5 rounded hover:bg-gray-100"
            title="Minimize"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-2 rounded-full ${isPlaying ? 'bg-red-500 text-white' : 'bg-blue-600 text-white'} hover:opacity-90 shadow-sm flex items-center justify-center transition-all`}
          title={isPlaying ? 'Pause Animation' : 'Play Time-Lapse'}
        >
          {isPlaying ? (
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
          )}
        </button>

        <input
          type="range"
          min="0"
          max={dates.length - 1}
          value={currentIndex}
          onChange={handleSliderChange}
          className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
      </div>

      <div className="flex justify-between text-[10px] font-medium text-gray-400">
        <span>Jan 2020</span>
        <span>Monthly Risk Frames</span>
        <span>Dec 2025</span>
      </div>
    </div>
  );
}
