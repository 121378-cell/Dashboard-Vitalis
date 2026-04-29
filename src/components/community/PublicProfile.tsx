import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

interface PublicProfileData {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  is_public: boolean;
  statistics: {
    total_workouts: number;
    best_readiness: number;
    current_level: number;
  };
}

interface PublicProfileProps {
  userId: string;
}

const PublicProfile: React.FC<PublicProfileProps> = ({ userId }) => {
  const { data, loading, error } = useApi<PublicProfileData>(
    `/community/profile/${userId}`
  );
  
  const [isFollowing, setIsFollowing] = useState(false);

  if (loading) return <div className="text-center py-12">Cargando perfil...</div>;
  if (error) return <div className="text-center text-red-500 py-12">Error al cargar el perfil</div>;
  
  if (!data) return <div className="text-center py-12">Perfil no encontrado</div>;

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <div className="flex flex-col items-center text-center mb-8">
        {data.avatar_url ? (
          <img 
            src={data.avatar_url} 
            alt={`${data.display_name}'s avatar`} 
            className="w-24 h-24 rounded-full mb-4 object-cover"
          />
        ) : (
          <div className="w-24 h-24 rounded-full bg-gray-300 flex items-center justify-center text-white font-bold mb-4">
            {data.display_name.charAt(0).toUpperCase()}
          </div>
        )}
        
        <h2 className="text-2xl font-bold">{data.display_name}</h2>
        <p className="text-gray-600">Nivel {data.statistics.current_level}</p>
        
        {!data.is_public && (
          <div className="mt-3 px-4 py-2 bg-red-100 text-red-800 text-sm rounded">
            Este perfil es privado
          </div>
        )}
        
        {data.is_public && !isFollowing && (
          <button 
            onClick={() => setIsFollowing(true)}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
          >
            Seguir
          </button>
        )}
        
        {isFollowing && (
          <span className="mt-4 text-green-600 font-medium">¡Siguiendo!</span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="border rounded-lg p-4 text-center">
          <p className="text-gray-500 text-sm mb-1">Entrenamientos Totales</p>
          <p className="text-2xl font-bold">{data.statistics.total_workouts}</p>
        </div>
        
        <div className="border rounded-lg p-4 text-center">
          <p className="text-gray-500 text-sm mb-1">Mejor Readiness</p>
          <p className="text-2xl font-bold">{data.statistics.best_readiness}</p>
        </div>
        
        <div className="border rounded-lg p-4 text-center">
          <p className="text-gray-500 text-sm mb-1">Nivel Actual</p>
          <p className="text-2xl font-bold">{data.statistics.current_level}</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="border-t pt-4">
          <h3 className="text-lg font-semibold mb-3">Logros y Estadísticas</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Racha actual:</span>
              <span className="font-medium text-gray-800">7 días</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Mejor racha:</span>
              <span className="font-medium text-gray-800">21 días</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Volumen total levantado:</span>
              <span className="font-medium text-gray-800">1.250 kg</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">XP total ganado:</span>
              <span className="font-medium text-gray-800">15.420 XP</span>
            </div>
          </div>
        </div>
        
        <div className="border-t pt-4">
          <h3 className="text-lg font-semibold mb-3">Desafíos Recientes</h3>
          {/* In a real app, this would come from an API endpoint */}
          <div className="space-y-2">
            <div className="flex justify-between items-center px-3 py-2 bg-gray-50 rounded">
              <span className="text-sm font-medium">Desafío de Semanal de Hierro</span>
              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Completado</span>
            </div>
            <div className="flex justify-between items-center px-3 py-2 bg-gray-50 rounded">
              <span className="text-sm font-medium">Desafío Mensual de Volumen</span>
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">En progreso</span>
            </div>
          </div>
        </div>
        
          <div className="border-t pt-4">
            <h3 className="text-lg font-semibold mb-3">Compartir Perfil</h3>
            <p className="text-sm text-gray-600 mb-3">
              Comparte tu perfil públicamente para que otros vean tus logros y progreso
            </p>
          
          <div className="flex flex-col sm:flex-row sm:space-x-3">
            <input 
              type="text" 
              value={`https://atlas.app/profile/${data.user_id}`} 
              readOnly
              className="p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button 
              onClick={() => {
                navigator.clipboard.writeText(`https://atlas.app/profile/${data.user_id}`);
                alert('Link copiado al portapapeles');
              }}
              className="mt-2 sm:mt-0 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Copiar Link
            </button>
          </div>
        </div>
        
        {/* Botón de desafiar (para futura implementación) */}
        <div className="border-t pt-6">
          <button 
            className="w-full bg-purple-600 text-white py-3 px-6 rounded hover:bg-purple-700 transition-colors"
            disabled
          >
            Desafiar (Próximamente)
          </button>
        </div>
      </div>
    </div>
  );
};

export default PublicProfile;