import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

interface ChallengeData {
  id: number;
  title: string;
  description: string;
  type: string;
  start_date: string;
  end_date: string;
  prize_xp: number;
}

interface ParticipantData {
  user_id: string;
  current_value: number;
  rank: number;
  display_name: string;
}

interface ChallengeCardProps {
  challengeId: number;
}

const ChallengeCard: React.FC<ChallengeCardProps> = ({ challengeId }) => {
  const { data: challenge, loading: challengeLoading, error: challengeError } = useApi<ChallengeData>(
    `/community/challenges/${challengeId}`
  );
  
  const { data: participants, loading: participantsLoading, error: participantsError } = useApi<ParticipantData[]>(
    `/community/challenges/${challengeId}/participants`
  );

  if (challengeLoading || participantsLoading) {
    return <div className="text-center py-8">Cargando desafío...</div>;
  }
  
  if (challengeError || participantsError) {
    return <div className="text-center text-red-500 py-8">Error al cargar el desafío</div>;
  }
  
  if (!challenge) {
    return <div className="text-center py-8">Desafío no encontrado</div>;
  }

  const startDate = new Date(challenge.start_date);
  const endDate = new Date(challenge.end_date);
  const now = new Date();
  
  const isActive = now >= startDate && now <= endDate;
  const daysLeft = Math.max(0, Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 3600 * 24)));
  
  // Find user's position (simplified - would come from auth context in real app)
  const userPosition = participants.find(p => p.user_id === 'current-user-id');
  const userProgress = userPosition ? (userPosition.current_value / 100) * 100 : 0; // Assuming 100 is goal
  
  return (
    <div className="border rounded-lg p-5 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold text-lg">{challenge.title}</h3>
          <p className="text-sm text-gray-600">{challenge.description}</p>
        </div>
        <div className="text-right">
          {isActive ? (
            <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded">Activo</span>
          ) : (
            <span className="bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded">Próximamente</span>
          )}
        </div>
      </div>
      
      <div className="mb-4">
        <p className="text-sm text-gray-500">Del {startDate.toLocaleDateString()} al {endDate.toLocaleDateString()}</p>
        {!isActive && daysLeft > 0 && (
          <p className="text-sm font-medium text-blue-600">{daysLeft} días para comenzar</p>
        )}
        {isActive && daysLeft > 0 && (
          <p className="text-sm font-medium text-blue-600">{daysLeft} días restantes</p>
        )}
        {!isActive && daysLeft <= 0 && (
          <p className="text-sm font-medium text-red-600">Finalizado</p>
        )}
      </div>
      
      <div className="mb-4">
        <p className="text-sm font-medium mb-1">Progreso hacia el objetivo:</p>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className={`bg-gradient-to-r from-blue-500 to-indigo-600 h-2.5 rounded-full transition-width duration-700`}
            style={{ width: `${Math.min(userProgress, 100)}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 text-right mt-1">
          {Math.round(userProgress)}% completado
        </p>
      </div>
      
      <div className="mb-4">
        <p className="text-sm font-medium mb-1">Participantes y ranking:</p>
        {participants.slice(0, 5).map((participant, index) => (
          <div key={participant.user_id} className="flex justify-between items-center px-3 py-2 bg-gray-50 rounded">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-sm font-medium">
                {index + 1}
              </div>
              <div>
                <p className="font-medium">{participant.display_name}</p>
                <p className="text-sm text-gray-500">#{participant.rank}</p>
              </div>
            </div>
            <div className="text-right font-bold">
              {participant.current_value}
            </div>
          </div>
        ))}
        
        {participants.length > 5 && (
          <div className="text-center text-xs text-gray-500 mt-2">
            y {participants.length - 5} más participantes...
          </div>
        )}
      </div>
      
      {isActive && !userPosition && (
        <button 
          className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
          onClick={() => {
            // In real app, this would call API to join challenge
            console.log('Unirse al desafío:', challenge.id);
          }}
        >
          Unirse al desafío
        </button>
      )}
      
      {!isActive && (
        <div className="text-center text-xs text-gray-500">
          Este desafío no está activo actualmente
        </div>
      )}
    </div>
  );
};

export default ChallengeCard;