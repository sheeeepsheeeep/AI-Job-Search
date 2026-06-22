import React from 'react';
import './Sidebar.css';

export default function Sidebar({ pages, currentPage, onNavigate, collapsed, onToggle, currentUser, onLogout }) {
  const navItems = Object.entries(pages);

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Logo / Brand */}
      <div className="sidebar-header">
        <div className="sidebar-logo" onClick={onToggle}>
          <div className="logo-icon">
            <span className="logo-icon-inner">AI</span>
          </div>
          {!collapsed && (
            <div className="logo-text">
              <span className="logo-title gradient-text">JobSearch</span>
              <span className="logo-subtitle">AI Agent</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">{!collapsed && 'NAVIGATION'}</div>
        {navItems.map(([key, { label, icon }], index) => (
          <button
            key={key}
            className={`nav-item ${currentPage === key ? 'active' : ''}`}
            onClick={() => onNavigate(key)}
            title={collapsed ? label : undefined}
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <span className="nav-icon">{icon}</span>
            {!collapsed && <span className="nav-label">{label}</span>}
            {currentPage === key && <span className="nav-active-indicator" />}
          </button>
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="sidebar-footer">
        <div className="divider" />
        <div className="sidebar-user">
          <div className="user-avatar" title={currentUser?.email || 'Candidate'}>
            <span>👤</span>
          </div>
          {!collapsed && (
            <div className="user-info">
              <span className="user-name" title={currentUser?.email}>
                {currentUser?.email ? currentUser.email.split('@')[0] : 'Candidate'}
              </span>
              <span className="user-status">
                <span className="status-dot" />
                Active
              </span>
            </div>
          )}
          {!collapsed && (
            <button className="btn-logout" onClick={onLogout} title="Log Out">
              🚪
            </button>
          )}
        </div>
        {collapsed && (
          <button className="btn-logout-collapsed" onClick={onLogout} title="Log Out">
            <span>🚪</span>
          </button>
        )}
      </div>
    </aside>
  );
}
