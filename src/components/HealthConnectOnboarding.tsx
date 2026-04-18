import React from 'react';
import { motion } from 'motion/react';
import { Heart, Activity, Flame, Moon, Footprints, ShieldCheck } from 'lucide-react';
import { useHealthConnectPermissions } from '../hooks/useHealthConnectPermissions';

interface HealthConnectOnboardingProps {
  onComplete?: () => void;
  onSkip?: () => void;
}

export const HealthConnectOnboarding: React.FC<HealthConnectOnboardingProps> = ({ onComplete, onSkip }) => {
  const { requestPermissions } = useHealthConnectPermissions();

  const handleConnect = async () => {
    await requestPermissions();
    if (onComplete) onComplete();
  };

  const handleSkip = () => {
    if (onSkip) onSkip();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-sm overflow-hidden bg-gray-900 border border-gray-800 rounded-3xl shadow-2xl relative"
      >
        <div className="absolute inset-0 bg-gradient-to-t from-emerald-900/20 to-transparent pointer-events-none" />
        
        <div className="p-8 relative z-10">
          <motion.div 
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", delay: 0.2 }}
            className="flex items-center justify-center w-16 h-16 mx-auto mb-6 bg-gradient-to-br from-emerald-400 to-teal-600 rounded-full shadow-lg shadow-emerald-500/30"
          >
            <Activity className="w-8 h-8 text-white" />
          </motion.div>
          
          <h2 className="mb-2 text-2xl font-bold text-center text-white">Conecta tu salud</h2>
          <p className="mb-8 text-sm text-center text-gray-400">
            Para darte el mejor consejo, Vitalis necesita acceder a tus datos a través de Health Connect:
          </p>

          <div className="space-y-3 mb-8">
            <PermissionItem icon={<Heart size={20} />} label="Ritmo Cardíaco" delay={0.3} />
            <PermissionItem icon={<Moon size={20} />} label="Sueño" delay={0.4} />
            <PermissionItem icon={<Footprints size={20} />} label="Pasos" delay={0.5} />
            <PermissionItem icon={<Flame size={20} />} label="Calorías" delay={0.6} />
            <PermissionItem icon={<ShieldCheck size={20} />} label="Biométricas" delay={0.7} />
          </div>

          <div className="space-y-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleConnect}
              className="w-full py-3.5 font-semibold text-white transition-all bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl hover:shadow-lg hover:shadow-emerald-500/25"
            >
              Conectar Health Connect
            </motion.button>
            <div className="relative flex items-center py-2">
              <div className="flex-grow border-t border-gray-800"></div>
              <span className="flex-shrink-0 mx-4 text-xs font-medium text-gray-500 uppercase tracking-widest">o</span>
              <div className="flex-grow border-t border-gray-800"></div>
            </div>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSkip}
              className="w-full py-3.5 font-semibold text-gray-300 transition-all bg-gray-800 rounded-xl hover:bg-gray-700"
            >
              Usar solo Garmin
            </motion.button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const PermissionItem = ({ icon, label, delay }: { icon: React.ReactNode, label: string, delay: number }) => (
  <motion.div 
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay }}
    whileHover={{ x: 4 }}
    className="flex items-center justify-between p-3 transition-colors bg-gray-800/50 rounded-xl hover:bg-gray-800 border border-gray-800/50"
  >
    <div className="flex items-center space-x-3 text-gray-200">
      <div className="p-2 text-emerald-400 bg-emerald-400/10 rounded-lg">
        {icon}
      </div>
      <span className="font-medium text-sm">{label}</span>
    </div>
    <div className="flex items-center justify-center w-6 h-6 text-white bg-emerald-500 rounded-full shadow-sm">
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    </div>
  </motion.div>
);