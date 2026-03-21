import { useEffect, useState, useRef } from 'react'
import { useNavigate, NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchUnreadCount, markNotificationRead, markAllNotificationsRead } from '../api'
import type { User, Notification } from '../types'
import './DashboardLayout.css'

interface Props {
  user: User
  notifications: Notification[]
  unreadCount: number
  onRefreshNotifications: () => void
  children: React.ReactNode
}

export default function DashboardLayout({ user, notifications, unreadCount, onRefreshNotifications, children }: Props) {
  const navigate = useNavigate()
  const notifRef = useRef<HTMLDivElement>(null)
  const [showNotifs, setShowNotifs] = useState(false)
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifs(false)
    }
    if (showNotifs) document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [showNotifs])

  const handleLogout = () => {
    sessionStorage.removeItem('user')
    navigate('/')
  }

  const handleMarkRead = async (id: number) => {
    await markNotificationRead(user.id, id)
    onRefreshNotifications()
  }

  const handleMarkAllRead = async () => {
    await markAllNotificationsRead(user.id)
    onRefreshNotifications()
    setShowNotifs(false)
  }

  const navItems =
    user.role === 'prepod'
      ? [
          { to: '/schedule', label: 'Расписание' },
          { to: '/grades/add', label: 'Выставить оценку' },
        ]
      : [
          { to: '/schedule', label: 'Расписание' },
          { to: '/grades', label: 'Оценки' },
        ]

  return (
    <div className="dashboard">
      <div className="dashboard-bg">
        <motion.div className="blob blob-1" animate={{ opacity: [0.3, 0.5, 0.3] }} transition={{ duration: 5, repeat: Infinity }} />
        <motion.div className="blob blob-2" animate={{ opacity: [0.2, 0.4, 0.2] }} transition={{ duration: 6, repeat: Infinity, delay: 1 }} />
      </div>

      <motion.header
        className="dashboard-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="header-left">
          <nav className="nav-tabs">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <p className="user-info">
            <span>{user.name}</span>
            <span className="role-badge">{user.role === 'prepod' ? 'Преподаватель' : 'Студент'}</span>
          </p>
        </div>
        <div className="header-right">
          {user.role === 'student' && (
            <div className="notif-wrapper" ref={notifRef}>
              <motion.button
                type="button"
                className="btn-notif"
                onClick={() => setShowNotifs(!showNotifs)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <span className="notif-icon">🔔</span>
                {unreadCount > 0 && (
                  <motion.span
                    className="notif-badge"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 500 }}
                  >
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </motion.span>
                )}
              </motion.button>
              <AnimatePresence>
                {showNotifs && (
                  <motion.div
                    className="notif-dropdown"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="notif-header">
                      <span>Уведомления</span>
                      {unreadCount > 0 && (
                        <button type="button" className="btn-mark-all" onClick={handleMarkAllRead}>
                          Прочитать все
                        </button>
                      )}
                    </div>
                    <div className="notif-list">
                      {notifications.length === 0 ? (
                        <p className="notif-empty">Нет уведомлений</p>
                      ) : (
                        notifications.map((n) => (
                          <motion.div
                            key={n.id}
                            className={`notif-item ${n.is_read ? 'read' : ''}`}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            onClick={() => !n.is_read && handleMarkRead(n.id)}
                          >
                            <p className="notif-msg">{n.message}</p>
                            <span className="notif-date">{new Date(n.created_at).toLocaleString('ru')}</span>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
          <button type="button" className="btn-logout" onClick={handleLogout}>
            Выйти
          </button>
        </div>
      </motion.header>

      <main className="dashboard-main">
        {children}
      </main>
    </div>
  )
}
