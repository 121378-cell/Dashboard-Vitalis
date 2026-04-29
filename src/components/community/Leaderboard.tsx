import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

interface LeaderboardEntry {
  display_name: string;
  rank: number;
  score: number;
}

interface ChallengeLeaderboard {
  challenge_id: number;
  title: string;
  leaderboard: LeaderboardEntry[];
}

interface LeaderboardProps {
  type?: 'weekly' | 'monthly' | 'all-time';
  metric?: 'workouts' | 'volume' | 'readiness' | 'streak' | 'xp';
}

const Leaderboard: React.FC<LeaderboardProps> = ({ type = 'weekly', metric = 'workouts' }) => {
  const { data, loading, error } = useApi<ChallengeLeaderboard[]>(
    `/community/leaderboard/${metric}?type=${type}`
  );
  const [userRank, setUserRank] = useState<number | null>(null);
  const [userScore, setUserScore] = useState<number | null>(null);

  useEffect(() => {
    if (data) {
      // Find user's position in leaderboard (simplified - in reality would come from API)
      const allEntries = data.flatMap(challenge => challenge.leaderboard);
      // This would be replaced with actual user ID lookup
      const userEntry = allEntries.find(entry => entry.display_name === 'Tu Nombre');
      if (userEntry) {
        setUserRank(userEntry.rank);
        setUserScore(userEntry.score);
      }
    }
  }, [data]);

  if (loading) return <div className="text-center py-10">Cargando leaderboard...</div>;
  if (error) return <div className="text-center text-red-500 py-10">Error al cargar el leaderboard</div>;

  const metricsMap: Record<string, string> = {
    workouts: 'Entrenamientos',
    volume: 'Volumen (kg)',
    readiness: 'Readiness Promedio',
    streak: 'Racha de Días Activos',
    xp: 'XP Ganado'
  };

  const periodMap: Record<string, string> = {
    weekly: 'Semanal',
    monthly: 'Mensual',
    'all-time': 'Histórico'
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Leaderboard de {metricsMap[metric]}</h2>
        <div className="flex space-x-3">
          <select 
            className="border rounded px-3 py-1"
            value={type}
            onChange={(e) => {
              // In a real app, this would trigger a refetch with new type
              console.log('Cambiar periodo a:', e.target.value);
            }}
          >
            <option value="weekly">Semanal</option>
            <option value="monthly">Mensual</option>
            <option value="all-time">Histórico</option>
          </select>
          <select 
            className="border rounded px-3 py-1"
            value={metric}
            onChange={(e) => {
              // In a real app, this would trigger a refetch with new metric
              console.log('Cambiar métrica a:', e.target.value);
            }}
          >
            <option value="workouts">Entrenamientos</option>
            <option value="volume">Volumen</option>
            <option value="readiness">Readiness</option>
            <option value="streak">Racha</option>
            <option value="xp">XP</option>
          </select>
        </div>
      </div>

      {data.map((challenge) => (
        <div key={challenge.challenge_id} className="border rounded-lg p-4">
          <h3 className="font-semibold mb-3">{challenge.title}</h3>
          <div className="space-y-2">
            {challenge.leaderboard.slice(0, 10).map((entry, index) => (
              <div 
                key={entry.display_name} 
                className={`flex justify-between items-center px-3 py-2 ${index === 0 ? 'bg-gradient-to-r from-amber-50 to-yellow-50' : 'bg-gray-50'} rounded`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-sm font-medium">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium">{entry.display_name}</p>
                    <p className="text-sm text-gray-500">#{entry.rank}</p>
                  </div>
                </div>
                <div className="text-right font-bold">
                  {entry.score}
                </div>
              </div>
            ))}
            
            {/* User's position if not in top 10 */}
            {userRank !== null && userRank > 10 && (
              <div className="border-t pt-3 mt-4 space-y-2">
                <div className="flex justify-between items-center px-3 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 rounded">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-200 rounded-full flex items-center justify-center text-sm font-medium">
                      {userRank}
                    </div>
                    <div>
                      <p className="font-medium">Tu Nombre</p>
                      <p className="text-sm text-gray-500">#{userRank}</p>
                    </div>
                  </div>
                  <div className="text-right font-bold text-blue-600">
                    {userScore}
                  </div>
                </div>
                <p className="text-xs text-gray-500 text-center">
                  Tu posición en el leaderboard completo
                </p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default Leaderboard;