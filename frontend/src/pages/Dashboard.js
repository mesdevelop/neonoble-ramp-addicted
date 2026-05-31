import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { usePricing } from '../hooks/usePricing';
import { useTransactions } from '../hooks/useTransactions';
import { Coins, LogOut } from 'lucide-react';
import { PriceDisplay } from '../components/dashboard/PriceDisplay';
import { TransactionList } from '../components/dashboard/TransactionList';
import { RampPanel } from '../components/dashboard/RampPanel';

const POPULAR_CRYPTOS = ['BTC', 'ETH', 'NENO', 'USDT', 'SOL', 'BNB'];

export default function Dashboard() {
  const { user, logout, isDeveloper } = useAuth();
  const navigate = useNavigate();
  const { prices, loading: loadingPrices, refresh: refreshPrices } = usePricing();
  const { transactions, refresh: refreshTransactions } = useTransactions();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="dashboard">
      <header className="border-b border-white/10 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-2">
              <Coins className="h-8 w-8 text-purple-400" />
              <span className="text-xl font-bold text-white">NeoNoble Ramp</span>
            </Link>
            <div className="flex items-center space-x-4">
              <Link
                to="/transak"
                className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                data-testid="nav-transak-demo"
              >
                Transak Demo
              </Link>
              {isDeveloper && (
                <Link
                  to="/dev"
                  className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                  data-testid="nav-dev-portal"
                >
                  Dev Portal
                </Link>
              )}
              <Link
                to="/change-password"
                className="text-gray-300 hover:text-white px-3 py-2 text-sm"
                data-testid="nav-change-password"
              >
                Change Password
              </Link>
              <span className="text-gray-400 text-sm">{user?.email}</span>
              <button
                onClick={handleLogout}
                className="text-gray-400 hover:text-white p-2"
                data-testid="logout-btn"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <RampPanel onTransactionExecuted={refreshTransactions} />
          </div>
          <div className="space-y-6">
            <PriceDisplay
              symbols={POPULAR_CRYPTOS}
              prices={prices}
              loading={loadingPrices}
              onRefresh={refreshPrices}
            />
            <TransactionList transactions={transactions} />
          </div>
        </div>
      </div>
    </div>
  );
}
