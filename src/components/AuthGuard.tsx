import { Navigate, Outlet } from 'react-router-dom';
import { getAuthToken } from '../config';

export const AuthGuard = () => {
  const token = getAuthToken();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default AuthGuard;
