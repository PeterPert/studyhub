import { useEffect, useState, useCallback } from 'react'
import { useNavigate, Routes, Route, Navigate } from 'react-router-dom'
import { fetchNotifications, fetchUnreadCount, fetchStudentGroupName } from '../api'
import type { User, Notification } from '../types'
import DashboardLayout from '../components/DashboardLayout'
import Schedule from './Schedule'
import Grades from './Grades'
import AddGrade from './AddGrade'
import StudentAssignments from './StudentAssignments'
import TeacherAssignments from './TeacherAssignments'

const NOTIF_POLL_INTERVAL = 30000 // 30 sec

export default function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [studentGroupName, setStudentGroupName] = useState<string | null>(null)

  useEffect(() => {
    const stored = sessionStorage.getItem('user')
    if (!stored) {
      navigate('/')
      return
    }
    try {
      const u = JSON.parse(stored) as User
      if (u.role !== 'student' && u.role !== 'prepod') {
        sessionStorage.removeItem('user')
        navigate('/')
        return
      }
      setUser(u)
    } catch {
      navigate('/')
    }
  }, [navigate])

  useEffect(() => {
    if (!user || user.role !== 'student') {
      setStudentGroupName(null)
      return
    }
    fetchStudentGroupName(user.id)
      .then((r) => setStudentGroupName(r.group_name))
      .catch(() => setStudentGroupName(null))
  }, [user])

  const refreshNotifications = useCallback(() => {
    if (!user || user.role !== 'student') return
    fetchNotifications(user.id).then(setNotifications)
    fetchUnreadCount(user.id).then(setUnreadCount)
  }, [user])

  useEffect(() => {
    if (!user || user.role !== 'student') return
    refreshNotifications()
    const id = setInterval(refreshNotifications, NOTIF_POLL_INTERVAL)
    return () => clearInterval(id)
  }, [user, refreshNotifications])

  if (!user) return null

  return (
    <DashboardLayout
      user={user}
      studentGroupName={studentGroupName}
      notifications={notifications}
      unreadCount={unreadCount}
      onRefreshNotifications={refreshNotifications}
    >
      <Routes>
        <Route index element={<Navigate to="/schedule" replace />} />
        <Route path="/schedule" element={<Schedule userId={user.id} userRole={user.role} />} />
        <Route
          path="/grades"
          element={
            user.role === 'student' ? <Grades userId={user.id} /> : <Navigate to="/grades/add" replace />
          }
        />
        <Route
          path="/grades/add"
          element={
            user.role === 'prepod' ? <AddGrade userId={user.id} /> : <Navigate to="/grades" replace />
          }
        />
        <Route
          path="/assignments"
          element={
            user.role === 'prepod' ? (
              <TeacherAssignments userId={user.id} />
            ) : (
              <StudentAssignments userId={user.id} />
            )
          }
        />
        <Route path="*" element={<Navigate to="/schedule" replace />} />
      </Routes>
    </DashboardLayout>
  )
}
