import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

const routeNames: Record<string, string> = {
  repositories: 'Repositories',
  flags: 'Feature Flags',
  'stale-flags': 'Stale Flags Detection',
  'code-analysis': 'Code AST Analysis',
  'removal-operations': 'Removal Operations',
  verification: 'Verification Pipeline',
  reports: 'Evidence & Reports',
  settings: 'System Settings',
};

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter((x) => x);

  return (
    <nav className="flex items-center gap-1.5 text-xs text-zinc-400 mb-4 select-none">
      <Link to="/" className="flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors">
        <Home className="w-3.5 h-3.5" />
        <span>FlagOps</span>
      </Link>
      {pathnames.length > 0 && <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
      {pathnames.map((name, index) => {
        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
        const isLast = index === pathnames.length - 1;
        const displayName = routeNames[name] || name;

        return (
          <React.Fragment key={name}>
            {isLast ? (
              <span className="text-zinc-200 font-medium">{displayName}</span>
            ) : (
              <Link to={routeTo} className="text-zinc-400 hover:text-zinc-200 transition-colors">
                {displayName}
              </Link>
            )}
            {!isLast && <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
