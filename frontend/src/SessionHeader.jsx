// Session Header Component - Round containers with connecting line
// Uses HORIZON session times only (not Universe)
// Line passes between session name and time for aesthetic feel

import { useState, useEffect } from 'react';

const SessionHeader = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [hoveredSession, setHoveredSession] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // HORIZON Trading sessions only (different from Universe sessions)
  // Horizon does NOT include: Pre-Asia, Asia Close, Low Vol, NY Close
  // Times match the Session Analysis page exactly
  const sessions = [
    { id: 'japan', name: 'Japan', time: '19:00-20:00', color: '#9370DB', start: 1900, end: 2000 },
    { id: 'china', name: 'China', time: '20:00-23:00', color: '#F472B6', start: 2000, end: 2300 },
    { id: 'deadzone', name: 'Deadzone', time: '02:00-03:00', color: '#6B7280', start: 200, end: 300 },
    { id: 'london', name: 'London', time: '03:00-06:00', color: '#3B82F6', start: 300, end: 600 },
    { id: 'us_ib', name: 'US IB', time: '08:20-09:30', color: '#F59E0B', start: 820, end: 930 },
    { id: 'ny_1h', name: 'NY 1H', time: '09:30-10:30', color: '#10B981', start: 930, end: 1030 },
    { id: 'ny_2h', name: 'NY 2H', time: '10:30-11:30', color: '#06B6D4', start: 1030, end: 1130 },
    { id: 'lunch', name: 'Lunch', time: '11:30-13:30', color: '#8B5CF6', start: 1130, end: 1330 },
    { id: 'ny_pm', name: 'NY PM', time: '13:30-16:00', color: '#EF4444', start: 1330, end: 1600 },
  ];

  // Get current HORIZON session based on ET time
  // Returns null if current time doesn't match any Horizon session
  const getCurrentSession = () => {
    const etTime = new Date(currentTime.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const hours = etTime.getHours();
    const minutes = etTime.getMinutes();
    const timeNum = hours * 100 + minutes;

    // Horizon sessions only - no Asia Close (23:00-02:00), no Pre-Asia, Low Vol, etc.
    if (timeNum >= 1900 && timeNum < 2000) return 'japan';
    if (timeNum >= 2000 && timeNum < 2300) return 'china';
    // Gap: 23:00-02:00 is Asia Close in Universe, NOT a Horizon session
    if (timeNum >= 200 && timeNum < 300) return 'deadzone';
    if (timeNum >= 300 && timeNum < 600) return 'london';
    // Gap: 06:00-08:20 is Low Vol in Universe, NOT a Horizon session
    if (timeNum >= 820 && timeNum < 930) return 'us_ib';
    if (timeNum >= 930 && timeNum < 1030) return 'ny_1h';
    if (timeNum >= 1030 && timeNum < 1130) return 'ny_2h';
    if (timeNum >= 1130 && timeNum < 1330) return 'lunch';
    if (timeNum >= 1330 && timeNum < 1600) return 'ny_pm';

    // Outside Horizon trading hours - no active session
    return null;
  };

  const currentSession = getCurrentSession();
  const hasActiveSession = currentSession !== null;

  const totalSessions = sessions.length;

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(12,12,16,0.98) 0%, rgba(8,8,12,1) 100%)',
      borderRadius: 16,
      border: '1px solid rgba(255,255,255,0.08)',
      marginBottom: 16,
      padding: '24px 16px',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
    }}>
      {/* Session Timeline */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative'
      }}>
        {/* Sessions with connecting line */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          position: 'relative',
          width: '100%'
        }}>
          {/* Connecting line behind circles */}
          <div style={{
            position: 'absolute',
            top: 60,
            left: 50,
            right: 50,
            height: 1,
            background: 'rgba(255,255,255,0.1)',
            zIndex: 0
          }} />

          {sessions.map((session, idx) => {
            const isActive = session.id === currentSession;
            const isHovered = hoveredSession === session.id;
            const isPast = (() => {
              if (!hasActiveSession) return false;
              const sessionIndex = sessions.findIndex(s => s.id === currentSession);
              return idx < sessionIndex;
            })();
            const isFirst = idx === 0;
            const isLast = idx === totalSessions - 1;

            const baseSize = 90;

            return (
              <div
                key={session.id}
                onMouseEnter={() => setHoveredSession(session.id)}
                onMouseLeave={() => setHoveredSession(null)}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  position: 'relative',
                  zIndex: isHovered ? 10 : 1,
                  cursor: 'pointer',
                  minWidth: 80,
                  height: 120
                }}
              >
                {/* Round Container with hover animation */}
                <div style={{
                  width: baseSize,
                  height: baseSize,
                  borderRadius: '50%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 3,
                  background: isActive
                    ? `linear-gradient(135deg, rgba(20,20,28,1) 0%, rgba(15,15,22,1) 100%)`
                    : isHovered
                      ? `linear-gradient(135deg, rgba(30,30,40,1) 0%, rgba(25,25,35,1) 100%)`
                      : 'rgb(20, 20, 28)',
                  border: isActive
                    ? `2px solid ${session.color}`
                    : isHovered
                      ? `2px solid ${session.color}80`
                      : '1px solid rgba(255,255,255,0.08)',
                  opacity: !hasActiveSession ? 0.7 : (isPast ? 0.5 : 1),
                  transition: 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  boxShadow: isActive
                    ? `0 0 25px ${session.color}50, 0 8px 32px rgba(0,0,0,0.4)`
                    : isHovered
                      ? `0 0 30px ${session.color}40, 0 12px 40px rgba(0,0,0,0.5)`
                      : '0 4px 12px rgba(0,0,0,0.3)',
                  position: 'relative',
                  transform: isHovered ? 'scale(1.2) translateY(-5px)' : 'scale(1) translateY(0)',
                  zIndex: isHovered ? 5 : 1
                }}>
                  {/* Color Dot */}
                  <div style={{
                    width: isHovered ? 12 : 10,
                    height: isHovered ? 12 : 10,
                    borderRadius: '50%',
                    background: session.color,
                    boxShadow: isActive || isHovered ? `0 0 12px ${session.color}` : 'none',
                    animation: isActive ? 'sessionDotPulse 1.5s ease-in-out infinite' : 'none',
                    transition: 'all 0.3s ease'
                  }} />

                  {/* Session Name - smaller font for "Close" suffix */}
                  <span style={{
                    fontSize: isHovered ? 16 : 14,
                    color: isActive
                      ? session.color
                      : isHovered
                        ? '#fff'
                        : !hasActiveSession
                          ? '#888'
                          : '#e5e5e5',
                    fontWeight: 600,
                    textAlign: 'center',
                    lineHeight: 1.1,
                    transition: 'all 0.3s ease',
                    textShadow: isHovered ? `0 0 10px ${session.color}60` : 'none'
                  }}>
                    {session.name}
                  </span>

                  {/* Time inside circle - reduced by 20% (10px -> 8px) */}
                  <span style={{
                    fontSize: isHovered ? 9 : 8,
                    color: isActive
                      ? session.color
                      : isHovered
                        ? session.color
                        : !hasActiveSession
                          ? '#555'
                          : '#666',
                    fontFamily: "'JetBrains Mono', monospace",
                    opacity: 0.9,
                    transition: 'all 0.3s ease'
                  }}>
                    {session.time}
                  </span>

                  {/* LIVE Badge - only when session is active in Horizon */}
                  {isActive && hasActiveSession && (
                    <div style={{
                      position: 'absolute',
                      bottom: -10,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      background: 'linear-gradient(135deg, #00ff88 0%, #00cc66 100%)',
                      color: '#000',
                      fontSize: 8,
                      fontWeight: 700,
                      padding: '3px 10px',
                      borderRadius: 10,
                      letterSpacing: '0.05em',
                      boxShadow: '0 4px 12px rgba(0,255,136,0.6)',
                      animation: 'liveBadgePulse 2s ease-in-out infinite'
                    }}>
                      LIVE
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes sessionDotPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.2); }
        }
        @keyframes liveBadgePulse {
          0%, 100% { box-shadow: 0 4px 12px rgba(0,255,136,0.6); }
          50% { box-shadow: 0 4px 20px rgba(0,255,136,0.9); }
        }
      `}</style>
    </div>
  );
};

export default SessionHeader;
