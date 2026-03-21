import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchSchedule } from '../api'
import type { ScheduleItem } from '../types'
import './Schedule.css'

/** Пн–Вс (индекс совпадает с API: 0 = понедельник) */
const DAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

interface Props {
  userId: number
  userRole: 'student' | 'prepod'
}

export default function Schedule({ userId, userRole }: Props) {
  const [dayOfWeek, setDayOfWeek] = useState(() => {
    const d = new Date().getDay()
    return d === 0 ? 6 : d - 1
  })
  const [schedule, setSchedule] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    fetchSchedule(userId, userRole, dayOfWeek)
      .then(setSchedule)
      .catch(() => setError('Не удалось загрузить расписание'))
      .finally(() => setLoading(false))
  }, [userId, userRole, dayOfWeek])

  return (
    <div className="schedule-page">
      <motion.div
        className="schedule-day-tabs"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {DAYS.map((name, i) => (
          <motion.button
            key={i}
            type="button"
            className={`tab ${dayOfWeek === i ? 'active' : ''}`}
            onClick={() => setDayOfWeek(i)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {name}
          </motion.button>
        ))}
      </motion.div>

      <motion.div
        className="schedule-card"
        layout
        initial={{ borderRadius: 20 }}
        animate={{ borderRadius: 20 }}
      >
        {loading ? (
          <motion.div className="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.span
              className="spinner"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              ◐
            </motion.span>
            Загрузка...
          </motion.div>
        ) : error ? (
          <motion.p className="empty-msg" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {error}
          </motion.p>
        ) : schedule.length === 0 ? (
          <motion.p className="empty-msg" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
            Нет пар на этот день
          </motion.p>
        ) : (
          <table className="schedule-table">
            <thead>
              <tr>
                <th>Время</th>
                <th>Предмет</th>
                <th>Аудитория</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence mode="popLayout">
                {schedule.map((item, i) => (
                  <motion.tr
                    key={item.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ delay: i * 0.05, duration: 0.3 }}
                    layout
                  >
                    <td className="time">
                      <motion.span
                        className="time-badge"
                        whileHover={{ scale: 1.05 }}
                        transition={{ type: 'spring', stiffness: 400 }}
                      >
                        {item.time.slice(0, 5)}
                      </motion.span>
                    </td>
                    <td className="subject">{item.subject}</td>
                    <td className="classroom">{item.classroom}</td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </motion.div>
    </div>
  )
}
