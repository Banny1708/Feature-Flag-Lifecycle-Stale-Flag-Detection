import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { DashboardPage } from '@/pages/DashboardPage';
import { RepositoriesPage } from '@/pages/RepositoriesPage';
import { FeatureFlagsPage } from '@/pages/FeatureFlagsPage';
import { StaleFlagsPage } from '@/pages/StaleFlagsPage';
import { CodeAnalysisPage } from '@/pages/CodeAnalysisPage';
import { RemovalOperationsPage } from '@/pages/RemovalOperationsPage';
import { VerificationPage } from '@/pages/VerificationPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { SettingsPage } from '@/pages/SettingsPage';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/repositories" element={<RepositoriesPage />} />
        <Route path="/flags" element={<FeatureFlagsPage />} />
        <Route path="/stale-flags" element={<StaleFlagsPage />} />
        <Route path="/code-analysis" element={<CodeAnalysisPage />} />
        <Route path="/removal-operations" element={<RemovalOperationsPage />} />
        <Route path="/verification" element={<VerificationPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        {/* Fallback to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};
