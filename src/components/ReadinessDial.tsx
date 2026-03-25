import React from 'react';

interface Props {
  score: number;
  status: string;
}

export const ReadinessDial: React.FC<Props> = ({ score, status }) => {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (score >= 75) return 'stroke-green-400';
    if (score >= 50) return 'stroke-orange-400';
    return 'stroke-red-400';
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-4">
      <svg className="w-32 h-32 transform -rotate-90">
        <circle
          cx="64" cy="64" r={radius}
          stroke="currentColor" strokeWidth="8"
          fill="transparent"
          className="text-surface-variant/20"
        />
        <circle
          cx="64" cy="64" r={radius}
          stroke="currentColor" strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`transition-all duration-1000 ${getColor()}`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-black">{score}</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          {status}
        </span>
      </div>
    </div>
  );
};
